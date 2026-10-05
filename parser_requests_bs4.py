import json
import re
from pprint import pprint

import requests
from bs4 import BeautifulSoup

# Setup Django ORM context
from modules.load_django import *
from django.db import IntegrityError
from parser_app.models import Product

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ' (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.google.com/',
}

URLS = [
    'https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html',
    'https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_128GB_Black-p1145393.html',
    'https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_14_Pro_Max_128Gb_Deep_Purple_REF_A_BREEZY_2QMQ9T3-p1376515.html',
]


def clean_text(text: str | None) -> str:
    """Replace non-breaking spaces and collapse whitespace."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()


def parse_price(node) -> int | None:
    """Convert text of ONE price node to int, e.g. '46 999' -> 46999."""
    if node is None:
        return None
    digits = re.sub(r'\D', '', node.get_text())
    return int(digits) if digits else None


def parse_resolution(value: str | None) -> str | None:
    """Keep only 'WIDTH x HEIGHT', e.g. '1290 x 2796 pixels' -> '1290 x 2796'."""
    if not value:
        return None
    match = re.search(r'\d+\s*[xх]\s*\d+', value)  # latin x and cyrillic х
    return match.group(0) if match else None


def parse_specs(soup: BeautifulSoup) -> dict:
    """
    Page structure:
    .br-pr-chr-item (section) > div > div (row) > span (name) + span (value)
    The name is found first, the value is its next sibling span (no index usage).
    """
    specs = {}
    for row in soup.select('.br-pr-chr-item > div > div'):
        name_node = row.find('span')
        if name_node is None:
            continue
        value_node = name_node.find_next_sibling('span')
        if value_node is None:
            continue

        name = clean_text(name_node.get_text())
        links = value_node.find_all('a')
        if links:  # value is a list of links, e.g. "2G, 3G, 4G, 5G"
            value = ', '.join(clean_text(link.get_text()) for link in links)
        else:
            value = clean_text(value_node.get_text())

        if name and value:
            specs[name] = value
    return specs


def parse_photos(soup: BeautifulSoup) -> list[str]:
    """Return unique product photo links in page order."""
    photos = []
    for image in soup.select('img.br-main-img'):
        link = image.get('src')
        if link and link.startswith('http') and link not in photos:
            photos.append(link)
    return photos


def extract_color_from_title(title: str | None) -> str | None:
    """Extract color from title, e.g. '... 128GB Deep Purple (MTP03)' -> 'Deep Purple'."""
    if not title:
        return None
    match = re.search(r'\d+\s*(?:GB|TB)\s+([^()]+?)\s*\(', title, re.IGNORECASE)
    return clean_text(match.group(1)) if match else None


def parse_product(url: str) -> dict:
    """Parse a product page and extract all relevant data."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # --- TITLE ---
    title = None
    try:
        title = clean_text(soup.select_one('h1').get_text())
    except AttributeError:
        pass

    # --- SPECIFICATIONS ---
    specs = parse_specs(soup)

    # --- MANUFACTURER ---
    manufacturer = specs.get('Виробник')

    # --- PRODUCT CODE ---
    product_code = None
    try:
        product_code = clean_text(soup.select_one('span.br-pr-code-val').get_text())
    except AttributeError:
        pass

    # --- PRICES ---
    # Discontinued products keep a hidden price block in HTML,
    # so the "archived" class must be checked first.
    is_archived = soup.select_one('div.main-right-block.archived') is not None
    price = None
    sale_price = None

    if not is_archived:
        price_block = soup.select_one('div.main-price-block')
        if price_block is not None:
            old_price_node = price_block.select_one('div.br-pr-op div.price-wrapper > span')
            new_price_node = price_block.select_one('div.br-pr-np div.price-wrapper > span')
            if old_price_node is not None:
                price = parse_price(old_price_node)
                sale_price = parse_price(new_price_node)
            else:
                price = parse_price(new_price_node)

    # --- REVIEWS COUNT ---
    reviews_count = None
    try:
        reviews_count = int(
            soup.select_one('a.reviews-count:not(.series-reviews) > span').get_text(strip=True)
        )
    except (AttributeError, ValueError):
        pass

    # --- PHOTOS ---
    photos = parse_photos(soup)

    return {
        'title': title,
        'color': extract_color_from_title(title) or specs.get('Колір'),
        'memory': specs.get("Вбудована пам'ять"),
        'manufacturer': manufacturer,
        'price': price,
        'sale_price': sale_price,
        'photos': photos or None,
        'product_code': product_code,
        'reviews_count': reviews_count,
        'screen_diagonal': specs.get('Діагональ екрану'),
        'screen_resolution': parse_resolution(specs.get('Роздільна здатність екрану')),
        'specifications': specs or None,
    }


def save_to_db(data: dict, source: str = 'requests_bs4') -> None:
    """Save or update product in database."""
    product_code = data.get('product_code')
    if not product_code:
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


if __name__ == '__main__':
    for url in URLS:
        print(f'\nParsing: {url}')
        try:
            product_data = parse_product(url)
        except requests.RequestException as error:
            print(f'[ERROR] Request failed: {error}')
            continue

        pprint(product_data)
        save_to_db(product_data, source='requests_bs4')