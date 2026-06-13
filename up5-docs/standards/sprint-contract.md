# Sprint Contract

A sprint contract is a pre-implementation agreement written in `claude-progress.md` before
any code is written for an `active` task. It converts a `feature_list.json` entry from a
description into a binding scope document.

**Required by:** CLAUDE.md Hard Constraint #13

---

## Why it exists

Without a sprint contract, agents begin coding before scope is clear. Ambiguous criteria
lead to over-building, under-building, or discovering a misunderstanding at Layer 2/3
verification — when the fix is expensive. A sprint contract surfaces ambiguities in minutes,
before they cost sessions.

---

## Template

Copy this block into `claude-progress.md` at the start of any `active` task:

```markdown
### Sprint Contract: <task-id> — <task-title>

**Behavior (from feature_list.json):**
<paste behavior field>

**In scope:**
- <criterion 1 from criteria array>
- <criterion 2>
- ...

**Out of scope (explicit):**
- <what this task does NOT include — list at least one item>

**Verification command:** `<exact command from verification field>`

**Ambiguities resolved:**
- <any unclear criterion and how it was resolved before coding started>
  (none if all criteria are unambiguous)
```

---

## Rules

1. **Write the contract before the first line of code** — not after
2. **Out-of-scope list must have at least one item** — if you can't think of one, the scope is probably too vague
3. **Ambiguities resolved must be filled** — "none" is only valid if every criterion is already specific and verifiable
4. **Do not modify in-scope list after coding starts** — scope changes require re-negotiation (update the task criteria and restart)

---

## Example

```markdown
### Sprint Contract: up5-crm-stage — Add pipeline stage model

**Behavior (from feature_list.json):**
The up5_crm module defines a Stage model with name and probability fields; stages
appear in a list view accessible from the CRM menu; ./verify.sh up5_crm exits 0.

**In scope:**
- `up5.crm.stage` model with `name` (Char, required) and `probability` (Float, 0–100)
- `ir.model.access.csv` entry for the model
- List view + menu item under CRM
- `TransactionCase` test for model creation and probability validation
- `./verify.sh up5_crm` exits 0

**Out of scope (explicit):**
- Kanban view (separate task)
- Many2one link from leads to stages (separate task)
- Any changes to `res.partner` or other existing models

**Verification command:** `./verify.sh up5_crm`

**Ambiguities resolved:**
- "probability" range: 0.0–100.0 (Float), not 0–1 — chosen for UI readability
```
