# Assumptions, Unknowns & Constraints

**Workspace:** tx10-odoo | **Branch:** 19.0 (FINAL) | **Last updated:** 2026-05-22
**Evidence sources:** `setup.cfg`, `requirements.txt`, `odoo/release.py`, `setup.py`

---

## Phase 7 User Input (HITL)

Clarified in HITL conversation (2026-05-22):
- **Deployment context:** Learning/research + Development/testing (NOT production)
- **Business modules configured:** None yet (fresh clone, not configured)
- **CI/CD pipeline:** None yet (not needed in research phase)
- **Critical research goal:** "How can Odoo become an AI-first CRM/ERP system?"

---

## Known Assumptions

These are inferred from the codebase and treated as true unless the operator confirms otherwise.

### Deployment Context

| Assumption | Status | Source |
|------------|--------|--------|
| This is a research-stage deployment | **Confirmed** | Phase 7 HITL |
| No production data or users affected | **Confirmed** | Phase 7 HITL |
| Development/testing environment only | **Confirmed** | Phase 7 HITL |
| AI integration is a primary research goal | **Confirmed** | Phase 7 HITL |

### Runtime Environment

| Assumption | Evidence | Source |
|------------|----------|--------|
| Python 3.10 or newer required | `MIN_PY_VERSION = (3, 10)` | `odoo/release.py` |
| Python < 3.14 required | `MAX_PY_VERSION = (3, 14)` | `odoo/release.py` |
| PostgreSQL 13 or newer required | `MIN_PG_VERSION = (13,)` | `odoo/release.py` |
| psycopg2 used as DB adapter | `psycopg2` in install_requires | `setup.py` |
| gevent available only on Linux/macOS | `python-ldap` marked Linux-only; gevent absent on Windows | `requirements.txt`, `setup.py` |
| Windows requires pypiwin32 fallback | `pypiwin32` listed as Windows dependency | `requirements.txt` |

### Build & Packaging

| Assumption | Evidence | Source |
|------------|----------|--------|
| Namespace packages used (`odoo.*`) | `find_namespace_packages(where='.')` | `setup.py` |
| CLI entry point is `setup/odoo` script | `scripts=['setup/odoo']` | `setup.py` |
| Linting via Ruff (primary) + Flake8 (RST) | `ruff.toml` + `[flake8]` section | `ruff.toml`, `setup.cfg` |
| 103 pinned dependency versions | Line count in requirements.txt | `requirements.txt` |

### Module System

| Assumption | Evidence | Source |
|------------|----------|--------|
| Each addon declares its own dependencies | `depends` key in `__manifest__.py` | Pattern: module-addon-structure |
| Module load order is topologically sorted | `odoo/modules/graph.py` | `docs/CODEMAP.md` |
| Single database per Odoo instance | `db_name` config key (single value) | Odoo config conventions |

---

## Unknowns — Research Needed

Items not determinable from the repository alone. Some resolved in Phase 7 HITL; others remain open for future phases.

### Deployment (Phase 7 RESOLVED)

| Unknown | Status | User Answer |
|---------|--------|-------------|
| Deployment target (Docker, Kubernetes, bare metal, Odoo.sh) | **RESOLVED** | Development/testing (not production) |
| CI/CD pipeline required | **RESOLVED** | None yet (not needed in research phase) |
| Business modules configured | **RESOLVED** | None yet (fresh clone) |

### AI Integration (NEW — Phase 7+ Priority)

| Research Topic | Why it matters | Candidate patterns |
|---|---|---|
| **LLM API injection points** | Where to call Claude/GPT from Odoo business logic (models, controllers, views) | Decorator patterns on model methods, custom field compute functions, wizard integration |
| **AI-driven field computation** | Fields that use LLM for values (summaries, classifications, predictions) | Field.compute + async calls to Claude API |
| **Workflow automation with AI decisions** | Triggers that use LLM output to transition workflow states | ir.actions + AI decision logic, email automation with AI classification |
| **Custom field types for AI outputs** | Data types for storing/rendering LLM structured outputs (embeddings, classifications, summaries) | Custom field classes extending ir.fields.Field |
| **Prompt engineering for Odoo context** | How to structure Claude prompts with Odoo business context (customer data, historical records) | Mixin patterns + context building in compute methods |

### Operations (Not yet prioritized)

| Unknown | Why it matters | Status |
|---------|---------------|--------|
| Performance baseline (concurrent users, response time SLA) | Required for optimization decisions | Deferred (research phase) |
| Logging and monitoring stack (ELK, Datadog, etc.) | Affects observability setup | Deferred (research phase) |
| Backup and recovery strategy | Required for RTO/RPO planning | Deferred (research phase) |

### Localization (Not yet relevant)

| Unknown | Why it matters | Status |
|---------|---------------|--------|
| Active `l10n_*` modules (country-specific accounting rules) | Determines which localization patches are relevant | Deferred (no localization needed for research) |
| Primary language(s) of end users | Affects i18n testing and PO file maintenance | Deferred (English only for research) |

---

## Constraints

These are fixed limits that must be respected regardless of operator preference.

### Branch Policy (19.0 FINAL)

- No new features — only bug fixes and security patches
- All commits must follow the `[TAG] module: description` convention (e.g., `[FIX] account: ...`, `[IMP] sale: ...`)
- Breaking changes to existing APIs are not permitted

### Upstream Contribution

- CLA (Contributor License Agreement) required for any PR to `github.com/odoo/odoo`
- Runbot CI must pass before merge
- Code review by Odoo S.A. maintainers required for upstream acceptance

### Security

- Raw SQL that bypasses the ORM also bypasses Odoo's record-rule security layer
- `ir.model.access.csv` must be present for every new model or the module will fail to install
- Field-level `groups=` restrictions are enforced at the ORM read level, not the view level

### Licensing

- All community contributions must be compatible with LGPL-3
- Proprietary modules must not be placed in `addons/` (this directory is LGPL)
- OWL (Odoo Web Library) is licensed separately under LGPL

---

## Related Documentation

- [docs/TECHSTACK.md](./TECHSTACK.md) — version matrix for all runtime dependencies
- [docs/DEPENDENCIES.md](./DEPENDENCIES.md) — full pinned dependency list
- [docs/ARCHITECTURE.md](./ARCHITECTURE.md) — technical architecture and security model
