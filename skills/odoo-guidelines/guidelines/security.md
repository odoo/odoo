# Access rights

Master unifies the old `ir.model.access` ACLs and `ir.rule` record rules into
a single `ir.access` model, declared in `security/ir.access.csv` with columns
`id,name,model_id,group_id/id,operation,domain`.

- `operation` is required: a subset of `crud` letters (`r`, `cru`, `crud`, …);
  a row applies to exactly the operations it lists. The optional `domain`
  restricts the row to matching records (what record rules used to do).
- Rows **with** a group are *permissions*: OR-ed together (union over the
  user's groups); a row's domain limits only what that row grants. Rows
  **without** a group are *restrictions*: AND-ed onto **every** user — they
  never grant anything, and non-overlapping restrictions can lock everyone
  out.
- Default deny: a model with no permission row is inaccessible. Granting to
  everyone (portal/public included) is done via `base.group_everyone` — flag
  any `c`/`u`/`d` granted to `base.group_everyone`, `base.group_portal`, or
  `base.group_public`.
- Multi-company models need a group-less restriction row with a company
  domain — `"[('company_id', 'in', company_ids)]"` (`company_ids` evaluates to
  the user's allowed companies; append `+ [False]` when the company is
  optional).

For auditing beyond the data files (`sudo()`, SQL, public methods, …), use the
`odoo-security` skill.
