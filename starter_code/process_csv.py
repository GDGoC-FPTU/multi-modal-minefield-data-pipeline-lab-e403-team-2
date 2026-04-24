import pandas as pd
import re
from datetime import datetime
from schema import SourceType, QualityFlag, migrate_to_latest

# ==========================================
# ROLE 2: ETL/ELT BUILDER
# ==========================================
# Task: Process sales records, handling type traps and duplicates.

WORD_TO_NUMBER = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12,
}

def parse_price(value) -> tuple:
    """Return (price_float_or_None, quality_flag_or_None)"""
    if pd.isna(value):
        return None, QualityFlag.MISSING_PRICE
    s = str(value).strip()
    if s in ("N/A", "NULL", "Liên hệ", ""):
        return None, QualityFlag.MISSING_PRICE
    # Remove currency symbol and commas
    s_clean = s.replace("$", "").replace(",", "").strip()
    # Try direct float
    try:
        price = float(s_clean)
        if price < 0:
            return price, QualityFlag.NEGATIVE_VALUE
        return price, None
    except ValueError:
        pass
    # Try word numbers (e.g. "five dollars")
    lower = s_clean.lower()
    for word, num in WORD_TO_NUMBER.items():
        if lower.startswith(word):
            return float(num), None
    return None, QualityFlag.UNPARSEABLE


DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%B %d %Y",
    "%d %b %Y",
]

def parse_date(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Normalize ordinal suffixes: "January 16th 2026" -> "January 16 2026"
    s_norm = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', s)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s_norm, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # Return as-is if unparseable


def process_sales_csv(file_path):
    # --- FILE READING (Handled for students) ---
    df = pd.read_csv(file_path)
    # ------------------------------------------

    # Remove duplicate rows based on 'id' (keep first)
    df = df.drop_duplicates(subset=["id"], keep="first")

    results = []
    for _, row in df.iterrows():
        flags = []

        # Clean price
        price, price_flag = parse_price(row.get("price"))
        if price_flag:
            flags.append(price_flag)

        # Normalize date
        date_str = parse_date(row.get("date_of_sale"))

        # Handle stock
        stock = row.get("stock_quantity")
        stock_val = None
        if pd.notna(stock):
            try:
                stock_val = int(float(stock))
                if stock_val < 0:
                    flags.append(QualityFlag.NEGATIVE_VALUE)
            except (ValueError, TypeError):
                pass

        if not flags:
            flags.append(QualityFlag.CLEAN)

        content = (
            f"Product: {row.get('product_name', 'Unknown')} | "
            f"Category: {row.get('category', 'Unknown')} | "
            f"Price: {price} {row.get('currency', '')} | "
            f"Date: {date_str} | "
            f"Stock: {stock_val}"
        )

        doc = {
            "document_id": f"csv-sale-{row['id']}",
            "content": content,
            "source_type": SourceType.CSV,
            "author": row.get("seller_id", "Unknown"),
            "timestamp": None,
            "title": str(row.get("product_name", "")),
            "topics": ["sales", str(row.get("category", "")).lower()],
            "quality_flags": flags,
            "source_metadata": {
                "original_id": row["id"],
                "price_cleaned": price,
                "currency": row.get("currency"),
                "date_of_sale": date_str,
                "stock_quantity": stock_val,
            },
        }

        results.append(migrate_to_latest(doc))

    return results
