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

## 2026-06-13 — Clean state as a completion criterion (lecture 12)

**Decision:** Every session must exit across all five clean state dimensions: build passes, tests pass (including pre-existing), progress recorded, no temporary artifacts, startup path functional. These are non-negotiable — a session missing any dimension is incomplete and must stash rather than commit. Artifact hygiene (no debug prints, commented code, untracked TODOs) is Hard Constraint #14.

**Alternatives considered:**
- Clean up in the next session: Lehman's entropy law confirms systems undergoing continuous change grow more complex without active management — "next session" functionally means never
- Build-only validation as clean state: code compiling ≠ clean state; tests, documentation, and artifact hygiene are equally non-negotiable

**Rationale:** 12-week Electron app study: without cleanup discipline, week 12 build success 68%, test pass 61%, startup 60+ minutes. With cleanup: 97% / 95% / 9 minutes — 29-34 percentage point improvement and 85% faster startup from 5 minutes per-session overhead.

**Consequence:** `clean-state-checklist.md` is the physical exit checklist (five dimensions with specific checks). `quality-document.md` tracks module health scores (A-F) across verification, understandability, test stability, architectural compliance, and code conventions. Session End step 6 explicitly confirms Dimension 4 before committing.

---

## 2026-06-13 — Sprint contracts and runtime observability (lecture 11)

**Decision:** Before writing any code on an `active` task, a sprint contract must be written in `claude-progress.md`: behavior (from feature_list.json), in-scope criteria, explicit out-of-scope list, verification command, and resolved ambiguities. Session End step 2 requires WHY rationale for non-obvious decisions — this is the task trace.

**Alternatives considered:**
- Start coding immediately from feature_list.json criteria: scope misalignment surfaces at Layer 2/3 verification, the most expensive recovery point
- Verbal sprint contract (not written): not observable by the next session; 30-50% of handoff time is spent re-diagnosing state

**Rationale:** Observability has two layers: runtime (what did the system do) and process (why should this change be accepted). Without the process layer, evaluators and future sessions cannot reproduce assessments. The sprint contract is the minimum process artifact that prevents scope drift before a line of code is written.

**Consequence:** `up5-docs/standards/sprint-contract.md` documents the template. The `dev-environment.md` now documents Odoo log levels and how to read test output (runtime observability layer).

---

## 2026-06-13 — E2E test requirement for cross-component changes (lecture 10)

**Decision:** Any change touching two or more Odoo layers (model + controller, controller + view, etc.) requires either an `HttpCase` test or a documented manual smoke test before the task is `passing`. Every test file must include at least one failure scenario. Review feedback promotion: a pattern violation caught more than once in review becomes a Hard Constraint or `odoo-conventions.md` rule — not just a comment.

**Alternatives considered:**
- TransactionCase only: misses interface mismatches, state propagation errors, and environment dependency failures — all five defect categories in the file-export case study were invisible to unit tests
- Manual-only E2E: inconsistent across sessions, unauditable

**Rationale:** Five defect categories are invisible to unit tests by design: interface mismatch, state propagation errors, resource lifecycle, environment dependency, error propagation. The 2-second → 15-second trade-off for E2E tests is acceptable in agent workflows. Agents copy existing patterns — without layer constraints established early, pattern drift compounds exponentially across sessions.

**Consequence:** `odoo-conventions.md` documents which test class covers which layer, and the ERROR/WHY/FIX error message structure. Module layer architecture (models → wizards → controllers → views) is documented and enforced at code review.

---

## 2026-06-13 — Three-layer verification and Completion Priority Constraint (lecture 09)

**Decision:** `./verify.sh` enforces Layers 1 and 2 automatically. Layer 3 (system confirmation) is a manual smoke test required before marking any `up5_*` task `passing`. No refactoring or optimisation is permitted until Layer 2 passes.

**Alternatives considered:**
- Trust agent self-assessment of completion: ICML 2017 study shows confidence significantly exceeds accuracy; self-evaluation bias increases with multi-file complexity
- Unit tests as completion gate: unit tests mock dependencies and mask integration failures — interface mismatches and DB state errors only surface at Layer 2/3

**Rationale:** Agents systematically overestimate completion quality (premature victory declaration). Externalising judgment to the harness removes self-assessment from the loop. Sequential layer enforcement (L1 → L2 → L3) catches failures at the cheapest layer first.

**Consequence:** verify.sh now labels output by layer. Layer 3 is a browser smoke test — the agent must note the result in `claude-progress.md` before setting a task to `passing`. Refactoring before Layer 2 is a Hard Constraint violation.

---

## 2026-06-13 — feature_list.json schema: state machine + behavior field (lecture 08)

**Decision:** `feature_list.json` uses `state` (not `status`) with four values: `not_started → active → blocked → passing`. Each entry requires a `behavior` field (single-sentence description of the system's observable behavior when done) alongside `criteria`, `verification`, and `evidence` (commit hash + verify output).

**Alternatives considered:**
- Keep `status: "done"` — readable but doesn't communicate irreversibility or machine-readability requirement
- Free-form task notes — flexible but agents cannot reliably determine actual state from prose

**Rationale:** Feature lists are harness primitives, not planning memos (lecture 08). A state machine with explicit `passing` as terminal state enforces that only verified output moves a task forward. The `behavior` field grounds criteria in observable system behavior, not implementation steps. Evidence = commit hash makes the claim auditable.

**Consequence:** All new tasks require `behavior` before being set `active`. Evidence must include a commit hash. `passing` state is irreversible.

---

## 2026-06-13 — WIP=1 task discipline

**Decision:** Only one task may be `active` in `feature_list.json` at a time. A task is not done until `./verify.sh` output is pasted as `evidence` and `state` is `passing`. The next task cannot be set `active` until VCR (verified tasks ÷ activated tasks) = 1.0.

**Alternatives considered:**
- Parallel feature work: faster apparent progress but produces code without passing end-to-end verification — the REST API study showed 20% pass rate vs. 100% with WIP=1
- Trusting "code looks correct" as done: subjective, unverifiable, and the primary cause of under-finished sessions

**Rationale:** Agents have finite context (C). Activating k tasks simultaneously gives each C/k reasoning capacity — below a threshold, none finish. WIP=1 concentrates full context on one task, producing fewer but completed features per session.

**Consequence:** Session Start must check for `active` tasks with empty `evidence` and resume them before touching anything else. A broad prompt that implies multiple simultaneous tasks must be scoped to one at a time.

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
