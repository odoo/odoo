# Lecture 09 — Why Agents Declare Victory Too Early

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-09-why-agents-declare-victory-too-early/

## Core insight

Agents systematically overestimate their own completion quality (ICML 2017: confidence significantly
exceeds actual accuracy). Writing code that passes unit tests does not constitute task completion.
The harness must enforce externalized, execution-based verification — not agent self-assessment.

> "Replace agent confidence with externalized verification. Completion is not a feeling."

## The confidence calibration bias

The gap between what agents believe they've accomplished and actual completion quality
**increases with multi-file complexity**. A single-file change is low-risk. A feature touching
models + views + security + tests has four surfaces where the agent can silently be wrong.

## Real-world example (password reset)

Appeared complete: schema modified, endpoint written, template added, unit tests passing.
Actual failures: end-to-end flow never executed, DB migration partially failed (inconsistent
schema), email service config missing. All three failures would have been caught by the three-layer gate.

## Three-layer termination validation

| Layer | What it checks | Cost | Information |
|---|---|---|---|
| 1 — Static | Syntax, imports, style (ruff) | Lowest | Lowest — necessary but insufficient |
| 2 — Runtime | Test execution, app startup, critical paths | Medium | Core completion evidence |
| 3 — System | End-to-end, integration, user scenario | Highest | Final defence against false completion |

**Sequential enforcement:** Layer N only proceeds if Layer N-1 passes.
**No shortcuts:** skipping to Layer 3 without Layer 2 is not faster — it's unreliable.

## Completion Priority Constraint

1. **Functionality** — get Layer 2 to pass first
2. **Correctness** — Layer 3 smoke test confirms system behavior
3. **Style** — refactor only after both layers pass

Refactoring before Layer 2 shifts the verified/unverified code boundary and can break previously correct paths.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Unit tests ≠ completion | Mocks mask integration failures; state propagation errors invisible |
| Refactor before verify | Shifts verified/unverified boundary; breaks correct paths |
| Self-evaluation | Agents rate their own work overly positive even when objectively wrong |
| "Looks correct" | Not measurable; cannot be reproduced or audited |

## Actionable error feedback

Error messages should include repair instructions, not just failure notifications.

Not: "Test failed."
But: "Test failed: check `_compute_` method dependencies; ensure `@api.depends` lists all fields read inside the method."

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| Layer 1 | `ruff check` in `./verify.sh` (auto) |
| Layer 2 | Odoo test runner in `./verify.sh` (auto) |
| Layer 3 | Manual browser smoke test at http://localhost:8069 — result noted in `claude-progress.md` |
| Completion Priority | Hard Constraint #7 — no refactor before Layer 2 passes |
| Self-assessment banned | Hard Constraint #5 — agent confidence is not evidence; pasted output is |
| Actionable errors | `verify.sh` now prints fix instructions alongside each failure |
| Sequential enforcement | `verify.sh` exits on Layer 1 failure; never runs Layer 2 with lint errors |
