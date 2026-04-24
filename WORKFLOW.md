# WORKFLOW — The Multi-Modal Minefield (Data Pipeline Lab)

## Tổng quan luồng xử lý

```
raw_data/
├── lecture_notes.pdf       ──→ process_pdf.py
├── sales_records.csv       ──→ process_csv.py
├── product_catalog.html    ──→ process_html.py
├── demo_transcript.txt     ──→ process_transcript.py
└── legacy_pipeline.py      ──→ process_legacy_code.py
                                        │
                              (mỗi processor trả về)
                              UnifiedDocument (dict)
                                        │
                                quality_check.py
                               run_quality_gate()
                                        │
                              ┌─────────┴─────────┐
                            PASS               FAIL (bị loại)
                              │
                          final_kb[]
                              │
                  processed_knowledge_base.json
```

---

## Vai trò & File tương ứng

| Role | Tên vai trò | File chính | Trạng thái |
|------|-------------|------------|------------|
| 1 | Lead Data Architect | `starter_code/schema.py` | ✅ Hoàn thành |
| 2 | ETL/ELT Builder | `starter_code/process_*.py` | ✅ Hoàn thành |
| 3 | Observability & QA Engineer | `starter_code/quality_check.py` | 🔲 TODO |
| 4 | DevOps & Integration Specialist | `starter_code/orchestrator.py` | 🔲 TODO |

---

## Chi tiết từng bước

### Role 1 — Schema (`schema.py`)

Định nghĩa **Data Contract** dùng chung cho toàn bộ pipeline.

```
schema.py
├── SourceType (Enum)     — PDF | CSV | HTML | Video | Code
├── QualityFlag (Enum)    — clean | missing_price | negative_value |
│                           duplicate | discrepancy | noise | unparseable
├── UnifiedDocument       — Pydantic model, trường bắt buộc:
│   ├── document_id       (str, không rỗng)
│   ├── content           (str, không rỗng)
│   ├── source_type       (SourceType)
│   ├── author            (str, mặc định "Unknown")
│   ├── timestamp         (datetime | None)
│   ├── title             (str | None)
│   ├── topics            (List[str])
│   ├── quality_flags     (List[QualityFlag])
│   ├── schema_version    (str, mặc định "v1")
│   └── source_metadata   (dict, linh hoạt theo nguồn)
├── V2_FIELD_RENAMES      — dict sẵn sàng cho migration v1→v2
└── migrate_to_latest()   — áp dụng rename, tất cả processor gọi hàm này
```

---

### Role 2 — ETL/ELT Processors (`process_*.py`)

Mỗi file nhận `file_path`, trả về `dict` hoặc `list[dict]` theo chuẩn `UnifiedDocument`.

#### `process_csv.py` — Sales Records

```
Đầu vào : raw_data/sales_records.csv (20 rows thô, có lỗi)
Xử lý   :
  1. Loại bỏ duplicate theo cột `id` (giữ lần đầu)
  2. Làm sạch cột `price`:
       "$1200"       → 1200.0
       "five dollars"→ 5.0
       "N/A" / "NULL"/ "Liên hệ" → None  [flag: missing_price]
       giá âm        → flag: negative_value
  3. Chuẩn hóa `date_of_sale` về YYYY-MM-DD (6 định dạng khác nhau)
  4. Xử lý stock rỗng hoặc âm
Đầu ra  : list[dict] — 20 UnifiedDocument (source_type=CSV)
```

#### `process_html.py` — Product Catalog

```
Đầu vào : raw_data/product_catalog.html
Xử lý   :
  1. BeautifulSoup tìm <table id="main-catalog"> — bỏ nav/footer/sidebar
  2. Extract 5 hàng sản phẩm
  3. Parse giá VND, xử lý "N/A" và "Liên hệ" → None [flag: missing_price]
  4. Stock âm → flag: negative_value
Đầu ra  : list[dict] — 5 UnifiedDocument (source_type=HTML)
```

#### `process_transcript.py` — Lecture Transcript (⭐ Forensic Check #2)

```
Đầu vào : raw_data/demo_transcript.txt
Xử lý   :
  1. Xóa noise tokens: [Music], [inaudible], [Laughter], v.v.
  2. Xóa timestamps: [HH:MM:SS]
  3. Trích xuất giá tiếng Việt:
       "năm trăm nghìn" → source_metadata['detected_price_vnd'] = 500000
Đầu ra  : dict — 1 UnifiedDocument
             source_type      = "Video"   ← BẮT BUỘC cho forensic agent
             detected_price_vnd = 500000  ← BẮT BUỘC cho forensic check #2
             quality_flags    = [noise]
```

#### `process_legacy_code.py` — Business Logic Extraction

```
Đầu vào : raw_data/legacy_pipeline.py
Xử lý   :
  1. ast.parse() — extract docstrings an toàn (không execute code)
  2. Regex tìm "# Business Logic Rule XXX" comments
  3. Phát hiện discrepancy:
       comment nói "8%" ≠ code tax_rate = 0.10 (10%)
       → flag: discrepancy
Đầu ra  : dict — 1 UnifiedDocument (source_type=Code)
```

#### `process_pdf.py` — Lecture Notes PDF (Gemini API)

```
Đầu vào : raw_data/lecture_notes.pdf
Yêu cầu : GEMINI_API_KEY trong file .env
Xử lý   :
  1. genai.upload_file() — upload PDF lên Gemini
  2. generate_content() — prompt yêu cầu Title, Author, 3-sentence summary
  3. Parse JSON response (xử lý markdown code block nếu có)
Đầu ra  : dict — 1 UnifiedDocument (source_type=PDF)
```

---

### Role 3 — Quality Gate (`quality_check.py`)

```python
run_quality_gate(document_dict) -> bool
```

| Rule | Điều kiện | Hành động |
|------|-----------|-----------|
| R1 | `len(content) < 20` | reject (return False) |
| R2 | content chứa `"Null pointer exception"` hoặc chuỗi lỗi | reject ← Forensic Check #3 |
| R3 | flag `discrepancy` có trong quality_flags | log cảnh báo, vẫn cho qua |

---

### Role 4 — Orchestrator (`orchestrator.py`)

```
main()
├── 1. Khai báo đường dẫn (dùng RAW_DATA_DIR, không hardcode)
├── 2. Gọi từng processor:
│       extract_pdf_data(pdf_path)
│       process_sales_csv(csv_path)
│       parse_html_catalog(html_path)
│       clean_transcript(trans_path)
│       extract_logic_from_code(code_path)
├── 3. Với mỗi document/list document:
│       if run_quality_gate(doc): final_kb.append(doc)
├── 4. json.dump(final_kb, output_path)
└── 5. In thời gian xử lý & số lượng document (SLA tracking)
```

**Output file:** `processed_knowledge_base.json` ở thư mục gốc project.

---

## Cách chạy pipeline

```bash
# 1. Cài dependencies
pip install -r requirements.txt

# 2. Tạo file .env ở thư mục gốc
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. Copy lecture_notes.pdf vào raw_data/
cp path/to/lecture_notes.pdf raw_data/

# 4. Chạy pipeline
python starter_code/orchestrator.py

# 5. Kiểm tra kết quả với forensic agent
python forensic_agent/agent_forensic.py
```

---

## Forensic Agent — 3 điểm kiểm tra tự động

| Check | Nội dung kiểm tra | File liên quan |
|-------|-------------------|----------------|
| #1 | Không có document_id trùng trong CSV docs | `process_csv.py` |
| #2 | `source_metadata['detected_price_vnd'] == 500000` và `source_type == "Video"` | `process_transcript.py` |
| #3 | Không có document nào chứa `"Null pointer exception"` | `quality_check.py` |

Điểm đạt: **≥ 2/3**

---

## Mid-Lab Incident — Schema Migration v1 → v2

Vào T+60 phút, schema thay đổi được thông báo. Quy trình xử lý:

```
1. Role 1 cập nhật V2_FIELD_RENAMES trong schema.py:
       V2_FIELD_RENAMES = { "old_field": "new_field", ... }
   và bump SCHEMA_VERSION = "v2"

2. Tất cả processor đã gọi migrate_to_latest() trước khi return
   → Migration tự động áp dụng, không cần sửa từng file

3. Role 4 chạy lại orchestrator.py để reprocess toàn bộ
```

---

## Cấu trúc thư mục

```
multi-modal-minefield-data-pipeline-lab-e403-team-2/
├── .env                              ← GEMINI_API_KEY (tự tạo, không commit)
├── requirements.txt
├── STUDENT_GUIDE_VN.md
├── codelab_03_v1.md
├── WORKFLOW.md                       ← file này
├── processed_knowledge_base.json     ← output (tự sinh sau khi chạy)
├── raw_data/
│   ├── sales_records.csv
│   ├── product_catalog.html
│   ├── demo_transcript.txt
│   ├── legacy_pipeline.py
│   └── lecture_notes.pdf             ← tự thêm vào
├── starter_code/
│   ├── schema.py                     ← Role 1 ✅
│   ├── process_pdf.py                ← Role 2 ✅
│   ├── process_csv.py                ← Role 2 ✅
│   ├── process_html.py               ← Role 2 ✅
│   ├── process_transcript.py         ← Role 2 ✅
│   ├── process_legacy_code.py        ← Role 2 ✅
│   ├── quality_check.py              ← Role 3 🔲
│   └── orchestrator.py               ← Role 4 🔲
└── forensic_agent/
    └── agent_forensic.py
```
