# Module Quality Document

Active health scores for all `up5_*` modules.
Update when a module reaches `state: passing` or when a regression is detected.

---

## Scoring dimensions

| Code | Dimension | What it checks |
|---|---|---|
| **V** | Verification | `./verify.sh <module>` exits 0 |
| **U** | Understandability | Models self-documenting; `NOTES.md` exists if architecture is non-obvious |
| **T** | Test stability | Tests pass reliably across sessions; failure scenarios included |
| **A** | Architectural compliance | No backwards imports; no hardcoded IDs; `ondelete` explicit |
| **C** | Code conventions | `ruff` clean; `@api.depends` on all compute methods; XML IDs prefixed |

## Grade scale

| Grade | Meaning |
|---|---|
| **A** | All checks in this dimension pass |
| **B** | Minor issues — not blocking, will fix next session |
| **C** | Significant issues — tracked in `feature_list.json` |
| **D** | Hard Constraint violation — must fix before next commit |
| **F** | Critical failure — `./verify.sh` broken or security gap |

Any module at **D or F** blocks new feature work until resolved.

---

## Module scores

| Module | V | U | T | A | C | Overall | Last checked |
|---|---|---|---|---|---|---|---|
| *(no `up5_*` modules yet)* | — | — | — | — | — | — | — |

---

## How to update

1. Run `./verify.sh <module>` → sets **V**
2. Read `models/` → score **U** and **A**
3. Read `tests/` → score **T** (does every test file have a failure scenario?)
4. Run `conda run -n odoo19 ruff check addons/<module>/` → sets **C**
5. Record overall grade and date
6. Any dimension at C or below → add a `not_started` task in `feature_list.json`
