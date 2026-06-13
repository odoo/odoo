# Lecture 06 — Why Initialization Needs Its Own Phase

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-06-why-initialization-needs-its-own-phase/

## Core insight

Initialization and implementation are two fundamentally different work types.
Mixing them creates a multi-objective problem that satisfies neither.

> "Projects using a dedicated initialization phase showed 31% higher feature completion rates in multi-session scenarios."

## Two distinct phases

| Phase | Optimises for | Done when |
|---|---|---|
| **Initialization** | Reliability and efficiency of subsequent work | All 4 readiness conditions are green |
| **Implementation** | Feature quantity and quality | Tasks complete with passing verification |

## Four readiness conditions

All must be ✅ before implementation begins:

| # | Condition | Verification |
|---|---|---|
| 1 | **Can Start** | `python odoo-bin --version` succeeds; server launches |
| 2 | **Can Test** | `./verify.sh <module>` exits 0 end-to-end |
| 3 | **Can See Progress** | `claude-progress.md` has Current State + Next Steps |
| 4 | **Can Pick Up Next Steps** | `feature_list.json` has ≥1 `todo` task with criteria |

## Five initialization deliverables

1. Runnable environment (deps locked, project starts)
2. Verifiable test framework (at least one test passes)
3. **Startup Readiness Checklist document** — the formal handoff artifact
4. Task breakdown with acceptance criteria
5. Git checkpoint marking end of initialization

## Key metric

**Time from session start to first productive action** — should be under 3 minutes with proper initialization. Session 2 rebuild: 20 min (no artifacts) → 3 min (with artifacts).

## Anti-patterns

- Assuming session 1 decisions are available in session 2 without writing them down
- Starting feature work before the test pipeline actually runs end-to-end
- Treating initialization as "just setup" — it is a deliverable phase with verifiable outputs

## How this maps to `odoo-up5`

| Deliverable | Implementation |
|---|---|
| Runnable environment | conda env `odoo19` + requirements installed ✅ |
| Verifiable test framework | `verify.sh` — pending PostgreSQL installation ⚠️ |
| Startup Readiness Checklist | `startup-readiness.md` at repo root ✅ |
| Task breakdown | `feature_list.json` — needs first dev task added ⚠️ |
| Git checkpoint | All harness commits on `19.0-add-harness-engineering-cla` ✅ |

**Current state:** Initialization phase is 3/5 complete.
Initialization finishes when PostgreSQL is installed and `./verify.sh account` exits 0.
