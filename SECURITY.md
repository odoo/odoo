# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public GitHub issue.**

- **Email:** security@yourdomain.com
- **GitHub:** Use the [private security advisory](https://github.com/7ananSaif/odoo/security/advisories/new) feature

Include:
- Steps to reproduce
- Affected version / commit SHA
- Potential impact assessment
- Suggested fix (if any)

We aim to acknowledge within 48 hours and provide a fix or mitigation plan
within 7 days for critical issues.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅        |
| Older branches | ❌ |

---

## Security Gates (Every Pull Request)

| Tool       | Scope                    | Fail on        | Config                        |
|------------|--------------------------|----------------|-------------------------------|
| **Bandit** | Python SAST (Odoo addon + invoice-ai) | HIGH, MEDIUM | `-ll` severity filter          |
| **Trivy**  | Container images (Odoo Dockerfile + invoice-ai Dockerfile) | CRITICAL, HIGH | `--exit-code 1`               |
| **ZAP**    | Web application baseline scan | FAIL alerts   | `zap-baseline.py` against staging |

## Triage Legend

| Status | Meaning |
|--------|---------|
| **Real finding** | Must be fixed before merge |
| **False positive** | Documented below with ZAP alert ID / Bandit test ID and rationale |
| **Accepted risk** | Owner + expiry date documented below |

---

## OWASP Web Top 10 — Current Posture

| # | Category | Status | Notes |
|---|----------|--------|-------|
| A01 | Broken Access Control | ✅ Hardened | Record rules on all `invoice_agent` models restrict by `company_ids`. Portal user isolation tested. |
| A02 | Cryptographic Failures | ✅ OK | HS256 JWT with 60s TTL. TLS 1.2+ via Let's Encrypt. Quarterly secret rotation documented. |
| A03 | Injection | ✅ Hardened | ORM prevents SQL injection. OCR text wrapped in `<<<SCAN_CONTENT>>>` delimiters for prompt injection isolation. |
| A04 | Insecure Design | ✅ Hardened | slowapi rate limiting on FastAPI endpoints (10/min extract, 30/min embed). Upload size enforced. |
| A05 | Security Misconfiguration | ✅ Hardened | CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy via Nginx. |
| A06 | Vulnerable Components | ✅ Gated | Trivy + pip-audit in CI. Container images scanned on every PR. |
| A07 | Auth Failures | ✅ OK | JWT auth on service-to-service endpoints. `auth_password_policy` addon available. |
| A08 | Software/Data Integrity | ⚠️ Planned | AMQP results are JWT-signed. `extract.request` signing is a planned enhancement. |
| A09 | Logging/Monitoring Failures | ✅ OK | Prometheus + Grafana with 7 alert rules. Security alerts for auth spikes planned. |
| A10 | SSRF | ✅ OK | No outbound HTTP to user-controlled URLs. OCR processes uploaded bytes only. |

## OWASP LLM Top 10 — Current Posture

| # | Category | Status | Notes |
|---|----------|--------|-------|
| LLM01 | Prompt Injection | ✅ Hardened | Triple mitigation: delimiters in claude.py + anti-injection in v3.md system prompt + schema validation on output. |
| LLM02 | Sensitive Info Disclosure | ✅ OK | Data stays within authenticated Odoo boundary. No log of raw OCR text at INFO level. |
| LLM03 | Supply Chain | ✅ Gated | Pinned versions in pyproject.toml/requirements.txt. Trivy + pip-audit in CI. |
| LLM04 | Data Poisoning | ✅ Mitigated | Confidence filter on RAG corpus embedding (`confidence_score >= 0.5`). |
| LLM05 | Improper Output Handling | ✅ OK | `json.loads` on Claude output with ValueError handling. Client never sends payload values. |
| LLM06 | Excessive Agency | ✅ OK | Claude extracts structured data only — no tools, no function calling, no code execution. |
| LLM07 | System Prompt Leakage | ⚠️ Low risk | Prompt contains no secrets. Anti-leakage instruction added. |
| LLM08 | Vector/Embedding Weaknesses | ✅ OK | pgvector HNSW index. Embeddings L2-normalized by Voyage API. |
| LLM09 | Misinformation | ✅ Mitigated | Three-tier confidence routing prevents auto-posting of untrusted extractions. |
| LLM10 | Unbounded Consumption | ⚠️ Planned | Daily token budget and spend alert are planned enhancements. |

---

## False Positive Registry

### ZAP Alerts

| Alert ID | Alert Name | Verdict | Rationale |
|----------|-----------|---------|-----------|
| (fill in after ZAP scan) | | | |

### Bandit Findings

| Test ID | Test Name | Verdict | Rationale |
|---------|----------|---------|-----------|
| (fill in after bandit run) | | | |

### Accepted Risks

| Risk | Owner | Expiry | Justification |
|------|-------|--------|---------------|
| AMQP `extract.request` messages not signed | (owner) | (date) | Internal VPC only; requires broker compromise to exploit |
| No account lockout on Odoo login | (owner) | (date) | Mitigated by Nginx rate limiting; `auth_password_policy` addon available |
| No daily LLM token budget | (owner) | (date) | Prometheus alert on daily spend is the planned mitigation |

---

## Secrets Management

| Secret | Storage | Access Method |
|--------|---------|---------------|
| RDS master password | AWS Secrets Manager | Terraform + migration script |
| Odoo DB password | AWS Secrets Manager | EC2 instance IAM role |
| Redis AUTH token | AWS Secrets Manager | EC2 instance IAM role |
| `ANTHROPIC_API_KEY` | AWS Secrets Manager | EC2 instance IAM role |
| `INVOICE_AI_JWT_SECRET` | AWS Secrets Manager | EC2 instance IAM role |
| `RABBITMQ_DEFAULT_PASS` | AWS Secrets Manager | EC2 instance IAM role |
| Docker/Compose `.env` | EC2 filesystem | Not in git, manual only |
| GitHub Actions secrets | GitHub repo settings | CI/CD pipeline |
