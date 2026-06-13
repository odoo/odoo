# Lecture 10 — Why End-to-End Testing Changes Results

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-10-why-end-to-end-testing-changes-results/

## Core insight

Unit tests create systematic blind spots by design — their isolation methodology prevents
detection of component boundary defects. Only E2E testing reveals interaction failures between
components that individually pass all tests.

Critically: **knowing their work faces E2E validation causes agents to fundamentally shift their
coding behavior toward architectural awareness.** The test requirement changes how agents write
code, not just how failures are caught.

## Five defect categories invisible to unit tests

| Category | Example |
|---|---|
| Interface mismatch | Component A and B each pass unit tests; fail when integrated due to inconsistent parameter formats |
| State propagation errors | Schema change not propagated through caching layers |
| Resource lifecycle issues | File handles / connections held across components |
| Environment dependency | Mocked behavior passes; real environment fails |
| Error propagation | Exceptions lost between layers |

**Case study:** File export feature — 5 defects, all missed by unit tests, all caught by E2E. Cost: 2s → 15s per test run. Worth it.

## Testing adequacy gradient

```
unit tests ⊂ integration tests ⊂ end-to-end tests
```

Each layer is a strict superset of defect detection. Skipping a level = skipping defect categories.

## Required mechanisms

### 1. Explicit validation hierarchy (no skipping)
```
Level 1: Static analysis (ruff)           — must pass
Level 2: Runtime tests (Odoo test runner) — must pass
Level 3: E2E / smoke test                 — must pass for cross-component changes
Skipping a level = incomplete.
```

### 2. Executable architectural rules
Convert constraints from documentation into automated checks:
- Lint rules for layered dependency violations
- Tests confirming boundary separation
- The harness enforces what the docs merely recommend

### 3. ERROR/WHY/FIX error message structure
```
ERROR: [specific violation — location and code]
WHY:   [architectural principle or safety reason]
FIX:   [concrete steps with file paths and API names]
```
Failure messages are self-correction mechanisms for agents, not observations for humans.

### 4. Review feedback promotion
Recurring code review comment → automated rule → never needs to be said again.

## Agent behaviour implication

Agents copy existing patterns from the codebase. Without early architectural constraints:
- Pattern drift compounds with each session
- Later enforcement becomes exponentially harder
- Day-one boundaries are worth far more than day-ten fixes

## Anti-patterns

| Anti-pattern | Effect |
|---|---|
| "Unit tests pass = done" | Misses all 5 boundary defect categories |
| Skip integration, run only fast tests | Systematic blind spot by design |
| Architectural rules in docs only | Agents ignore docs; rules need mechanical enforcement |
| Generic error messages ("violation detected") | Agent cannot self-correct |
| E2E optional for cross-component changes | Exactly where boundary defects live |

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| Layer mapping | `odoo-conventions.md` — TransactionCase (L2), HttpCase (L2/3), JS tour (L3) |
| Cross-component requirement | `HttpCase` or manual smoke test required for model+controller or controller+view changes |
| Failure scenario rule | Every test file must include ≥1 failure case |
| ERROR/WHY/FIX | Documented in `odoo-conventions.md`; used in `up5_*` `ValidationError` messages |
| Module layer architecture | `odoo-conventions.md` — models → wizards → controllers → views; no backwards imports |
| Review feedback promotion | Session End step 5 in `CLAUDE.md` — recurring violations become Hard Constraints |
| Executable constraints | Hard Constraints 8–12 in `CLAUDE.md` are the enforced layer rules for Odoo |
