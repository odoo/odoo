# RELEASE.md — v0.6 "Hardened extraction" release checklist

Target: move the extraction pipeline from "works on my machine" to
"operators and accountants can trust it under load". Every item below is a
gate; v0.6 ships only when the whole checklist is green.

## 0. Freeze scope: walk the diff

```bash
git fetch --tags && git log v0.5..HEAD --oneline
```

The v0.6 diff covers exactly these areas (nothing else):

1. **Exception hardening** — `invoice.llm.service._map_sdk_error` maps
   `NotFoundError` / `RateLimitError` (reads `Retry-After`) / `APIStatusError`
   / `APIConnectionError` to distinct accountant-readable `UserError`s.
2. **Prompt caching** — the frozen instructions + rendered chart of accounts
   are sent as `system=[{..., "cache_control": {"type": "ephemeral"}}]`; the
   volatile invoice text stays last in `messages`. Second+ calls show
   non-zero `usage.cache_read_input_tokens` (>= 4096-token prefix on
   `claude-opus-4-8`).
3. **Usage ledger** — `invoice.agent.usage` (model + ACLs + list view grouped
   by month) logs input/cache-write/cache-read/output tokens and a `cost`
   computed at Opus rates; "AI Usage & Spend" sits under Invoicing > Vendors.
4. **Load test + release docs** — `scripts/loadtest_extractions.py`,
   `RELEASE.md` (this file).

## 1. Update step (the only supported upgrade path)

```bash
cd /opt/odoo && git pull origin production
docker compose up -d --build
docker compose exec -T odoo odoo -d <db> -u invoice_agent \
    --db_host=db --db_user=odoo --db_password=odoo --stop-after-init
docker compose restart odoo
```

`-u invoice_agent --stop-after-init` materialises the new table
(`invoice_agent_usage`), its indexes and the ACL rows. Re-run it for every
database on the host.

## 2. New configuration parameters (all optional; defaults safe)

| Parameter | Where | Default | Notes |
|---|---|---|---|
| `invoice_agent.anthropic_api_key` | Settings → Invoice Agent | — | Required. Never commit the value. |
| `invoice_agent.anthropic_model` | Settings → Invoice Agent | `claude-opus-4-8` | Overridable per installation. |
| `ANTHROPIC_API_KEY` env var | `docker-compose.yml` odoo service | — | Used by the SDK when the settings field is empty. |

SDK retry policy: `max_retries=2` (idempotent 429/408/5xx) + 90 s timeout,
both pinned in `models/llm_service.py`.

## 3. Verification gates

### 3.1 Tests

```bash
python odoo-bin -c config/odoo.conf -d v06_test -i invoice_agent \
    --test-enable --test-tags /invoice_agent --stop-after-init
```

All mocked (offline) tests green, including `test_llm_errors` (exception
chain) and `test_usage` (ledger + cost + MTD spend).

### 3.2 Golden-set accuracy

```bash
python scripts/eval_extraction.py --live   # requires ANTHROPIC_API_KEY
```

Accuracy must be >= the day-three baseline recorded in
`docs/performance.md` (Week-seven baseline line).

### 3.3 Prompt-cache proof (two sequential real calls)

```python
# odoo-bin shell
svc = env["invoice.llm.service"]
r1 = svc.extract_invoice("INVOICE ... first")
r2 = svc.extract_invoice("INVOICE ... second")
print(r1["usage"]["cache_creation_input_tokens"], r2["usage"]["cache_read_input_tokens"])
# Expect: first call creates the prefix, second call reads it -> r2 cache_read > 0
```

### 3.4 Load test

```bash
venv\Scripts\python.exe odoo-bin shell -d <db> \
    -c "exec(open('scripts/loadtest_extractions.py').read())"
```

20 concurrent extractions: all succeed, cache reads register in the usage
ledger, month-to-date spend > 0. Record the observed cache-hit rate and
cost-per-invoice into the PR description as before/after evidence.

### 3.5 Live smoke test behind nginx HTTPS

Log into the production URL, open a real draft vendor bill, click
**Suggest with AI**, confirm fields populate. In parallel:

```bash
docker compose logs -f odoo
docker compose logs -f nginx
```

Watch for nginx 502s or `proxy_read_timeout` cutoffs on the slower Claude
request (current `proxy_read_timeout 720s` comfortably covers a 90 s SDK
timeout; only raise it if Claude regularly exceeds it).

## 4. Rollback path (exact)

The deploy pipeline snapshots the DB before upgrading. To roll back v0.6:

```bash
cd /opt/odoo
git reset --hard v0.5                 # source back to the tagged release
docker compose up -d --build          # rebuild the previous image
docker compose exec -T db psql -U odoo -d postgres \
    -f /tmp/pre_deploy_<timestamp>.sql # restore the pre-upgrade snapshot (all DBs)
docker compose restart odoo
```

Verify with a health check through nginx:

```bash
curl -s -o /dev/null -w "%{http_code}
" https://<domain>/web/login   # expect 200/303
```

Note: `invoice_agent_usage` rows created under v0.6 that are *not* in the
snapshot are lost on DB rollback — the accepted trade-off for a point-in-time
restore. If you must keep them, dump the table first:

```bash
docker compose exec -T db pg_dump -U odoo -d <db> -t invoice_agent_usage > usage_backup.sql
```

## 5. Release notes skeleton (GitHub release for v0.6)

* What shipped: error-chain hardening, prompt caching with COA prefix,
  token/cost ledger + AI Usage view, load-test harness.
* Measured accuracy: paste the golden-set overall % from 3.2.
* Cost per invoice: paste cost-per-invoice from 3.4.
* Top three failure modes for week seven (as observed):
  1. `RateLimitError` bursts at peak hours (mitigated by Retry-After + retries).
  2. `APIConnectionError` on the EC2 egress path (nginx timeouts / VPC NAT).
  3. Low-confidence vendor-name mismatches on invoices without a VAT number.
