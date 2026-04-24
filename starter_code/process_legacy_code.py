import ast
import re
from schema import SourceType, QualityFlag, migrate_to_latest

# ==========================================
# ROLE 2: ETL/ELT BUILDER
# ==========================================
# Task: Extract docstrings and comments from legacy Python code.


def extract_logic_from_code(file_path):
    # --- FILE READING (Handled for students) ---
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    # ------------------------------------------

    # --- Extract docstrings via AST (safe, no execution) ---
    tree = ast.parse(source_code)

    docstrings = {}
    business_rules = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                name = getattr(node, 'name', '__module__')
                docstrings[name] = docstring

                # Extract business rule references from docstrings
                rules_found = re.findall(r'Business Logic Rule\s+(\w+)', docstring)
                for rule in rules_found:
                    business_rules.append(f"Rule {rule}: {docstring.strip()}")

    # --- Detect business rule comments (# Business Logic Rule XXX) ---
    comment_rules = re.findall(r'#\s*(Business Logic Rule\s+\w+.*)', source_code)
    for cr in comment_rules:
        if cr not in business_rules:
            business_rules.append(cr.strip())

    # --- Detect tax rate discrepancy ---
    # Comment says 8%, code sets 0.10 (10%)
    has_discrepancy = False
    discrepancy_note = ""
    # Find the comment that mentions the stated rate (8%) vs actual code rate (10%)
    # Comment: "the code says it does 8%" — look for the smaller % number in comment
    comment_pct_matches = re.findall(r'#[^\n]*', source_code)
    comment_rate = None
    for line in comment_pct_matches:
        nums = re.findall(r'(\d+)%', line)
        if len(nums) >= 2:
            # Line mentions two rates — the discrepancy comment
            comment_rate = int(min(nums, key=int))  # stated wrong rate is the smaller one (8)
            break
        elif nums:
            candidate = int(nums[0])
            if comment_rate is None:
                comment_rate = candidate
    code_tax_match = re.search(r'tax_rate\s*=\s*([\d.]+)', source_code)
    if comment_rate is not None and code_tax_match:
        code_rate = float(code_tax_match.group(1))
        if abs(comment_rate / 100 - code_rate) > 0.001:
            has_discrepancy = True
            discrepancy_note = (
                f"Tax rate discrepancy detected: comment says {comment_rate}%, "
                f"code uses {int(code_rate * 100)}%."
            )

    # --- Build content ---
    content_parts = []
    for func_name, doc in docstrings.items():
        content_parts.append(f"[{func_name}] {doc}")
    if discrepancy_note:
        content_parts.append(discrepancy_note)
    content = "\n\n".join(content_parts) if content_parts else "Legacy pipeline business logic."

    flags = []
    if has_discrepancy:
        flags.append(QualityFlag.DISCREPANCY)
    if not flags:
        flags.append(QualityFlag.CLEAN)

    doc = {
        "document_id": "legacy-pipeline-001",
        "content": content,
        "source_type": SourceType.CODE,
        "author": "Senior Dev (retired)",
        "timestamp": None,
        "title": "VinData Legacy Pipeline v1.2",
        "topics": ["business logic", "pricing", "discounts", "tax", "region mapping"],
        "quality_flags": flags,
        "source_metadata": {
            "original_file": "legacy_pipeline.py",
            "functions_found": list(docstrings.keys()),
            "business_rules": business_rules,
            "tax_discrepancy": discrepancy_note if discrepancy_note else None,
        },
    }

    return migrate_to_latest(doc)
