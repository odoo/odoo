# Lecture 11 — Why Observability Belongs Inside the Harness

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-11-why-observability-belongs-inside-the-harness/

## Core insight

Agents executing tasks without visibility into runtime state make decisions under uncertainty.
The harness must expose both system behavior (runtime observability) and evaluation signals
(process observability) to guide effective decision-making.

> "Observability is an architecture property, not an afterthought."

## Two layers of observability

| Layer | Answers | Examples |
|---|---|---|
| **Runtime observability** | "What did the system do?" | Logs, traces, process events, health checks |
| **Process observability** | "Why should this change be accepted?" | Sprint contracts, rubrics, criteria, decision records |

Both must reinforce each other. Runtime signals explain behavior; process artifacts explain intent.

## Problems without observability

| Problem | Cost |
|---|---|
| Indistinguishable outcomes | Code appears correct but fails at runtime under specific conditions |
| Mystical evaluation | Assessments not reproducible; different evaluators reach different conclusions |
| Blind retries | Agent retries randomly without root-cause visibility |
| Handoff inefficiency | Missing observability forces redundant diagnosis — **30-50% of session time** |

## Key mechanisms

### Sprint contract (pre-implementation agreement)
Written before the first line of code. Specifies:
- Scope (what is in)
- Exclusions (what is explicitly out)
- Verification standards (exact command)
- Resolved ambiguities (criteria made specific before coding)

Without it, agents discover scope misalignment at Layer 2/3 — the most expensive point.

### Evaluator rubric
Structured scoring with dimensional thresholds. Converts subjective "looks good" into:
- Specific measured outcomes ("contrast ratio 4.5:1 required")
- Pass/fail thresholds per dimension
- Reproducible by any evaluator

### Task trace
Complete decision path from task start to `passing`. Enables:
- Process replay when failures occur
- Root-cause diagnosis without re-reading all code
- Next session picks up exactly where this one left off

## Planner → Generator → Evaluator workflow

When quality matters more than speed:
- **Planner** defines scope and constraints (not granular implementation)
- **Generator** implements per sprint contract
- **Evaluator** scores against rubric using actual execution, not self-assessment

Same model, three roles. Anthropic data: multi-agent = full correctness vs. single-agent = failure on identical tasks.

## Anti-patterns

| Anti-pattern | Effect |
|---|---|
| Agents self-instrument their work | Agents don't log what they don't realize matters |
| Process observability without runtime | Explains intent but not behavior — misalignment invisible |
| Runtime without process | Explains behavior but not why — diagnosis is guesswork |
| Vague evaluation ("looks good") | Not reproducible; different sessions reach different conclusions |

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| Sprint contract | CLAUDE.md Hard Constraint #13; template at `up5-docs/standards/sprint-contract.md` |
| Runtime observability | `dev-environment.md` — log levels, test output signals, browser debug mode |
| Process observability | `claude-progress.md` with WHY rationale; `DECISIONS.md`; sprint contract block |
| Task trace | Session End step 2 — include WHY for non-obvious decisions |
| Evaluator rubric | `verify.sh` Layers 1+2 as automated rubric; Layer 3 manual with noted result |
| Blind retry prevention | `claude-progress.md` Current Verified State + Blockers section |
