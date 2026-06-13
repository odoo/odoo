# Startup Readiness Checklist

Run this checklist to verify the project is ready for a fresh agent or developer session.
All four conditions must pass before implementation work begins.

Update the **Status** column as conditions are met.

---

## Condition 1 — Can Start

> Dependencies installed, environment configured, project launches without errors.

| Check | Command | Status |
|---|---|---|
| conda env exists | `conda env list \| grep odoo19` | ✅ |
| Python packages installed | `conda run -n odoo19 python odoo-bin --version` | ✅ |
| PostgreSQL reachable | `psql -U odoo -c "SELECT 1;"` | ✅ |
| `odoo_dev` database exists | `psql -U odoo -c "\l" \| grep odoo_dev` | ✅ |
| Odoo server starts | `conda run -n odoo19 python odoo-bin -c odoo.conf --stop-after-init` | ✅ |

---

## Condition 2 — Can Test

> Test framework configured; at least one test passes end-to-end.

| Check | Command | Status |
|---|---|---|
| `verify.sh` is executable | `ls -la verify.sh` | ✅ |
| ruff lint runs | `conda run -n odoo19 ruff check addons/account/ \| head -5` | ✅ |
| Odoo tests run | `./verify.sh account` | ✅ |
| At least one test passes | `./verify.sh account` exits 0 | ✅ |

---

## Condition 3 — Can See Progress

> Current state documented and visible from repo contents alone.

| Check | File | Status |
|---|---|---|
| Progress log exists | `claude-progress.md` | ✅ |
| Current state is described | `claude-progress.md` → Current Verified State | ✅ |
| Next steps are listed | `claude-progress.md` → Next Steps | ✅ |
| Blockers are noted | `claude-progress.md` → Blockers | ✅ |
| Key decisions recorded | `DECISIONS.md` | ✅ |

---

## Condition 4 — Can Pick Up Next Steps

> Task breakdown with clear acceptance criteria exists.

| Check | File | Status |
|---|---|---|
| Feature tracker exists | `feature_list.json` | ✅ |
| At least one `todo` task with criteria | `feature_list.json` | ⚠️ no dev tasks yet — add before starting work |
| Conventions documented | `up5-docs/standards/odoo-conventions.md` | ✅ |
| Git workflow documented | `up5-docs/standards/git-workflow.md` | ✅ |

**Resolution:** Before starting any development task, add an entry to `feature_list.json` with:
- `"state": "not_started"` (valid states: `not_started / active / blocked / passing`)
- `"criteria"` array with specific, verifiable acceptance conditions
- `"verification"` command

---

## Overall Readiness

| Condition | Ready? |
|---|---|
| Can Start | ✅ |
| Can Test | ✅ |
| Can See Progress | ✅ |
| Can Pick Up Next Steps | ⚠️ partial — no dev tasks in queue yet |

**Initialization is complete.** Add a `todo` task to `feature_list.json` to begin implementation.
