# Lecture 05 — Why Long-Running Tasks Lose Continuity

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-05-why-long-running-tasks-lose-continuity/

## Core insight

Context windows are finite. Complex tasks deplete them faster than simple generation tasks.
When a new session starts, the agent loses decision rationale, progress records, and project state.

> "Treat the agent like an engineer whose short-term memory gets wiped every session."

## What gets lost without state artifacts

| Lost information | Impact |
|---|---|
| Intermediate reasoning | Agent re-derives decisions, may reach different conclusions |
| Progress tracking | Work duplicated or skipped |
| Decision history | Why option A over B — agent picks randomly next session |
| Verification results | Known failures re-introduced; passing tests assumed broken |

## Context anxiety

Anthropic research: agents approaching context limits exhibit **rushed-finish behaviour** — premature task completion, skipped verification steps. Mitigation: explicit session-end procedure that stops work and writes state before context exhausts.

## Four essential state artifacts

| Artifact | Purpose |
|---|---|
| **Progress file** (`claude-progress.md`) | Current state, completed work, **Next Steps**, blockers |
| **Decision log** (`DECISIONS.md`) | Design choices with rationale and constraints — the "why" |
| **Git commits** | Atomic checkpoints with explanatory messages |
| **Init routine** | Clock-in / clock-out procedures in harness documentation |

**Next Steps is the critical field.** Session resume begins from Next Steps, not from re-reading all history.

## Real-world impact

| Metric | Without artifacts | With artifacts |
|---|---|---|
| Rebuild time | baseline | −78% |
| Feature completion | 58% | 100% |
| Hidden defects | 43% | 8% |

## How this maps to `odoo-up5`

| Gap | Fix applied |
|---|---|
| No decision rationale stored | Created `DECISIONS.md` with 4 founding decisions |
| `claude-progress.md` had no Next Steps | Restructured with **Next Steps** and **Blockers** sections |
| No session-end procedure | Added **Session End** checklist to `CLAUDE.md` (5 steps) |
| Session Start didn't include DECISIONS.md | Added step 4: read `DECISIONS.md` before changing conventions |
| Topic Documents table missing progress files | Added `claude-progress.md` and `DECISIONS.md` as first two rows |

## Session start / end protocol (implemented)

**Start:** activate env → read progress → read feature list → read decisions → confirm environment

**End:** verify.sh → update progress (Current State + Next Steps + Blockers) → update feature list → log any new decisions → commit
