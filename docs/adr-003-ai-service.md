# ADR-003: Separate `invoice-ai` Service for Claude Extraction

- **Status**: Accepted
- **Date**: 2026-08-11
- **Deciders**: AI Backend · Linux & Systems · Git & CI/CD tracks
- **Technical story**: Why a Separate Service — Boundaries & Scaling

## Context

The `invoice_agent` addon runs Claude extraction (`client.messages.parse`,
~5-20 s per invoice) *inside an Odoo HTTP worker*. Odoo's process model is
prefork: each of the `workers`-configured HTTP workers is a separate process
serving one request at a time. A long LLM round-trip therefore pins one
worker for its whole duration; when concurrent uploads exceed the worker
count, every unrelated page — including the login page — queues behind them.

Odoo's own engineering guidance is explicit: heavyweight, slow, externally-
dependent work does not belong on the HTTP request path. The module already
routes OCR (a ~20 s Tesseract job) through `ir.cron` for exactly this reason
(`data/cron.xml`), but the Claude call remained on the request path.

## Decision

Extract OCR + Claude extraction + prompt handling into a standalone
**`invoice-ai`** service (FastAPI, one process, independently deployed and
scaled), and make Odoo a *client* of it.

- The service boundary is locked today by `docs/openapi.yaml` — versioned
  `/v1` prefix before any client exists.
- Odoo keeps what it is uniquely good at: records, security (ACLs, record
  rules, multi-company), the extraction state machine, the confidence
  routing, and the workflow (draft bills, Needs Review, approval).
- The service owns: multipart ingestion, PDF/image OCR (Tesseract),
  the winning prompt (`prompts/v3.md`), prompt caching, and the single
  Anthropic API call.

## Measured evidence — Claude calls block Odoo HTTP workers

Methodology (deterministic, zero API cost — see the note below): an
`invoice_agent.measure_delay` config parameter makes the LLM service's
client constructor sleep *inside the HTTP worker process* for a given number
of seconds, exactly where a real Claude round-trip would block
(`models/llm_service.py::_client`). A dev-only route
(`/invoice_agent/measure/trigger`) runs that code path synchronously per
request. `scripts/measure_blocking.py` fires **6 concurrent extractions**
against a dedicated **`workers=2`** Odoo server and, mid-flight, times a GET
on the unrelated `/web/login` page.

Server: `odoo --database=v06_test --http-port=8073 --workers=2` (workers=2
as the brief specifies), five idle probes averaged, one blocked probe taken
0.5 s into the burst.

### Run A — 5 s simulated Claude round-trip (claude config)

Raw data: `runs/worker-blocking-claude-20260810-222138.csv`

| Metric | Value |
|---|---|
| Idle `/web/login` (avg of 5) | **0.44 s** |
| `/web/login` during 6×5 s extractions | **14.78 s** |
| Degradation | **33.5×** |
| Extraction latency (min / avg / max) | 5.0 s / 10.3 s / 15.6 s |

The 15 s max is exactly the 2-worker queue: 6 requests × 5 s / 2 workers =
3 waves. Worker 0 served requests 0,2,4 (5.0,10.0,15.6 s); worker 1 served
1,3,5 (5.6,10.6,15.0 s). Every unrelated page behind the login is equally
blocked.

### Run B — 50 ms control (baseline config)

Raw data: `runs/worker-blocking-baseline-20260810-222402.csv`

| Metric | Value |
|---|---|
| Idle `/web/login` (avg of 5) | 0.53 s |
| `/web/login` during 6×50 ms extractions | 0.41 s |
| Degradation | **0.8×** (no degradation) |

The same worker count handles the same concurrency fine when the work is
fast — isolating the *latency of the held worker* as the sole cause.

> Note on methodology honesty: a real Anthropic call was not used — the DB
> holds no API key and the `.env` key is a placeholder. The injected sleep
> reproduces the worker-hold semantics (blocking call, held process, request
> queue) deterministically and for free. The mechanism is validated by the
> recorded CSV: per-request elapsed equals the configured delay exactly
> (reported 5.001 s vs configured 5.0 s).

### What stays in Odoo

- `account.move` extension fields, the extraction state machine
  (`pending → processing → extracted → validated | failed`), OCR state.
- Confidence calibration and routing (`models/confidence.py`,
  `confidence_score`, `ai_extraction_state` kanban: Auto / Needs Review /
  Approved, journal thresholds + global parameter override).
- Security: bearer auth, API keys, ACLs, record rules, multi-company.
- The `/invoice_agent/upload` and `/invoice_agent/status/<id>` facades.
  (These become thin proxies that POST the PDF to `invoice-ai`.)

### What moves out

- OCR (Tesseract + pdf2image) — `app/ocr.py`.
- The winning prompt (`prompts/v1.md` → service `prompts/v3.md`) and prompt
  caching (`cache_control` on the frozen system block).
- The Anthropic SDK, API key, model id, and all LLM error mapping
  (429/503 → Retry-After-envelope, etc.).

## Non-goal — no microservice sprawl

This is a *single* extraction service, not the beginning of a fleet. OCR,
extraction, and prompting stay together in `invoice-ai` because they share
one request lifecycle and one contract. **No** per-feature services
(tax-rate lookup, vendor matching, embedding) are spun out. Odoo remains
the orchestrator and the system of record. Any future addition must justify
its own boundary with the same measured evidence standard as this ADR.

## Consequences

- **Positive**: Odoo workers are freed for the actual product (pages,
  journals, workflows); the 33.5× login collapse disappears because the 2
  Odoo workers now only proxy a fast HTTP POST while `invoice-ai` owns the
  slow LLM call and scales independently (`uvicorn --workers N`).
- **Positive**: AI dependencies (`anthropic`, `pytesseract`, `pdf2image`)
  leave the Odoo image; Odoo upgrades no longer move the AI stack.
- **Negative**: one more service to deploy/monitor; Odoo must handle
  `invoice-ai` downtime (it does — the pipeline already degrades to
  `failed` + Needs Review instead of raising).
- **Odoo release cycle**: Odoo's semiannual releases and monolithic image
  no longer gate AI iteration — prompt/schema/model updates deploy with the
  service only.

## References

- Measure script: `scripts/measure_blocking.py`
- Instrumented hook: `custom_addons/invoice_agent/models/llm_service.py`
  (`MEASURE_DELAY_PARAM`), trigger route:
  `custom_addons/invoice_agent/controllers/main.py`
- Service contract: `docs/openapi.yaml` (this repo)
- Service implementation: `invoice-ai/` (this repo)
- Anthropic Messages API: https://platform.claude.com/docs/en/api/messages/create
- Tesseract docs: https://tesseract-ocr.github.io/tessdoc/
- Previous ADRs: `custom_addons/invoice_agent/docs/adr-001-llm-service.md`,
  `custom_addons/invoice_agent/docs/adr-002-ocr-engine.md`
