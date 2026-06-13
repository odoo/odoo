# Module NOTES.md Template

Create `addons/<module>/NOTES.md` when a module has non-obvious architecture,
cross-module dependencies, or business rules that aren't visible in the code.

**Proximity principle:** docs belong next to the code they describe — not in a
central wiki that decays and drifts.

---

## Template

```markdown
# <module_name>

## What this module does
One paragraph. What business problem it solves. What it does NOT do.

## Key design decisions
- Why <pattern/approach> was chosen over the alternative
- Any constraint imposed by the client/business that shaped the code

## Dependencies and integration points
- Depends on: `module_a`, `module_b`
- Extended by: `module_c` (adds field X)
- Calls: `res.partner` for [reason]

## Data model notes
- `my.model` — [what it represents, key invariants]
- `my.model.line` — [relationship to parent, constraints]

## Non-obvious behaviour
- [Anything that would surprise a developer reading the code]
- [Side effects of saving/posting/validating records]

## Known limitations
- [What the module deliberately does not handle]

## Last updated
YYYY-MM-DD — [who updated it and why]
```

---

## When to create a NOTES.md

Create one when any of the following are true:
- The module has a custom workflow (states, transitions, automated actions)
- It integrates with an external API or system
- It overrides core Odoo behaviour in a non-obvious way
- A new developer would need more than 10 minutes to understand its structure
- It has been a source of bugs that required explanation

Do NOT create one for simple modules that just add fields to existing models.
