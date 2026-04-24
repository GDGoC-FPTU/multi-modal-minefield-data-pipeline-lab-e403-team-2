import json
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(ROOT_DIR, "raw_data")
STARTER_DIR = os.path.join(ROOT_DIR, "starter_code")
if STARTER_DIR not in sys.path:
    sys.path.insert(0, STARTER_DIR)

from process_csv import process_sales_csv
from process_html import parse_html_catalog
from process_legacy_code import extract_logic_from_code
from process_transcript import clean_transcript
from quality_check import run_quality_gate
from schema import UnifiedDocument


class TestRole1Schema(unittest.TestCase):
    def test_unified_document_validation(self):
        doc = {
            "document_id": "test-doc-001",
            "content": "This is valid content for schema validation.",
            "source_type": "CSV",
            "author": "tester",
            "timestamp": None,
            "title": "test",
            "topics": ["qa"],
            "quality_flags": ["clean"],
            "schema_version": "v1",
            "source_metadata": {"source": "unit-test"},
        }
        model = UnifiedDocument.model_validate(doc)
        self.assertEqual(model.document_id, "test-doc-001")


class TestRole2Processors(unittest.TestCase):
    def test_csv_processor_removes_duplicates(self):
        docs = process_sales_csv(os.path.join(RAW_DATA_DIR, "sales_records.csv"))
        ids = [d["document_id"] for d in docs if d.get("document_id", "").startswith("csv-sale-")]
        self.assertGreater(len(ids), 0)
        self.assertEqual(len(ids), len(set(ids)))

    def test_html_processor_extracts_rows(self):
        docs = parse_html_catalog(os.path.join(RAW_DATA_DIR, "product_catalog.html"))
        self.assertIsInstance(docs, list)
        self.assertGreater(len(docs), 0)

    def test_transcript_processor_extracts_price(self):
        doc = clean_transcript(os.path.join(RAW_DATA_DIR, "demo_transcript.txt"))
        self.assertEqual(doc.get("source_type"), "Video")
        self.assertEqual(doc.get("source_metadata", {}).get("detected_price_vnd"), 500000)

    def test_legacy_processor_detects_discrepancy(self):
        doc = extract_logic_from_code(os.path.join(RAW_DATA_DIR, "legacy_pipeline.py"))
        flags = [str(flag) for flag in doc.get("quality_flags", [])]
        self.assertIn("discrepancy", flags)


class TestRole3QualityGate(unittest.TestCase):
    def test_quality_gate_rejects_toxic_content(self):
        bad_doc = {"content": "Null pointer exception from parser."}
        self.assertFalse(run_quality_gate(bad_doc))

    def test_quality_gate_accepts_clean_content(self):
        clean_doc = {"content": "This is a sufficiently long and clean content string."}
        self.assertTrue(run_quality_gate(clean_doc))


class TestRole4OutputShape(unittest.TestCase):
    def test_generated_output_if_exists_is_valid_json_array(self):
        output_path = os.path.join(ROOT_DIR, "processed_knowledge_base.json")
        if not os.path.exists(output_path):
            self.skipTest("processed_knowledge_base.json not found; run orchestrator first.")

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
