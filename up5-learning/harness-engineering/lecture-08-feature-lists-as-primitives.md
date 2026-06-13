# Lecture 08 — Why Feature Lists Are Harness Primitives

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-08-why-feature-lists-are-harness-primitives/

## Core insight

Feature lists are not planning memos — they are foundational execution structures.
Agents lack inherent understanding of "done." Structured feature lists with machine-readable
state eliminate this ambiguity and serve as the single source of truth for all harness components.

> "Projects using structured feature lists show 45% higher completion rates with zero duplicate implementations."
> "Good progress records reduce diagnostic startup time by 60-80% for follow-up sessions."

## Triple structure — all three required

| Element | Purpose | Missing = |
|---|---|---|
| `behavior` | What the system does when this task is passing | Agent can't tell if it's building the right thing |
| `verification` | Executable command that proves done | Agent substitutes subjective assessment |
| `state` | Where the task stands right now | Agent can't resume from cold start |

## State machine

```
not_started → active → passing
                ↕
             blocked
```

- Only `./verify.sh` output permits the transition to `passing`
- `passing` is irreversible — do not regress a passing task
- Only one task may be `active` at a time (WIP=1, lecture 07)

## Required schema

```json
{
  "id": "unique-kebab-id",
  "behavior": "Single sentence: observable system behavior when this task is passing",
  "state": "not_started | active | blocked | passing",
  "verification": "exact executable command",
  "evidence": "commit <hash> — YYYY-MM-DD; <verify output summary>"
}
```

## Granularity rule

Each task must be **completable in one session**. If it isn't, split it before marking `active`.
- Too broad: "Implement the invoicing module" — split into model, views, tests, security
- Too granular: "Add one field" — group related fields into one task
- Right size: "Create `up5_foo` module skeleton with model, access CSV, and passing verify.sh"

## Anti-patterns

| Anti-pattern | Effect |
|---|---|
| "Mostly done" / "Still need payments" | New session can't determine actual state |
| Implicit verification ("no syntax errors") | Doesn't prove end-to-end functionality |
| Scope scattered across conversations and TODO comments | Contradictions, duplicate work |
| Overly broad tasks ("implement shopping cart") | Won't finish in one session |

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| Single source of truth | `feature_list.json` — git-tracked, machine-readable |
| `behavior` field | Required on every new task before setting `active` |
| `state` machine | `not_started → active → blocked → passing` — enforced by WIP=1 rule |
| `evidence` | Must include commit hash — makes the claim auditable |
| Granularity | One `up5_*` module feature per task, sized to complete in one session |
| Primitives vs. documents | `feature_list.json` is a primitive: CLAUDE.md Hard Constraint #1 enforces it |
