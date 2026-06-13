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
3. Read `feature_list.json` → if any task is `active` with empty `evidence`, resume it — **do not start a new task** (WIP=1)
4. Read `DECISIONS.md` → understand why conventions exist before changing them
5. `python odoo-bin --version` → confirm environment is live

If `claude-progress.md` is missing, treat state as unknown and say so before proceeding.

## Session End (mandatory — do not skip)

Before closing any session, even if the task is incomplete, run the
[clean-state checklist](up5-docs/standards/clean-state-checklist.md) — all 5 dimensions must be ✅:

1. Run `./verify.sh <module>` on anything changed — paste output into `claude-progress.md`
2. Update `claude-progress.md`: Current Verified State, Next Steps, any new Blockers — include WHY for non-obvious decisions (these form the task trace for the next session)
3. Update `feature_list.json` `state` for any tasks touched
4. If a significant decision was made, add it to `DECISIONS.md` with rationale
5. If a pattern violation appeared more than once during the session, convert it to a Hard Constraint or add it to `odoo-conventions.md` — recurring review comments become permanent rules
6. Confirm Dimension 4: no debug prints, commented-out code, or untracked TODO markers remain
7. Commit all tracked changes with an atomic, descriptive message

---

## Hard Constraints

Non-negotiable. Any violation must be fixed before proceeding.

1. WIP=1 — only one task may be `active` in `feature_list.json` at a time; do not set the next task `active` until the current has `evidence` and `state: "passing"`
2. Never modify `odoo/` or any non-`up5_` module — extend via `_inherit` only
3. Never use `sudo()` without a comment explaining why
4. Never hardcode database IDs — use `env.ref('module.xml_id')`
5. Never declare a task done without pasting `./verify.sh <module>` output — agent confidence is not evidence
6. Never commit without `./verify.sh <module>` passing
7. Never refactor or optimise before Layer 2 (`./verify.sh`) passes — functionality first, then style
8. Every new `_name` model requires an `ir.model.access.csv` entry
9. All XML IDs must be prefixed with the module name
10. `__manifest__.py` `data` list: `security/` before `views/`
11. `@api.depends(...)` is required on every compute method
12. `Many2one.ondelete` must be explicit — never rely on the `'set null'` default
13. Before writing any code on an `active` task, write a sprint contract in `claude-progress.md` — `behavior`, `criteria`, and explicit out-of-scope statement; resolve ambiguities first
14. Never commit debug `print()`, commented-out code, or untracked `TODO`/`FIXME` markers — clean state is a completion criterion, not optional housekeeping

---

## Definition of Done

**Three layers — all required. "Code is written" is not done. Agent confidence is not evidence.**

| Layer | What | How |
|---|---|---|
| 1 — Static | ruff lint passes | `./verify.sh <module>` (auto) |
| 2 — Runtime | Odoo test runner exits 0 | `./verify.sh <module>` (auto) |
| 3 — System | module installs, critical path runs | manual smoke test at http://localhost:8069 |

- [ ] `./verify.sh <module>` exits 0 — **paste the full output** (Layers 1 + 2)
- [ ] Layer 3 smoke test confirmed — note result in `claude-progress.md`
- [ ] `claude-progress.md` updated with what was done and the evidence
- [ ] `feature_list.json` entry set to `"state": "passing"` with evidence (commit hash + verify output)

**No refactoring until Layer 2 passes.** Functionality first, then style.
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

## Initialization vs Implementation

These are two distinct phases. Never mix them.

**Initialization** — runs once per environment setup. Done when `startup-readiness.md` shows all four ✅:
1. Can Start — `conda activate odoo19 && python odoo-bin --version`
2. Can Test — `./verify.sh <module>` exits 0
3. Can See Progress — `claude-progress.md` has Current State + Next Steps
4. Can Pick Up Next Steps — `feature_list.json` has at least one `todo` task with criteria

Check current readiness: [startup-readiness.md](startup-readiness.md)

**Implementation** — only begins after all four conditions are green. One task from `feature_list.json` at a time. Each task must be scoped to complete in a single session — if it can't, split it before marking `active`.

**Sprint contract (required before writing any code):** Read the task's `behavior` + `criteria` + `verification`. If anything is ambiguous, resolve it. Write an explicit out-of-scope statement in `claude-progress.md`. Then code. See [sprint-contract.md](up5-docs/standards/sprint-contract.md) for the template.

---

## Topic Documents

| When you need... | Read... |
|---|---|
| Environment readiness status | [startup-readiness.md](startup-readiness.md) |
| Current progress, next steps, blockers | [claude-progress.md](claude-progress.md) |
| Why a convention or decision exists | [DECISIONS.md](DECISIONS.md) |
| Environment setup, running tests, dev server | [up5-docs/setup/dev-environment.md](up5-docs/setup/dev-environment.md) |
| Odoo model/field/view/security/test conventions | [up5-docs/standards/odoo-conventions.md](up5-docs/standards/odoo-conventions.md) |
| Git workflow, branch naming, commit tags, PR process | [up5-docs/standards/git-workflow.md](up5-docs/standards/git-workflow.md) |
| Module-level architecture notes | `addons/<module>/NOTES.md` (create when module is complex) |
| Template for documenting a complex module | [up5-docs/architecture/module-notes-template.md](up5-docs/architecture/module-notes-template.md) |
| Sprint contract template | [up5-docs/standards/sprint-contract.md](up5-docs/standards/sprint-contract.md) |
| End-of-session exit checklist | [up5-docs/standards/clean-state-checklist.md](up5-docs/standards/clean-state-checklist.md) |
| Module health scores | [up5-docs/standards/quality-document.md](up5-docs/standards/quality-document.md) |
