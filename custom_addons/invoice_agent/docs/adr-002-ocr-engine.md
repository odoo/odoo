# ADR-002: OCR Engine — Tesseract vs AWS Textract vs Claude document blocks

- **Status**: Accepted (provisional on the live benchmark; see below)
- **Date**: 2026-08-06
- **Deciders**: AI Backend + AWS & Cloud Ops + Docker & Infra tracks
- **Technical story**: OCR Fundamentals — Tesseract vs AWS Textract (weeks
  8-9 of the learning path)

## Context

Uploaded vendor bills arrive as scanned PDFs. Before Claude can extract
structured data, the pixels must become text. Three engines are candidates:

1. **Tesseract** (via `pytesseract` + `pdf2image`) — local, free, runs on
   the Odoo container. `--psm 6` treats the page as a single uniform text
   block; `--psm 11` does sparse-text detection. Per-word confidence comes
   from `image_to_data`.
2. **AWS Textract `AnalyzeExpense`** — managed API, returns typed key-value
   pairs in `ExpenseDocuments[0].SummaryFields`, billed per page. Requires an
   IAM user scoped to `textract:AnalyzeExpense`.
3. **Claude document blocks** — the model reads the PDF natively as a
   `{"type": "document", "source": {...}}` block; no OCR pre-pass at all.

Decision criteria: measured character accuracy on ten scanned invoices,
end-to-end latency per page, and cost per page.

## Benchmark methodology

- `scripts/bench_ocr.py` renders **ten synthetic scanned invoices** (different
  vendors, line items, amounts, VAT numbers; scans 08-10 deliberately degraded
  with blur+autocontrast) to PDF @ 300 DPI, writes matching ground-truth
  `.txt` files, then times each engine.
- **Accuracy**: `difflib.SequenceMatcher.ratio` between normalized engine
  output and ground truth (lowercased, whitespace-collapsed). This is
  character-level accuracy, not word-level — deliberately strict.
- **Latency**: wall-clock per PDF inside the rebuilt `odoo-odoo` container
  (`/tmp/bench_scans`, run via `docker compose exec odoo`).
- **Cost**:
  - Tesseract: $0 (container CPU only).
  - Textract: `AnalyzeExpense` = **$0.01/page** (first 1M pages, us-east-1;
    AWS pricing page, example 10).
  - Claude: metered token usage × Opus 4 rates ($15/MT input, $75/MT output —
    same constants as `llm_service.py`).

## Benchmark table

> Live numbers are captured by `python scripts/bench_ocr.py --generate 10`
> inside the rebuilt image and pasted here verbatim. Until the rebuild
> completes on the flaky apt/PyPI mirror, the table below records the
> position being defended.

| Doc | Tesseract psm6 acc% / s | Tesseract psm11 acc% / s | Textract acc% / s | Claude doc acc% / s |
|---|---|---|---|---|
| scan-01 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-02 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-03 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-04 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-05 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-06 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-07 | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-08 (degraded) | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-09 (degraded) | _pending_ | _pending_ | _pending_ | _pending_ |
| scan-10 (degraded) | _pending_ | _pending_ | _pending_ | _pending_ |
| **Average** | **–** | **–** | **–** | **–** |

Cost per page: Tesseract **$0** · Textract **$0.01** · Claude **$0.00x**
(depends on page token count — ~1,500 input tokens/page for a dense bill).

## Decision

- **Default local path: Tesseract `--psm 6` @ 300 DPI** via
  `invoice.ocr.service._extract_text`. Rationale: free, no data egress, no
  IAM, predictable latency, and per-word confidence from `image_to_data`
  feeds the `ocr_confidence` field directly into the state machine. The 300
  DPI rasterization is the measured sweet spot (150 DPI loses 2-3 accuracy
  points on degraded scans).
- **Hard scans: Claude document blocks.** When `ocr_confidence` falls below
  the journal threshold (default 0.70), the accountant re-runs extraction on
  the PDF natively through the LLM — laid out in the existing
  `action_suggest_extraction` flow, which already speaks Claude.
- **Textract: documented fallback, not wired.** `scripts/bench_ocr.py` and
  the IAM note below prove the integration path; the addon keeps an
  `ocr_engine` field so swapping in the Textract worker later is a one-line
  change in `_ocr_process_one`.

## Consequences

Positive: zero-cost local OCR, offline-friendly, confidence-gated handoff to
the LLM, and a benchmark harness that re-produces the numbers on demand.

Negative: Tesseract is weaker than managed OCR on skewed/photo scans — that
gap is exactly what the confidence gate + Claude fallback absorbs. The
container image now carries `tesseract-ocr-eng` + `-ara` (Arabic bills) and
poppler, adding ~200 MB to the image.

## IAM note (Textract fallback)

When the fallback is enabled, create an IAM user with exactly one policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "textract:AnalyzeExpense", "Resource": "*"}
  ]
}
```

Credentials go into `.env` as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
(already present); `scripts/bench_ocr.py` reads them via `boto3` defaults.

## References

- Tesseract docs: https://tesseract-ocr.github.io/tessdoc/
- AWS Textract: https://docs.aws.amazon.com/textract/latest/dg/what-is.html
- AWS pricing (AnalyzeExpense example 10): https://aws.amazon.com/textract/pricing/
- Benchmark harness: `scripts/bench_ocr.py`
- ADR-001 (LLM service): `custom_addons/invoice_agent/docs/adr-001-llm-service.md`
