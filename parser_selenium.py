from pprint import pprint

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

# Setup Django ORM context
from modules.load_django import *
from modules.utils import (
    clean_text,
    extract_color_from_title,
    parse_price,
    parse_resolution,
)
from parser_app.models import Product


def first_visible(driver, xpath: str):
    """Return the first displayed element matched by xpath, or None.

    The site has duplicated blocks (two search fields, hidden product links),
    so only the element the user can actually see must be used.
    """
    return next(
        (element for element in driver.find_elements(By.XPATH, xpath) if element.is_displayed()),
        None,
    )


def get_text(driver, xpath: str) -> str | None:
    """Return cleaned text of the first element matched by xpath, or None.

    textContent is used instead of .text because the page has duplicated
    blocks and tabs, and Selenium returns '' for elements that are not visible.
    """
    try:
        element = driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        return None
    return clean_text(element.get_attribute('textContent')) or None


def parse_specs(driver) -> dict:
    """Parse all product specifications into a dict {name: value}."""
    specs = {}
    rows = driver.find_elements(By.XPATH, "//div[contains(@class, 'br-pr-chr-item')]/div/div")
    for row in rows:
        try:
            name_node = row.find_element(By.XPATH, './span[not(preceding-sibling::span)]')
            value_node = row.find_element(By.XPATH, './span[preceding-sibling::span]')
        except NoSuchElementException:
            continue

        name = clean_text(name_node.get_attribute('textContent'))
        link_nodes = value_node.find_elements(By.XPATH, './a')
        if link_nodes:
            value = ', '.join(clean_text(link.get_attribute('textContent')) for link in link_nodes)
        else:
            value = clean_text(value_node.get_attribute('textContent'))

        if name and value:
            specs[name] = value
    return specs


def parse_prices(driver) -> tuple[int | None, int | None]:
    """Return (regular_price, sale_price) relative to the price container."""
    archived = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'main-right-block') and contains(@class, 'archived')]",
    )
    if archived:
        return None, None

    
    price_blocks = driver.find_elements(By.XPATH, "//div[contains(@class, 'main-price-block')]")
    if not price_blocks:
        return None, None
    price_container = price_blocks[0]

    
    try:
        current_price_node = price_container.find_element(
            By.XPATH, ".//div[contains(@class, 'br-pr-np')]//div[contains(@class, 'price-wrapper')]/span"
        )
        current_price = parse_price(current_price_node.get_attribute('textContent'))
    except NoSuchElementException:
        current_price = None

    try:
        old_price_node = price_container.find_element(
            By.XPATH, ".//div[contains(@class, 'br-pr-op')]//div[contains(@class, 'price-wrapper')]/span"
        )
        old_price = parse_price(old_price_node.get_attribute('textContent'))
    except NoSuchElementException:
        old_price = None

    if old_price is not None:
        return old_price, current_price
    return current_price, None


def parse_reviews_count(driver) -> int | None:
    """Return number of reviews, or None if the block is missing."""
    text = get_text(
        driver,
        "//a[contains(@class, 'reviews-count') and not(contains(@class, 'series-reviews'))]/span",
    )
    if text is None or not text.isdigit():
        return None
    return int(text)


def parse_photos(driver) -> list[str]:
    """Return unique product photo links in page order."""
    photos = []
    for image in driver.find_elements(By.XPATH, "//img[contains(@class, 'br-main-img')]"):
        link = image.get_attribute('src')
        if link and link.startswith('http') and link not in photos:
            photos.append(link)
    return photos


def parse_product(driver) -> dict:
    """Parse product data from the opened product page using XPath only."""
    title = get_text(driver, "//h1[contains(@class, 'main-title')]")
    product_code = get_text(driver, "//span[contains(@class, 'br-pr-code-val')]")
    specs = parse_specs(driver)
    price, sale_price = parse_prices(driver)
    photos = parse_photos(driver)

    return {
        'title': title,
        'color': extract_color_from_title(title) or specs.get('Колір'),
        'memory': specs.get("Вбудована пам'ять"),
        'manufacturer': specs.get('Виробник'),
        'price': price,
        'sale_price': sale_price,
        'photos': photos or None,
        'product_code': product_code,
        'reviews_count': parse_reviews_count(driver),
        'screen_diagonal': specs.get('Діагональ екрану'),
        'screen_resolution': parse_resolution(specs.get('Роздільна здатність екрану')),
        'specifications': specs or None,
    }


def save_to_db(data: dict, source: str = 'selenium') -> None:
    """Save product in database."""
    if not data.get('product_code'):
        print('[ERROR] Cannot save product without product_code')
        return

    data['parser_source'] = source

    product, created = Product.objects.get_or_create(**data)

    status = 'CREATED' if created else 'ALREADY EXISTS'
    print(f'[{status}] id={product.pk} (source: {source})')


def main():
    """Main function to run Selenium parser with search workflow."""
    options = Options()
    options.debugger_address = '127.0.0.1:9222'

    driver = None
    try:
        print('[INFO] Connecting to running Chrome...')
        driver = webdriver.Chrome(options=options)

        wait = WebDriverWait(driver, 10)
        long_wait = WebDriverWait(driver, 180)

        # Step 1: Open main page
        print('[STEP 1] Opening https://brain.com.ua/')
        driver.get('https://brain.com.ua/')

        # Step 2: Enter search query
        print('[STEP 2] Entering search query')
        search_input = long_wait.until(
            lambda d: first_visible(d, "//input[contains(@class, 'quick-search-input')]")
        )
        search_input.send_keys('Apple iPhone 15 128GB Black')

        # Step 3: Click search button
        print('[STEP 3] Clicking search button')
        search_button = long_wait.until(
            lambda d: first_visible(d, "//input[contains(@class, 'qsr-submit')]")
        )
        search_button.click()

        # Step 4: Wait for results and click first product
        print('[STEP 4] Waiting for search results...')
        results_xpath = "//div[contains(@class, 'view-grid')]//div[contains(@class, 'br-pp-img-grid')]/a"
        first_result = long_wait.until(lambda d: first_visible(d, results_xpath))
        first_result.click()

        
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'br-pr-chr-item')]"))
        )
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'main-price-block')]"))
        )
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'br-pr-code-val')]"))
        )

        # Step 5-6: Parse and print
        print('[STEP 5-6] Parsing product data...')
        product_data = parse_product(driver)
        pprint(product_data)

        # Step 7: Save to database
        save_to_db(product_data, source='selenium')

    except TimeoutException as error:
        print(f'[ERROR] Timeout: {error}')
    except NoSuchElementException as error:
        print(f'[ERROR] Element not found: {error}')
    except WebDriverException as error:
        print(f'[ERROR] WebDriver error: {error}')

    finally:
        print('[INFO] Done')


if __name__ == '__main__':
    main()