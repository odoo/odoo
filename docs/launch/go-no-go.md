# Go/No-Go Checklist — Invoice Agent v1.0.0 Launch

> **Owner:** [Your name]  
> **Launch window:** [Date] 09:00–12:00 UTC  
> **Code freeze:** [Date -1] 18:00 UTC — `main` locked at `v1.0.0-rc1`  
> **Rollback window:** First 4 hours post-cutover  
> **Rollback trigger:** Any hard NO blocks deployment; any soft NO blocks until resolved or owner signs off

---

## Rollback Triggers (Decide Now, Not Tomorrow)

| Metric | Threshold | Action |
|--------|-----------|--------|
| HTTP 5xx rate | > 2% for 5 minutes | **AUTOMATIC ROLLBACK** |
| p95 extraction latency | > 60s for 10 minutes | **AUTOMATIC ROLLBACK** |
| Odoo login failures | > 5 in 2 minutes | **ROLLBACK** (DB migration broke auth) |
| RDS connection errors | > 10 in 5 minutes | **ROLLBACK** (pool exhaustion) |
| Certbot renewal failing | Certificate expiring < 24h | **ESCALATE** (not rollback, but urgent) |
| Anthropic 429 rate | > 10/min sustained | **SCALE UP** workers, not rollback |
| Queue depth > 50 for 15 min | Worker bottleneck | **SCALE UP** workers, not rollback |

**Decision authority:** If the on-call person is unavailable, the deployer rolls back unconditionally. No partial rollbacks — full revert to `v0.11` tag.

---

## Phase 0: Pre-Launch (Day Before)

### Infrastructure

- [ ] **RDS snapshot verified**
  - Owner: `_____`
  - Command: `aws rds describe-db-snapshots --db-instance-identifier invoice-agent --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[:1]'`
  - Expected: Snapshot from today, status `available`
  - [ ] Snapshot timestamp: `_____`
  - [ ] Snapshot status: `_____`

- [ ] **S3 backup bucket verified**
  - Owner: `_____`
  - Command: `aws s3 ls s3://${PREFIX}-backups/daily/ --recursive | tail -5`
  - Expected: Dump file from today, size > 10MB

- [ ] **DR drill passed** (ran within last 7 days)
  - Owner: `_____`
  - Command: `cat docs/runbooks/disaster-recovery.md | grep "Last drilled"` 
  - [ ] DR drill date: `_____`

- [ ] **DNS TTL lowered to 60 seconds**
  - Owner: `_____`
  - Command: `dig +short invoices.<domain>` (verify ALB IP, not old)
  - [ ] TTL confirmed: `_____` seconds

- [ ] **SSL certificate valid > 30 days**
  - Owner: `_____`
  - Command: `echo | openssl s_client -connect invoices.<domain>:443 2>/dev/null | openssl x509 -noout -dates`
  - [ ] Expiry: `_____`

### Security

- [ ] **OWASP ZAP scan green**
  - Owner: `_____`
  - Command: `zap-cli quick-scan -s all -r https://invoices.<domain>`
  - Expected: 0 High, 0 Medium findings
  - [ ] High findings: `_____`
  - [ ] Medium findings: `_____`

- [ ] **Security headers present**
  - Owner: `_____`
  - Command: `curl -sI https://invoices.<domain> | grep -i "strict-transport-security\|x-frame-options\|content-security-policy"`
  - Expected: HSTS present, CSP present

### Monitoring

- [ ] **Alertmanager routing confirmed**
  - Owner: `_____`
  - Command: `amtool config route show` (or check Alertmanager UI)
  - [ ] Slack channel receiving test alerts: `_____`
  - [ ] PagerDuty/OpsGenie: `_____`

- [ ] **Grafana SLO dashboard loading**
  - Owner: `_____`
  - URL: `https://grafana.<domain>/d/agent-slo`
  - [ ] All panels rendering: `_____`

- [ ] **Prometheus targets healthy**
  - Owner: `_____`
  - Command: `curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | map(.health) | group_by(.) | map({status: .[0], count: length})'`
  - Expected: All targets `up`

### Code

- [ ] **v1.0.0-rc1 tagged and pushed**
  - Owner: `_____`
  - Command: `git log --oneline v1.0.0-rc1 -1`
  - [ ] Commit hash: `_____`

- [ ] **CI green on v1.0.0-rc1**
  - Owner: `_____`
  - Command: Check GitHub Actions status badge
  - [ ] All checks passing: `_____`

- [ ] **CHANGELOG.md reflects v1.0.0-rc1**
  - Owner: `_____`
  - Command: `grep "v0.11" CHANGELOG.md`
  - [ ] Entries present: `_____`

---

## Phase 1: Cutover Day (T-0: Launch Hour)

### T-0:00 — Freeze and Pre-Flight

- [ ] **Code freeze confirmed**
  - Owner: `_____`
  - Command: `git log --oneline main -3` — no commits after rc1
  - [ ] Last commit: `_____`

- [ ] **Maintenance page ready** (fallback if deployment stalls)
  - Owner: `_____`
  - Command: Verify nginx returns 503 when maintenance flag is set
  - [ ] Tested: `_____`

### T+0:05 — Deploy

- [ ] **GitHub Actions deploy triggered**
  - Owner: `_____`
  - Command: `git tag -a v1.0.0 -m "Release v1.0.0" && git push origin v1.0.0`
  - Or: trigger deploy workflow manually from GitHub UI
  - [ ] Workflow ID: `_____`
  - [ ] Deploy started: `_____` UTC

- [ ] **Watch the deploy**
  - Owner: `_____`
  - Monitor: `gh run watch` or GitHub Actions UI
  - [ ] Build stage passed: `_____` UTC
  - [ ] Test stage passed: `_____` UTC
  - [ ] Deploy stage passed: `_____` UTC
  - [ ] Health check passed: `_____` UTC

### T+0:10 — Post-Deploy Verification

- [ ] **Odoo responding**
  - Owner: `_____`
  - Command: `curl -sI https://invoices.<domain>/web/login | head -1`
  - Expected: `HTTP/2 200` (or 302 redirect to login)
  - [ ] Response: `_____`

- [ ] **invoice-ai responding**
  - Owner: `_____`
  - Command: `curl -s https://invoices.<domain>/healthz` (via internal)
  - Expected: `{"status":"ok","build_sha":"..."}`
  - [ ] Build SHA: `_____`

- [ ] **RabbitMQ management UI accessible**
  - Owner: `_____`
  - Command: Check queues via management API or compose exec
  - [ ] Queues healthy: `_____`

- [ ] **Worker connected and consuming**
  - Owner: `_____`
  - Command: `docker compose logs worker --tail 5 | grep "consuming"`
  - [ ] Worker log: `_____`

### T+0:15 — Smoke Test

- [ ] **Upload a real invoice via UI**
  - Owner: `_____`
  - Steps:
    1. Login to Odoo at `https://invoices.<domain>`
    2. Go to Invoicing → Vendors → Bills → Create
    3. Upload a scanned PDF
    4. Watch extraction status: pending → processing → extracted
    5. Review AI-suggested fields
    6. Approve and post
  - [ ] Invoice created: `_____` (move_id)
  - [ ] Extraction completed: `_____` UTC
  - [ ] Confidence score: `_____`
  - [ ] Invoice posted: `_____` UTC

- [ ] **Verify extraction in Grafana**
  - Owner: `_____`
  - Check: `invoice_worker_jobs_total{status="done"}[5m]` > 0
  - [ ] Jobs processed: `_____`

### T+0:20 — First Invoice Posted

- [ ] **Ledger entry confirmed**
  - Owner: `_____`
  - Command: Check the posted invoice in Odoo accounting
  - [ ] Journal entry correct: `_____`
  - [ ] Amount matches scanned PDF: `_____`

### T+0:30 — Monitoring Window (30 minutes)

- [ ] **p95 latency stable** (< 30s)
  - Owner: `_____`
  - Grafana: Agent SLO dashboard → Pipeline Breakdown → Claude API Duration
  - [ ] p95: `_____` s

- [ ] **Error rate zero**
  - Owner: `_____`
  - Grafana: Agent SLO Overview → Error Rate
  - [ ] Error rate: `_____`%

- [ ] **Queue depth = 0**
  - Owner: `_____`
  - Grafana: Agent SLO → Worker & Queue → Queue Depth
  - [ ] Queue depth: `_____`

- [ ] **No alerts firing**
  - Owner: `_____`
  - Command: `amtool alert instances` (or check Slack)
  - [ ] Active alerts: `_____`

- [ ] **Token spend nominal**
  - Owner: `_____`
  - Check: `invoice_claude_tokens_total` rate
  - [ ] Tokens/min: `_____`

---

## Phase 2: First Hour Watch

### T+1:00 — Hourly Check

- [ ] **p95 still stable**
  - [ ] p95: `_____` s

- [ ] **Error rate still zero**
  - [ ] Error rate: `_____`%

- [ ] **No 429s from Anthropic**
  - [ ] 429 rate: `_____`

- [ ] **All workers alive**
  - `docker compose ps worker`
  - [ ] Worker count: `_____`

- [ ] **RDS connections nominal**
  - `SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();`
  - [ ] Connections: `_____` / 200 max

### T+2:00, T+3:00, T+4:00 — Repeat Hourly Checks

- [ ] **T+2:00**: p95=`_____`s, errors=`_____`%, queue=`_____`
- [ ] **T+3:00**: p95=`_____`s, errors=`_____`%, queue=`_____`
- [ ] **T+4:00**: p95=`_____`s, errors=`_____`%, queue=`_____`

---

## Phase 3: Rollback (If Needed)

### Rollback Procedure (target: < 5 minutes)

```bash
# 1. Trigger rollback (GitHub Actions)
gh workflow run deploy.yml -f tag=v0.11

# OR manual rollback:
# 2. Pull previous image
docker compose pull odoo worker invoice-ai

# 3. Recreate containers with previous tag
docker compose up -d --force-recreate odoo worker invoice-ai

# 4. Verify health
curl -s https://invoices.<domain>/healthz
docker compose logs worker --tail 3

# 5. Confirm Odoo login works
curl -sI https://invoices.<domain>/web/login
```

### Rollback Verification

- [ ] **Odoo responding after rollback**
  - [ ] Response: `_____`

- [ ] **Worker consuming after rollback**
  - [ ] Worker log: `_____`

- [ ] **No data loss**
  - [ ] Check: Draft bills created during deploy window preserved: `_____`
  - [ ] Check: Posted invoices preserved: `_____`

- [ ] **Alerts cleared**
  - [ ] Active alerts: `_____`

### Rollback Decision Log

| Time | Trigger | Decision | Notes |
|------|---------|----------|-------|
| | | | |
| | | | |
| | | | |

---

## Phase 4: Announcement (T+2:00 minimum)

Only announce after all Phase 2 hourly checks pass.

- [ ] **Launch blog post published**
  - Owner: `_____`
  - URL: `_____`

- [ ] **Demo GIF embedded in post**
  - [ ] GIF link: `_____`

- [ ] **Load-test numbers in post**
  - [ ] p95: `_____`, throughput: `_____`, cost/invoice: `_____`

- [ ] **LinkedIn post published**
  - Owner: `_____`
  - [ ] URL: `_____`

- [ ] **Odoo community post published**
  - Owner: `_____`
  - [ ] URL: `_____`

- [ ] **GitHub repository visibility set to public**
  - Owner: `_____`
  - [ ] Confirmed: `_____`

- [ ] **Portfolio page updated**
  - Owner: `_____`
  - [ ] Architecture diagram visible: `_____`

---

## Phase 5: Post-Launch (First Night + 3 Months)

### First Night (00:00–08:00 UTC)

- [ ] **Dashboards watched**
  - Owner: `_____` (on-call rotation)
  - Tool: Grafana mobile alerts + Slack
  - [ ] Any incidents logged as GitHub issues (not hotfixes): `_____`

### One Week Post-Launch

- [ ] **No critical bugs in 7 days**
  - [ ] Open issues count: `_____`
  - [ ] Closed issues count: `_____`

- [ ] **Load test baseline established**
  - [ ] Actual invoices processed: `_____`
  - [ ] Actual p95: `_____`
  - [ ] Actual cost/invoice: `_____`

### Three-Month Retrospective

- [ ] **Retrospective written**
  - Owner: `_____`
  - File: `docs/retrospective-v1.md`
  - Sections: What shipped, what it cost, what broke, what comes next
  - [ ] Published: `_____`

---

## Signing Off

### Pre-Launch Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Deploy owner | | | |
| Backend lead | | | |
| Infrastructure lead | | | |
| Security reviewer | | | |

### Post-Launch Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Deploy owner | | | |
| First-hour watcher | | | |
| Announcement publisher | | | |

---

## Appendix: Timeline Summary

```
Day Before (T-1):
  18:00  Code freeze — main locked at v1.0.0-rc1
  18:30  Verify RDS snapshot, S3 backup, DR drill
  19:00  Lower DNS TTL to 60s
  19:30  Confirm alert routing (Slack test)
  20:00  Review this checklist, sign pre-launch section

Launch Day (T=0):
  08:30  Final pre-flight: all Phase 0 checkboxes green
  09:00  Tag v1.0.0, push, trigger deploy
  09:05  Watch deploy (build → test → deploy → health check)
  09:15  Post-deploy verification (Odoo, invoice-ai, RabbitMQ)
  09:20  Smoke test: upload real invoice
  09:30  First hour monitoring begins
  10:30  Second hour check
  11:30  Third hour check
  12:30  Fourth hour check — IF ALL GREEN → announce
  13:00  Publish launch post, LinkedIn, Odoo community
  13:30  Set repository to public
  22:00  Night watch begins (on-call rotation)

Day After (T+1):
  08:00  First morning check — 24h uptime confirmed
  10:00  Review any overnight issues, create GitHub issues
