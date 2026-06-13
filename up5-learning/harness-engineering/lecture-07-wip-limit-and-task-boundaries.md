# Lecture 07 — Why Agents Overreach and Under-Finish

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-07-why-agents-overreach-and-under-finish/

## Core insight

Agents have finite context capacity C. Activating k tasks simultaneously gives each task C/k
reasoning resources. Below a critical threshold, none complete successfully.

> "Agents using a 'small next step' strategy showed 37% higher task completion rate vs. broad prompts."
> "Code lines generated correlate *negatively* with feature completion — more code written, fewer finished features."

## Key concepts

| Term | Definition |
|---|---|
| **Overreach** | Activating more tasks than can complete — measurable as features with zero passing end-to-end tests |
| **Under-finish** | Verified tasks ÷ activated tasks < 1.0 (code exists but tests fail) |
| **WIP=1** | Only one task in-flight at a time — the safe default for agents |
| **VCR** | Verified Completion Rate = verified tasks ÷ activated tasks. Block new activation when VCR < 1.0 |
| **Completion evidence** | Executable verification command proving a task is done — not subjective assessment |

## The REST API experiment

| Mode | Features started | Total code | End-to-end pass rate | Features completed (3 sessions) |
|---|---|---|---|---|
| Unconstrained | 5 simultaneous | ~800 lines / 12 files | 20% | 3 of 8 |
| WIP=1 | 1 at a time | ~200 lines / feature | 100% | 7 of 8 |

WIP=1 produced *less code* but *more completed features*.

## Anti-patterns

- Broad prompts without scope boundaries → scope creep
- "Code looks correct" as completion criteria → unverifiable
- Parallel feature development without completion gates → overreach
- Skipping verification and relying on manual review → under-finish

## Rules

1. **WIP=1** — finish before starting next
2. **Completion evidence must be executable** — not subjective
3. **Scope surface is externalised** — machine-readable file (feature_list.json)
4. **VCR < 1.0 blocks new task activation** — resume in-progress first

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| WIP=1 | Hard Constraint #1 in `CLAUDE.md` — enforced at session start |
| Completion evidence | `evidence` field in `feature_list.json` — must contain `./verify.sh` output |
| Scope surface | `feature_list.json` — machine-readable, git-tracked |
| VCR check | Session Start step 3 — resume `in-progress` task before touching anything else |
| Completion gate | Status transitions: `todo` → `in-progress` → (evidence pasted) → `done` |
