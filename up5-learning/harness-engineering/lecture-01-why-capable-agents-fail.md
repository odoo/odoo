# Lecture 01 — Why Capable Agents Still Fail

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-01-why-capable-agents-still-fail/

## Core insight

**Model capability ≠ execution reliability.**

The same model (Claude Opus 4.5) on the same task:
- Bare prompt → 20 min, $9, features failed
- With full harness → 6 hours, $200, fully functional

The model didn't change. The infrastructure did.

> "When things fail, don't swap the model first — check the harness."

## Five failure modes

| # | Mode | What it looks like in practice |
|---|---|---|
| 1 | **Vague requirements** | "Add search" — full-text or structured? paginated? highlighted? |
| 2 | **Implicit conventions** | Odoo's `ondelete` default, data load order, decorator rules — the agent hasn't seen the rule |
| 3 | **Incomplete environment** | Agent spends context fixing missing deps instead of doing the task |
| 4 | **Missing verification** | Agent declares done because the code "looks right" — no test run |
| 5 | **Cross-session state loss** | Each new session re-explores structure; tasks > 30 min fail sharply |

## Key terms

- **Harness** — everything external to model weights: instructions, tools, environment, state, verification
- **Verification gap** — difference between agent confidence and actual correctness
- **Diagnostic loop** — execute → observe failure → attribute to one layer → fix → re-execute

## Five defence layers (use when debugging failures)

1. Task specification clarity
2. Context provision sufficiency
3. Execution environment configuration
4. Verification feedback mechanisms
5. State management across sessions

## How this maps to `odoo-up5`

| Failure mode | Our mitigation |
|---|---|
| Vague requirements | `feature_list.json` has explicit `criteria` per task |
| Implicit conventions | `CLAUDE.md` documents Odoo-specific rules agents can't infer |
| Incomplete environment | Startup checklist + conda env with all deps pre-installed |
| Missing verification | Definition of Done requires pasted test output, not "looks right" |
| Cross-session state loss | `claude-progress.md` read at every session start |
