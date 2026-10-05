import re


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