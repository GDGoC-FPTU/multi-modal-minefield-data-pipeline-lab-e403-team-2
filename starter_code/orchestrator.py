import json
import time
import os

# Robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "raw_data")


# Import role-specific modules
from schema import UnifiedDocument
from process_pdf import extract_pdf_data
from process_transcript import clean_transcript
from process_html import parse_html_catalog
from process_csv import process_sales_csv
from process_legacy_code import extract_logic_from_code
from quality_check import run_quality_gate

# ==========================================
# ROLE 4: DEVOPS & INTEGRATION SPECIALIST
# ==========================================
# Task: Orchestrate the ingestion pipeline and handle errors/SLA.

def main():
    start_time = time.time()
    final_kb = []
    
    # --- FILE PATH SETUP (Handled for students) ---
    pdf_path = os.path.join(RAW_DATA_DIR, "lecture_notes.pdf")
    trans_path = os.path.join(RAW_DATA_DIR, "demo_transcript.txt")
    html_path = os.path.join(RAW_DATA_DIR, "product_catalog.html")
    csv_path = os.path.join(RAW_DATA_DIR, "sales_records.csv")
    code_path = os.path.join(RAW_DATA_DIR, "legacy_pipeline.py")
    
    output_path = os.path.join(os.path.dirname(SCRIPT_DIR), "processed_knowledge_base.json")
    # ----------------------------------------------

    pipeline_steps = [
        ("pdf", extract_pdf_data, pdf_path),
        ("transcript", clean_transcript, trans_path),
        ("html", parse_html_catalog, html_path),
        ("csv", process_sales_csv, csv_path),
        ("legacy_code", extract_logic_from_code, code_path),
    ]

    for step_name, step_fn, input_path in pipeline_steps:
        print(f"[Pipeline] Processing {step_name}: {input_path}")
        try:
            result = step_fn(input_path)
        except Exception as exc:
            print(f"[Pipeline] Step '{step_name}' failed: {exc}")
            continue

        # Some processors return one document, others return a list.
        if result is None:
            docs = []
        elif isinstance(result, list):
            docs = result
        else:
            docs = [result]

        for doc in docs:
            if not isinstance(doc, dict):
                print(f"[Pipeline] Skipped invalid output from '{step_name}': not a dict")
                continue

            if not run_quality_gate(doc):
                print(
                    f"[Pipeline] Document rejected by quality gate: "
                    f"{doc.get('document_id', '<unknown>')}"
                )
                continue

            # Validate against role-1 schema before persisting.
            try:
                validated = UnifiedDocument.model_validate(doc)
            except Exception as exc:
                print(
                    f"[Pipeline] Schema validation failed for "
                    f"{doc.get('document_id', '<unknown>')}: {exc}"
                )
                continue

            final_kb.append(validated.model_dump(mode="json"))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_kb, f, ensure_ascii=False, indent=2)
    print(f"[Pipeline] Saved output to {output_path}")

    end_time = time.time()
    print(f"Pipeline finished in {end_time - start_time:.2f} seconds.")
    print(f"Total valid documents stored: {len(final_kb)}")


if __name__ == "__main__":
    main()
