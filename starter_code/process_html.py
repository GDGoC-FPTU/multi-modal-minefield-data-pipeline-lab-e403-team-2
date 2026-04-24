from bs4 import BeautifulSoup
from schema import SourceType, QualityFlag, migrate_to_latest

# ==========================================
# ROLE 2: ETL/ELT BUILDER
# ==========================================
# Task: Extract product data from the HTML table, ignoring boilerplate.

def parse_vnd_price(price_str: str):
    """Parse price string like '28,500,000 VND' -> float, or None if not parseable."""
    s = price_str.strip()
    if s in ("N/A", "Liên hệ", ""):
        return None
    # Remove currency labels and commas
    s = s.replace("VND", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_stock(stock_str: str):
    """Parse stock string to int, return None if not parseable."""
    try:
        return int(stock_str.strip())
    except (ValueError, AttributeError):
        return None


def parse_html_catalog(file_path):
    # --- FILE READING ---
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # --------------------

    soup = BeautifulSoup(content, 'html.parser')

    # Find only the main-catalog table, ignoring nav/footer/sidebar
    table = soup.find('table', id='main-catalog')
    if not table:
        return []

    results = []
    rows = table.find('tbody').find_all('tr')

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cells) < 6:
            continue

        product_id, product_name, category, price_raw, stock_raw, rating_raw = cells[:6]

        flags = []
        price = parse_vnd_price(price_raw)
        if price is None:
            flags.append(QualityFlag.MISSING_PRICE)

        stock = parse_stock(stock_raw)
        if stock is not None and stock < 0:
            flags.append(QualityFlag.NEGATIVE_VALUE)

        if not flags:
            flags.append(QualityFlag.CLEAN)

        content_text = (
            f"Product: {product_name} | Category: {category} | "
            f"Price: {price_raw} | Stock: {stock_raw} | Rating: {rating_raw}"
        )

        doc = {
            "document_id": f"html-product-{product_id.lower()}",
            "content": content_text,
            "source_type": SourceType.HTML,
            "author": "VinShop",
            "timestamp": None,
            "title": product_name,
            "topics": ["product catalog", category.lower()],
            "quality_flags": flags,
            "source_metadata": {
                "product_id": product_id,
                "price_raw": price_raw,
                "price_cleaned": price,
                "stock_quantity": stock,
                "rating": rating_raw,
            },
        }

        results.append(migrate_to_latest(doc))

    return results
