import json
import re
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
from django.db import IntegrityError
from parser_app.models import Product


def clean_text(text: str | None) -> str:
    """Replace non-breaking spaces and collapse whitespace."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()


def parse_price(value: str | None) -> int | None:
    """Convert price text to int, e.g. '46 999' -> 46999."""
    if not value:
        return None
    digits = re.sub(r'\D', '', value)
    return int(digits) if digits else None


def parse_resolution(value: str | None) -> str | None:
    """Keep only 'WIDTH x HEIGHT', e.g. '1290 x 2796 pixels' -> '1290 x 2796'."""
    if not value:
        return None
    match = re.search(r'\d+\s*[xх]\s*\d+', value)
    return match.group(0) if match else None


def extract_color_from_title(title: str | None) -> str | None:
    """Extract color from title, e.g. '... 128GB Deep Purple (MTP03)' -> 'Deep Purple'."""
    if not title:
        return None
    match = re.search(r'\d+\s*(?:GB|TB)\s+([^()]+?)\s*\(', title, re.IGNORECASE)
    return clean_text(match.group(1)) if match else None


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
    """Return (regular_price, sale_price). sale_price is None if there is no discount."""
    archived = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'main-right-block') and contains(@class, 'archived')]",
    )
    if archived:
        return None, None

    price_block = "//div[contains(@class, 'main-price-block')]"
    current_price = parse_price(
        get_text(driver, f"{price_block}//div[@class='br-pr-np']//div[@class='price-wrapper']/span")
    )
    old_price = parse_price(
        get_text(driver, f"{price_block}//div[@class='br-pr-op']//div[@class='price-wrapper']/span")
    )

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
    for image in driver.find_elements(By.XPATH, "//img[@class='br-main-img']"):
        link = image.get_attribute('src')
        if link and link.startswith('http') and link not in photos:
            photos.append(link)
    return photos


def parse_product(driver) -> dict:
    """Parse product data from the opened product page using XPath only."""
    title = get_text(driver, "//h1[@class='main-title']")
    product_code = get_text(driver, "//span[@class='br-pr-code-val']")
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
        'photos': json.dumps(photos, ensure_ascii=False) if photos else None,
        'product_code': product_code,
        'reviews_count': parse_reviews_count(driver),
        'screen_diagonal': specs.get('Діагональ екрану'),
        'screen_resolution': parse_resolution(specs.get('Роздільна здатність екрану')),
        'specifications': json.dumps(specs, ensure_ascii=False) if specs else None,
    }


def save_to_db(data: dict, source: str = 'selenium') -> None:
    """Save product in database."""
    if not data.get('product_code'):
        print('[ERROR] Cannot save product without product_code')
        return

    data['parser_source'] = source

    try:
        product, created = Product.objects.get_or_create(**data)
    except IntegrityError as error:
        print(f'[ERROR] Integrity error: {error}')
        return
    except TypeError as error:
        print(f'[ERROR] Type error: {error}')
        return

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

        # Step 1: Open main page
        print('[STEP 1] Opening https://brain.com.ua/')
        driver.get('https://brain.com.ua/')

        # Step 2: Enter search query into the visible search input
        print('[STEP 2] Entering search query')
        query = 'Apple iPhone 15 128GB Black'
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@class='quick-search-input']"))
        )
        search_inputs = driver.find_elements(By.XPATH, "//input[@class='quick-search-input']")
        search_input = next((el for el in search_inputs if el.is_displayed()), None)
        if search_input is None:
            raise NoSuchElementException('Visible search input not found')
        search_input.send_keys(query)

        # Step 3: Wait until the quick-search popup receives the query, then click its search button
        print('[STEP 3] Clicking search button')
        wait.until(
            lambda d: any(
                el.get_attribute('value') == query
                for el in d.find_elements(By.XPATH, "//input[@class='qsr-input']")
            )
        )
        search_button = wait.until(
            lambda d: next(
                (el for el in d.find_elements(By.XPATH, "//input[@class='qsr-submit']") if el.is_displayed()),
                None,
            )
        )
        search_button.click()

        # Step 4: Wait for results (solve Cloudflare check manually if shown), click first visible product link
        print('[STEP 4] Waiting for search results...')
        results_xpath = "//div[contains(@class, 'view-grid')]//div[contains(@class, 'br-pp-img-grid')]/a"
        WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.XPATH, results_xpath))
        )
        result_links = driver.find_elements(By.XPATH, results_xpath)
        first_result = next((el for el in result_links if el.is_displayed()), None)
        if first_result is None:
            raise NoSuchElementException('No visible product link in search results')
        first_result.click()

        # Wait until the product page is loaded before parsing
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//span[@class='br-pr-code-val']"))
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