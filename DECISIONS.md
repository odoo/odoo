# Decision Log

Architectural and process decisions with rationale.
Read this before changing any project-wide convention — it explains the *why*.

---

## 2026-06-13 — Development environment: Miniconda (not Docker or venv)

**Decision:** Use conda env `odoo19` (Python 3.12) on Windows via Miniconda.

**Alternatives considered:**
- Docker: good for team/production but adds overhead for solo local dev cycle
- venv: works but conda handles Python version pinning and binary Windows deps more reliably

**Rationale:** Developer already uses Miniconda for multiple projects; conda isolates the env cleanly. Docker/K8s preferred for deployment — local dev stays fast with conda + native PostgreSQL.

**Consequence:** `odoo.conf` is gitignored; each developer creates their own locally. PostgreSQL must be installed natively before the database can be initialised.

---

## 2026-06-13 — CLAUDE.md as 91-line entry file (not encyclopedia)

**Decision:** Split CLAUDE.md into a routing entry file + topic documents under `up5-docs/`.

**Rationale:** Liu et al. (2023) "lost in the middle" — LLMs process document extremes better than the centre. A 300-line file consumes 10–20K tokens before any task work begins, and critical constraints buried mid-file get ignored. Entry file routes to topic docs; context budget goes to task work.

**Consequence:** `up5-docs/standards/odoo-conventions.md` is the authoritative Odoo convention reference. Hard constraints sit at the top of CLAUDE.md where they are always read.

---

## 2026-06-13 — `up5_` prefix for all custom modules

**Decision:** All UP5 TECH custom Odoo modules use the `up5_` prefix.

**Rationale:** Distinguishes custom from upstream at a glance. Agents and developers immediately know what can be modified vs. what must be extended via `_inherit`.

**Consequence:** Any module without the `up5_` prefix is upstream Odoo — extend only, never patch directly.

---

## 2026-06-13 — WIP=1 task discipline

**Decision:** Only one task may be `in-progress` in `feature_list.json` at a time. A task is not done until `./verify.sh` output is pasted as `evidence` and status is `done`. The next task cannot be activated until VCR (verified tasks ÷ activated tasks) = 1.0.

**Alternatives considered:**
- Parallel feature work: faster apparent progress but produces code without passing end-to-end verification — the REST API study showed 20% pass rate vs. 100% with WIP=1
- Trusting "code looks correct" as done: subjective, unverifiable, and the primary cause of under-finished sessions

**Rationale:** Agents have finite context (C). Activating k tasks simultaneously gives each C/k reasoning capacity — below a threshold, none finish. WIP=1 concentrates full context on one task, producing fewer but completed features per session.

**Consequence:** Session Start must check for `in-progress` tasks with empty `evidence` and resume them before touching anything else. A broad prompt that implies multiple simultaneous tasks must be scoped to one at a time.

---

## 2026-06-13 — `verify.sh` as single verification command

**Decision:** `./verify.sh <module>` runs ruff lint + Odoo tests as one non-skippable step.

**Rationale:** Feedback subsystem has the highest ROI (lecture 02). A single command eliminates the verification gap — agents cannot skip lint by running only tests or vice versa. Definition of Done requires its output pasted.

**Consequence:** No task is done without `./verify.sh` output as evidence. No exceptions.

---

<!-- Add new decisions above this line in the format:
## YYYY-MM-DD — Short title

**Decision:** What was decided.
**Alternatives considered:** What else was on the table.
**Rationale:** Why this choice over the alternatives.
**Consequence:** What this decision locks in or rules out.
-->
