import asyncio
from pprint import pprint

from playwright.async_api import async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from asgiref.sync import sync_to_async

# Setup Django ORM context
from modules.load_django import *
from modules.utils import (
    clean_text,
    extract_color_from_title,
    parse_price,
    parse_resolution,
)
from parser_app.models import Product


async def get_text(page, xpath: str) -> str | None:
    """Return cleaned text of the first element matched by xpath, or None.

    text_content() is used because the page has duplicated blocks and tabs,
    and it also returns text of elements that are not visible.
    """
    locator = page.locator(f'xpath={xpath}')
    if await locator.count() == 0:
        return None
    return clean_text(await locator.first.text_content()) or None


async def parse_specs(page) -> dict:
    """Parse all product specifications into a dict {name: value}."""
    specs = {}
    rows = page.locator("xpath=//div[contains(@class, 'br-pr-chr-item')]/div/div")
    for index in range(await rows.count()):
        row = rows.nth(index)
        name_node = row.locator('xpath=./span[not(preceding-sibling::span)]')
        value_node = row.locator('xpath=./span[preceding-sibling::span]')
        if await name_node.count() == 0 or await value_node.count() == 0:
            continue

        name = clean_text(await name_node.first.text_content())
        link_texts = await value_node.first.locator('xpath=./a').all_text_contents()
        if link_texts:
            value = ', '.join(clean_text(text) for text in link_texts)
        else:
            value = clean_text(await value_node.first.text_content())

        if name and value:
            specs[name] = value
    return specs


async def parse_prices(page) -> tuple[int | None, int | None]:
    """Return (regular_price, sale_price) relative to the price container."""
    archived = page.locator(
        "xpath=//div[contains(@class, 'main-right-block') and contains(@class, 'archived')]"
    )
    if await archived.count() > 0:
        return None, None

    
    price_container = page.locator("xpath=//div[contains(@class, 'main-price-block')]").first
    if await price_container.count() == 0:
        return None, None

   
    current_price_node = price_container.locator(
        "xpath=.//div[contains(@class, 'br-pr-np')]//div[contains(@class, 'price-wrapper')]/span"
    )
    old_price_node = price_container.locator(
        "xpath=.//div[contains(@class, 'br-pr-op')]//div[contains(@class, 'price-wrapper')]/span"
    )

    current_price_text = await current_price_node.text_content() if await current_price_node.count() > 0 else None
    old_price_text = await old_price_node.text_content() if await old_price_node.count() > 0 else None

    current_price = parse_price(current_price_text)
    old_price = parse_price(old_price_text)

    if old_price is not None:
        return old_price, current_price
    return current_price, None


async def parse_reviews_count(page) -> int | None:
    """Return number of reviews, or None if the block is missing."""
    text = await get_text(
        page,
        "//a[contains(@class, 'reviews-count') and not(contains(@class, 'series-reviews'))]/span",
    )
    if text is None or not text.isdigit():
        return None
    return int(text)


async def parse_photos(page) -> list[str]:
    """Return unique product photo links in page order."""
    photos = []
    images = page.locator("xpath=//img[contains(@class, 'br-main-img')]")
    for index in range(await images.count()):
        link = await images.nth(index).get_attribute('src')
        if link and link.startswith('http') and link not in photos:
            photos.append(link)
    return photos


async def parse_product(page) -> dict:
    """Parse product data from the opened product page using XPath only."""
    title = await get_text(page, "//h1[contains(@class, 'main-title')]")
    product_code = await get_text(page, "//span[contains(@class, 'br-pr-code-val')]")
    specs = await parse_specs(page)
    price, sale_price = await parse_prices(page)
    photos = await parse_photos(page)

    return {
        'title': title,
        'color': extract_color_from_title(title) or specs.get('Колір'),
        'memory': specs.get("Вбудована пам'ять"),
        'manufacturer': specs.get('Виробник'),
        'price': price,
        'sale_price': sale_price,
        'photos': photos or None,
        'product_code': product_code,
        'reviews_count': await parse_reviews_count(page),
        'screen_diagonal': specs.get('Діагональ екрану'),
        'screen_resolution': parse_resolution(specs.get('Роздільна здатність екрану')),
        'specifications': specs or None,
    }


def save_to_db(data: dict, source: str = 'playwright') -> None:
    """Save product in database."""
    if not data.get('product_code'):
        print('[ERROR] Cannot save product without product_code')
        return

    data['parser_source'] = source

    product, created = Product.objects.get_or_create(**data)

    status = 'CREATED' if created else 'ALREADY EXISTS'
    print(f'[{status}] id={product.pk} (source: {source})')


async def main():
    """Main async function to run Playwright parser with search workflow."""
    async with async_playwright() as playwright:
        try:
            print('[INFO] Connecting to running Chrome...')
            browser = await playwright.chromium.connect_over_cdp('http://127.0.0.1:9222')
            context = browser.contexts[0]

            # Open a dedicated tab so the automated page is always the visible one
            page = await context.new_page()
            await page.bring_to_front()

            # Step 1: Open main page
            print('[STEP 1] Opening https://brain.com.ua/')
            await page.goto('https://brain.com.ua/', wait_until='load')

            # Step 2: Enter search query into the visible search input
            print('[STEP 2] Entering search query')
            search_input = page.locator(
                "xpath=//input[contains(@class, 'quick-search-input')] >> visible=true"
            ).first
            await search_input.fill('Apple iPhone 15 128GB Black', timeout=180000)

            # Step 3: Click search button of the quick-search popup that opens while typing
            print('[STEP 3] Clicking search button')
            search_button = page.locator("xpath=//input[contains(@class, 'qsr-submit')] >> visible=true").first
            await search_button.click()

            # Step 4: Wait for results, click first visible product link
            print('[STEP 4] Waiting for search results...')
            first_result = page.locator(
                "xpath=//div[contains(@class, 'view-grid')]//div[contains(@class, 'br-pp-img-grid')]/a >> visible=true"
            ).first
            await first_result.click(timeout=180000)

            
            await page.locator("xpath=//div[contains(@class, 'br-pr-chr-item')]").first.wait_for(
                state='attached', timeout=10000
            )
            await page.locator("xpath=//div[contains(@class, 'main-price-block')]").first.wait_for(
                state='attached', timeout=10000
            )
            await page.locator("xpath=//span[contains(@class, 'br-pr-code-val')]").first.wait_for(
                state='attached', timeout=10000
            )

            # Step 5-6: Parse and print
            print('[STEP 5-6] Parsing product data...')
            product_data = await parse_product(page)
            pprint(product_data)

            # Step 7: Save to database
            await sync_to_async(save_to_db)(product_data, source='playwright')

        except PlaywrightTimeoutError as error:
            print(f'[ERROR] Timeout: {error}')
        except PlaywrightError as error:
            print(f'[ERROR] Playwright error: {error}')

        finally:
            print('[INFO] Done')


if __name__ == '__main__':
    asyncio.run(main())