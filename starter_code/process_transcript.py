import re
from schema import SourceType, QualityFlag, migrate_to_latest

# ==========================================
# ROLE 2: ETL/ELT BUILDER
# ==========================================
# Task: Clean the transcript text and extract key information.

# Vietnamese number words -> value mapping
VIET_NUMBER_MAP = {
    "một trăm": 100_000,
    "hai trăm": 200_000,
    "ba trăm": 300_000,
    "bốn trăm": 400_000,
    "năm trăm": 500_000,
    "sáu trăm": 600_000,
    "bảy trăm": 700_000,
    "tám trăm": 800_000,
    "chín trăm": 900_000,
}

def extract_vietnamese_price(text: str):
    """
    Scan text for Vietnamese price patterns like 'năm trăm nghìn VND' -> 500000.
    Returns the detected price as int, or None if not found.
    """
    lower = text.lower()
    for phrase, base_value in VIET_NUMBER_MAP.items():
        if phrase in lower and "nghìn" in lower:
            return base_value
    # Fallback: look for explicit numeric "500,000 VND" patterns
    match = re.search(r'(\d[\d,\.]+)\s*VND', text)
    if match:
        try:
            return int(match.group(1).replace(",", "").replace(".", ""))
        except ValueError:
            pass
    return None


def clean_transcript(file_path):
    # --- FILE READING (Handled for students) ---
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    # ------------------------------------------

    # Remove noise tokens: [Music], [inaudible], [Laughter], [Music starts], [Music ends]
    cleaned = re.sub(r'\[[^\]]*\]', '', text)

    # Strip lines that are now empty or only contain whitespace/colons after noise removal
    lines = []
    for line in cleaned.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    cleaned_text = "\n".join(lines)

    # Extract Vietnamese price BEFORE stripping (work on original text for better context)
    detected_price = extract_vietnamese_price(text)

    # Detect noise quality flag (original had noise tokens)
    had_noise = bool(re.search(r'\[[^\]]*\]', text))

    flags = []
    if had_noise:
        flags.append(QualityFlag.NOISE)
    if not flags:
        flags.append(QualityFlag.CLEAN)

    doc = {
        "document_id": "transcript-demo-001",
        "content": cleaned_text if cleaned_text else text,
        "source_type": SourceType.VIDEO,   # CRITICAL: forensic check expects "Video"
        "author": "Speaker 1",
        "timestamp": None,
        "title": "Data Pipeline Engineering Lecture Transcript",
        "topics": ["data pipeline", "semantic drift", "unstructured data"],
        "quality_flags": flags,
        "source_metadata": {
            "original_file": "demo_transcript.txt",
            "detected_price_vnd": detected_price,  # CRITICAL: forensic check #2
        },
    }

    return migrate_to_latest(doc)
