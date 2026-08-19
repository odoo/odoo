# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.9] — 2026-08-16

### Added

- Async extraction pipeline live: aio-pika worker (`invoice-ai/app/consumer.py`,
  `python -m app.consumer`) consuming `invoice.extract` with prefetch=1,
  manual ack, `connect_robust` reattach, and signed `extract.done` results
- Dead-letter infrastructure: `invoice.extract.dlx` direct exchange,
  `invoice.extract.dead` poison queue, TTL-backed retry ladder
  (`retry.5s` → `retry.30s` → `retry.5m`) chained back to
  `extract.request`; `x-delivery-limit=3` crash safety net on
  `invoice.extract` (a poison PDF can never loop forever)
- Failure classification (`invoice-ai/app/retry.py`): transient
  (429/5xx/connection) rides the ladder by attempt counter; permanent
  (bad schema/malformed) dead-letters immediately; worker publishes a
  signed `status:"failed"` result when dead-lettering
- Idempotency: UNIQUE `invoice.agent.job.job_uuid` +
  `account.move.ai_job_uuid`, and an `invoice.agent.applied.job`
  ledger — the result consumer runs
  `INSERT ... ON CONFLICT DO NOTHING` before applying, so a redelivered
  job never creates a second draft `account.move`
- Odoo Outbox taskboard: Dead-Lettered state, `dead_reason`,
  `x_death_count`, and a **Requeue** button republishing to
  `extract.request`; dead-letter results flag the move for review
- pytest suite covering the retry ladder and worker routing with a fake
  broker (`invoice-ai/tests/test_retry.py`)
- `docs/runbook-v09.md` — cutover runbook (start order, topology init,
  worker health checks, synchronous fallback flag, mid-batch failure
  drill, rollback)
- `docs/plan-v09-dlq-retries-idempotency.md` — the implementation plan
- `docs/queue-contract.md` rewritten for the DLX/retry/idempotency
  contract

### Changed

- `invoice_queue/topology.py` + `invoice-ai/app/amqp.py`: full DLX +
  retry-ladder topology, idempotently declared/re-declared
- `invoice.agent.job` drain publishes the row's own `job_uuid`
  (backfilled from `account.move.ai_job_uuid` on upgrade via hooks.py)
- `_enqueue_ai_job` reuses the existing outbox row (fresh uuid on re-run,
  reset on dead) — never creates a second row for one move

---

## [v0.10] — 2026-08-17

### Added

- pgvector-backed RAG corpus on every **posted** vendor bill
  (`invoice.agent.vendor.doc`): `vector(1024)` column + HNSW cosine index,
  `UNIQUE(move_id)` — a redelivered embed upserts, never duplicates
- Voyage `voyage-3` embeddings via the invoice-ai service: `POST /v1/embed`
  (batched 128, one retry, 1024-dim assertion) + `app/embeddings.py` client
  with a lazy SDK import; Odoo-side `invoice.llm.service.embed_texts()`
  maps 503/connection failure to "deferred" (never failed)
- `account.move._build_rag_document()` — compact one-document-per-bill
  render (header + GL-coded lines) for the future RAG tool
- Live embed on `action_post()` (best-effort) + `ai_indexed` resume marker
  reset on write; 10-minute backfill `ir.cron` (batches of 100, idempotent,
  resume-safe across restarts)
- DB image pinned to `pgvector/pgvector:pg16` in compose and CI; the
  model's own `init()` creates the extension/column/index self-contained,
  so the CI runner needs no initdb hook
- `docs/vector-search.md` (schema bootstrap, querying, HNSW EXPLAIN check,
  failure paths, manual rank acceptance) and `docs/adr-005-pgvector-voyage.md`
- Addon test suite `tests/test_rag.py`: document shape, `write()` reset,
  live-embed success, upsert idempotency — plus the fake-Voyage endpoint
  suite `invoice-ai/tests/test_embeddings.py` (9 tests)

### Changed

- `docker-compose.yml`: db service now uses `pgvector/pgvector:pg16` with
  `shared_preload_libraries=pg_stat_statements,vector` and an initdb mount
  (`docker/initdb/001-vector-extension.sql`) that creates the extension and
  a 3-row demo for the rank acceptance exercise

---

## [v0.11] — 2026-08-19

### Added

- Load test infrastructure: `invoice-ai/locustfile.py` with two user classes
  (`InvoiceExtractorUser` for direct `/v1/extract` testing,
  `FullPipelineUser` for end-to-end AMQP path through Odoo JSON-RPC),
  staged load shape (10→25→50→100 users over 30 min)
- `scripts/generate_test_invoices.py` — synthetic invoice PDF generator
  (10 vendors, 15 line items, realistic VAT/amounts) for load test fixtures
- `docs/load-test-plan.md` — comprehensive guide covering percentiles vs
  averages, Little's Law for consumer pool sizing, coordinated omission,
  LLM pipeline saturation points, and the full 5-phase test methodology
- `docs/load-test.md` — capacity report template with p50/p95/p99 table,
  cost model ($90-$128 per 1K invoices), bottleneck identification, and
  Grafana PromQL queries
- README.md rewritten with architecture diagram (mermaid), 60-second
  quickstart, API endpoint table, config table, monitoring overview, and
  honest limitations section
- CONTRIBUTING.md with development setup, code style (ruff + mypy),
  PR workflow, testing instructions, and conventional commits convention
- `locust>=2.32.0` added to `[project.optional-dependencies] dev` in pyproject.toml
- `docs/launch/go-no-go.md` — launch checklist with rollback triggers (5xx > 2%
  → automatic rollback, p95 > 60s → rollback), pre-launch/cutover/watch phases,
  every line gets an owner + command + checkbox
- `scripts/cutover.sh` — automated deploy/rollback with health check loop,
  targets < 5 minutes for rollback scenarios
- `scripts/smoke-test.sh` — post-deploy smoke suite: service health, extraction
  endpoint, worker status, Prometheus metrics, TLS, optional Locust smoke
- Nginx reverse proxy with HTTP→HTTPS redirect, HSTS, and ACME HTTP-01
  challenge support
- WebSocket proxy with proper `Upgrade`/`Connection` header forwarding
  for Odoo bus/live-chat
- Let's Encrypt auto-renewal via `certbot/certbot` Docker container (12h loop)
- Odoo `proxy_mode = True` via `PROXY_MODE` environment variable
- `certbot-www` and `certbot-conf` named volumes for persistent TLS certificates
- `nginx/conf.d/odoo.conf` — reverse proxy with upstreams for Odoo (8069)
  and websocket (8072)
- `.env.example` — secrets template for docker-compose
- `docs/deployment.md` — deployment runbook covering architecture, DNS,
  nginx semantics, TLS, proxy mode, websocket, CI/CD, secrets, rollback,
  disaster recovery, and troubleshooting
- `docs/reverse-proxy-analysis.md` — deep reference on proxy_mode,
  X-Forwarded-For trust chain, websocket upgrade, ACME HTTP-01, failures

### Changed

- `invoice_agent/__manifest__.py`: summary updated to "AI-powered vendor
  invoice extraction and validation — OCR, Claude structured output,
  RAG validation, confidence-based kanban routing"
- `docker-compose.yml`:
  - Added `nginx:alpine` service (ports 80:80, 443:443)
  - Added `certbot/certbot` service with auto-renewal loop
  - Odoo ports bound to `127.0.0.1` only (loopback)
  - Added `PROXY_MODE: "True"` environment variable to Odoo
  - Added named volumes: `certbot-www`, `certbot-conf`
- `.github/workflows/deploy.yml`:
  - Health check polls HTTPS through nginx (full path validation)
  - Added websocket endpoint verification (expects HTTP 101)
  - Fallback to direct Odoo check if nginx is down

### Security

- Port 8069 no longer exposed to the internet (127.0.0.1 binding only)
- HSTS with `max-age=31536000; includeSubDomains`
- TLS 1.2 and 1.3 only with modern cipher suite
- ACME challenge location serves before HTTP→HTTPS redirect
---

## [v0.3] — 2026-07-20

### Added

- `invoice_agent` custom addon with AI fields on `account.move`
- CI pipeline (`ci.yml`): ruff lint + Odoo tests with PostgreSQL service
- Deploy pipeline (`deploy.yml`): SSH → compose rebuild → upgrade → health check → rollback
- `docker-compose.yml` with Postgres 16 and Odoo 19 services
- `Dockerfile` with Tesseract, Ghostscript, Poppler for PDF/image processing
- Postgres healthcheck in compose
- Resource limits (memory reservations/limits) for db and odoo services
- Logging configuration (json-file, 10MB max, 3 files rotation)

### Docs

- `docs/design.md` — core accounting mechanics, balance invariants, posting flow, AI extraction fields
