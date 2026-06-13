# Odoo Development Harness — UP5 TECH

## Project Identity

**Company:** UP5 TECH — "We Build Software That Drives Your Business"
**What:** `odoo-up5` is UP5 TECH's Odoo 19.0 platform for delivering custom ERP, CRM, and SaaS solutions to clients.
**Custom scope:** Modules prefixed `up5_` are UP5 TECH-specific. All others are upstream Odoo — never patch them.
- *(add `up5_*` modules here as they are created)*

---

## Session Start (mandatory — do not skip)

1. `conda activate odoo19`
2. Read `claude-progress.md` → restore state from **Current Verified State** and **Next Steps**
3. Read `feature_list.json` → identify `in-progress` or `blocked` tasks
4. Read `DECISIONS.md` → understand why conventions exist before changing them
5. `python odoo-bin --version` → confirm environment is live

If `claude-progress.md` is missing, treat state as unknown and say so before proceeding.

## Session End (mandatory — do not skip)

Before closing any session, even if the task is incomplete:

1. Run `./verify.sh <module>` on anything changed — paste output into `claude-progress.md`
2. Update `claude-progress.md`: Current Verified State, Next Steps, any new Blockers
3. Update `feature_list.json` status for any tasks touched
4. If a significant decision was made, add it to `DECISIONS.md` with rationale
5. Commit all tracked changes with an atomic, descriptive message

---

## Hard Constraints

Non-negotiable. Any violation must be fixed before proceeding.

1. Never modify `odoo/` or any non-`up5_` module — extend via `_inherit` only
2. Never use `sudo()` without a comment explaining why
3. Never hardcode database IDs — use `env.ref('module.xml_id')`
4. Never declare a task done without pasting `./verify.sh <module>` output
5. Never commit without `./verify.sh <module>` passing
6. Every new `_name` model requires an `ir.model.access.csv` entry
7. All XML IDs must be prefixed with the module name
8. `__manifest__.py` `data` list: `security/` before `views/`
9. `@api.depends(...)` is required on every compute method
10. `Many2one.ondelete` must be explicit — never rely on the `'set null'` default

---

## Definition of Done

- [ ] `./verify.sh <module>` exits clean — **paste the output**
- [ ] `claude-progress.md` updated with what was done and the evidence
- [ ] `feature_list.json` entry set to `"status": "done"` with evidence

**Verification gap rule:** "looks correct" is not done. No output = not done.
**Context runs low:** stop, write state to `claude-progress.md`, let next session verify.

---

## Verification

```bash
./verify.sh <module>                                # lint + tests — required before done
conda run -n odoo19 ruff check addons/<module>/     # lint only (faster, use during dev)
```

Full test command syntax → [dev-environment.md](up5-docs/setup/dev-environment.md)

---

## State Management (ACID)

- **Atomicity** — one logical change per commit; `git stash` incomplete work
- **Consistency** — `./verify.sh` passes before every commit
- **Isolation** — one branch per feature/fix; naming: `19.0-<desc>-<handle>`
- **Durability** — all decisions live in git-tracked files, never session memory

---

## Diagnostic Loop

Attribute failures to one layer in order — fix it, then re-run:

1. **Task spec** — ambiguous? re-read `feature_list.json` criteria first
2. **Context** — convention missing? add it to the relevant topic doc, then retry
3. **Environment** — does `python odoo-bin --version` succeed? deps installed?
4. **Verification** — did the test error at import? read the full traceback
5. **State** — is `claude-progress.md` stale? dirty DB state from a prior failure?

Do not blame the model. Failures are in one of these five layers.

---

## Topic Documents

| When you need... | Read... |
|---|---|
| Current progress, next steps, blockers | [claude-progress.md](claude-progress.md) |
| Why a convention or decision exists | [DECISIONS.md](DECISIONS.md) |
| Environment setup, running tests, dev server | [up5-docs/setup/dev-environment.md](up5-docs/setup/dev-environment.md) |
| Odoo model/field/view/security/test conventions | [up5-docs/standards/odoo-conventions.md](up5-docs/standards/odoo-conventions.md) |
| Git workflow, branch naming, commit tags, PR process | [up5-docs/standards/git-workflow.md](up5-docs/standards/git-workflow.md) |
| Module-level architecture notes | `addons/<module>/NOTES.md` (create when module is complex) |
| Template for documenting a complex module | [up5-docs/architecture/module-notes-template.md](up5-docs/architecture/module-notes-template.md) |
