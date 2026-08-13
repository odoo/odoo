# invoice-ai

[![CI](https://github.com/7ananSaif/odoo/actions/workflows/invoice-ai-ci.yml/badge.svg?branch=main)](https://github.com/7ananSaif/odoo/actions/workflows/invoice-ai-ci.yml)

Standalone vendor invoice extraction service for the `invoice_agent` Odoo
addon (see `docs/adr-003-ai-service.md` for the measured justification: a
5 s Claude call holds an Odoo HTTP worker process, and six concurrent
extractions degraded `/web/login` **33.5×** on a `workers=2` server).

The service owns what the Odoo request path must never run synchronously:

- multipart ingestion (`POST /v1/extract`),
- OCR (Tesseract + poppler, `app/ocr.py` — ADR-002 methodology),
- the winning prompt (`app/prompts/v3.md`) + prompt caching
  (`cache_control` on the frozen system block),
- the single Anthropic Claude call (`app/claude.py`, `AsyncAnthropic`).

The OpenAPI contract that locks this boundary lives in
`docs/openapi.yaml` (versioned `/v1`, `ErrorEnvelope` on every failure).

## Run

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs
```

The endpoint is `async def`; the Claude call runs through
`AsyncAnthropic` (httpx `AsyncClient`), so one uvicorn process concurrently
serves many extraction calls — no per-request process pinning.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/extract` | multipart `file` (PDF/image, ≤10 MiB) **or** OCR `text` → `InvoiceExtraction` + usage |
| GET | `/healthz` | liveness probe |

Errors follow the `{"error": {"code", "message", "retry_after_seconds?"}}`
envelope: `E4001` bad request · `E4131` too large · `E4151` bad mimetype ·
`E4221` validation failed · `E5031` upstream AI failure (rate limits surface
here as 503 with `retry_after_seconds`).

## Test

```bash
pytest -q            # httpx ASGITransport + mocked Claude service (no network)
ruff check app tests
```

## Monorepo vs separate repository — decision

**Decision: monorepo folder (`invoice-ai/`) inside the Odoo repo.**

Why, and when this reverses:

| Criterion | This project today | Separate repo wins when |
|---|---|---|
| Schema contract | `InvoiceExtraction` is shared **verbatim** with `custom_addons/invoice_agent/models/invoice_extraction.py`. One repo lets CI diff the two JSON Schemas and fail the build on drift. | The addon and service land on independent release cadences with a real versioned compatibility matrix (e.g. `invoice-ai` v2 ↔ addon v1). |
| Deployment | Both are deployed from the same GitHub Actions pipeline / EC2 runbook; the service ships alongside Odoo in the same compose file. | The service needs its own autoscaling, secrets scope, and deploy pipeline (bigger than "one more compose service"). |
| Dev loop | One checkout, one PR touches both sides — a child PR like this one (`invoice-ai/` + ADR + contract) is reviewable in a single diff. | Teams/builds are physically separated and the Odoo fork history pollution matters. |
| Risk | The Odoo repo is a fork of upstream `odoo/odoo`; a nested service folder adds no fork-merge burden since it is code we own. | Service must be public/OSS while the Odoo fork stays private. |

The boundary lock that matters is **not** the folder boundary — it is the
`docs/openapi.yaml` contract plus the shared Pydantic schema. As long as
clients talk `/v1` and the schemas are diffed in CI, moving `invoice-ai/`
to its own repository later is a copy-paste + secrets pass, not an
architecture change. ADR-003's non-goal (no microservice sprawl) is the
guard against fragmenting further services out.

## Layout

```
invoice-ai/
├── pyproject.toml            # deps pinned: anthropic, fastapi, uvicorn[standard]
├── Dockerfile                # python:3.12-slim + poppler + tesseract (-eng, -ara)
├── app/
│   ├── main.py               # FastAPI app: /v1/extract + /healthz + error envelope
│   ├── schemas.py            # InvoiceExtraction — verbatim twin of the Odoo schema
│   ├── claude.py             # AsyncAnthropic messages.parse + prompt caching
│   ├── ocr.py                # Tesseract/pdf2image (psm 6 @ 300 DPI)
│   ├── config.py             # pydantic-settings (BaseSettings)
│   ├── errors.py             # typed exceptions → OpenAPI ErrorEnvelope
│   ├── dependencies.py       # Depends(get_claude_service) — test seam
│   └── prompts/v3.md         # winning prompt (cacheable system prefix)
└── tests/
    ├── conftest.py           # ASGITransport client + FakeClaude
    └── test_extract.py       # happy, PDF-OCR, 400, 413, 415, 503
```

## Config

All settings read `INVOICE_AI_*` env vars (see `app/config.py`):

- `INVOICE_AI_ANTHROPIC_API_KEY` — Claude API key
- `INVOICE_AI_ANTHROPIC_MODEL` — model id (default `claude-opus-4-8`)
- `INVOICE_AI_MAX_UPLOAD_BYTES` — upload cap (default 10 MiB)
