# Odoo Development Harness

This file defines the operating rules for Claude Code working in this repository.
It is a fork of Odoo 19.0. The active branch is `19.0`.

---

## Startup Checklist (mandatory — do not skip)

Before doing any work, complete these steps in order:

1. **Read `claude-progress.md`** — restore session context. If it is missing, treat the state as unknown and say so before proceeding.
2. **Read `feature_list.json`** — identify which tasks are `in-progress` or `blocked`.
3. Confirm environment: `python odoo-bin --version`

Without step 1, cross-session context is lost and prior work may be duplicated or contradicted.

---

## Repository Layout

```
odoo-bin              # Main entry point (do not modify)
requirements.txt      # Python dependencies
addons/               # All standard and custom Odoo modules (work here)
odoo/                 # Core Odoo framework (DO NOT MODIFY)
setup/                # Installation scripts (do not modify)
doc/                  # Documentation (do not modify)
```

**Rule: Never edit files inside `odoo/` or `setup/`.** All development happens in `addons/`.

---

## Odoo Module Structure

Every module in `addons/` follows this layout:

```
addons/<module_name>/
├── __manifest__.py       # Module metadata (name, version, depends, data)
├── __init__.py           # Python package init
├── models/               # ORM model definitions
│   ├── __init__.py
│   └── *.py
├── views/                # XML view definitions
├── data/                 # Data files loaded on install
├── tests/                # Python test classes
│   ├── __init__.py
│   └── test_*.py
├── static/               # JS/CSS/img assets
└── security/             # Access control lists (ir.model.access.csv)
```

---

## Key Conventions

These are **implicit Odoo rules** not derivable from reading code alone. Violating them causes silent failures or runtime errors that only appear after installation.

**Models**
- Inherit from `models.Model`, `models.TransientModel`, or `models.AbstractModel`
- Use `_name` for new models, `_inherit` to extend existing ones
- `_inherit` without `_name` → modifies the existing model in place (adds fields/methods)
- `_inherit` with a new `_name` → creates a new model that copies the parent (rarely what you want)
- Compute methods: prefix with `_compute_`, mark fields with `compute='_compute_x'`
- Always declare `store=True` on compute fields that need to be searchable/filterable
- Onchange methods: prefix with `_onchange_`, decorate with `@api.onchange('field')`
- Constraint methods: prefix with `_check_`, decorate with `@api.constrains('field')`
- Default methods: prefix with `_default_`, reference with `default=_default_x`
- Use `_sql_constraints` for DB-level uniqueness — Python `@api.constrains` is not enough for race conditions
- `_rec_name` defaults to `name`; set it explicitly if your model's display name comes from another field

**Decorators (v19.0 — do not use deprecated v8/v10 API)**
- `@api.model` — method has no recordset, operates on the model class (e.g. `create`, `default_get`)
- `@api.depends('field1', 'field2')` — required on every compute method
- `@api.onchange('field')` — UI-only; does not persist unless the user saves
- `@api.constrains('field')` — runs on save; raise `ValidationError` to block

**Relational fields**
- `Many2one` `ondelete` must be explicit: `ondelete='restrict'` or `ondelete='cascade'` — default is `'set null'`
- `One2many` requires the inverse `Many2one` field name in `inverse_name`
- Never use `.ids` on a `Many2many` to set values — use `[(6, 0, ids)]` command syntax

**Views**
- Always declare `inherit_id` when extending an existing view — never duplicate base views
- Use `position="after"`, `position="before"`, or `position="replace"` in xpath
- Every view must reference its model with `model="module.model_name"`
- Use `groups` attribute on fields/buttons to restrict visibility by security group

**Security**
- Every new model needs an entry in `security/ir.model.access.csv`
- Format: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`
- Record-level rules go in `security/` as `ir.rule` XML records — field-level ACLs use `groups=` on the field

**`__manifest__.py` required fields**
```python
{
    'name': '...',
    'version': '19.0.1.0.0',   # always prefix with Odoo version
    'depends': ['base'],
    'data': [...],              # order matters: security/ before views/
    'license': 'LGPL-3',
}
```

**Data file load order in `data` list matters:**
1. `security/ir.model.access.csv`
2. `data/` XML files
3. `views/` XML files

**Tests**
- `TransactionCase` — each test method runs in a transaction that rolls back; use for unit tests
- `SavepointCase` — uses savepoints; faster for large test suites
- `HttpCase` — spins up a real HTTP server; use for UI/tour tests only (slow)
- Fixtures go in `setUpClass` with `@classmethod`; test data created there is shared across methods

---

## Running Tests

```bash
# Run tests for a single module (replace <db> and <module>)
python odoo-bin --test-enable -d <db> --stop-after-init -i <module>

# Run a specific test class or method
python odoo-bin --test-enable -d <db> --stop-after-init -i <module> \
  --test-tags <module>/<ClassName>.<method_name>

# Run with log level for debugging
python odoo-bin --test-enable -d <db> --stop-after-init -i <module> \
  --log-level=test
```

Tests live in `addons/<module>/tests/test_*.py` and inherit from `odoo.tests.common.TransactionCase` or `SavepointCase`.

---

## Running the Dev Server

```bash
python odoo-bin -d <db> --dev=all --addons-path=addons
```

`--dev=all` enables auto-reload of Python files and assets.

---

## Definition of Done

A task is complete **only** when all of the following are true:

- [ ] The change runs without Python import or syntax errors
- [ ] Tests for the affected module pass with `--test-enable` — **show the actual command and output**
- [ ] No regressions in directly dependent modules
- [ ] `claude-progress.md` is updated with session goals, what was completed, the exact test command run, and its result
- [ ] The corresponding entry in `feature_list.json` is updated to `"status": "done"` with evidence

**Verification gap rule:** Saying "this should work" or "the code looks correct" is not verification. Paste the actual test output. If the environment is not set up to run tests, say so explicitly — do not guess at correctness.

**When context runs low:** Do not skip verification to finish faster. Stop, write the current state to `claude-progress.md`, and let the next session run the tests.

---

## What NOT to Do

- Do not modify `odoo/` (core framework) — extend via `_inherit` in `addons/` instead
- Do not use `sudo()` without a documented reason — it bypasses access control
- Do not hardcode IDs (e.g. `res.partner` id `3`) — use `ref()` or `env.ref()`
- Do not create a new module when extending an existing one is sufficient
- Do not commit `.pyc` files or `__pycache__/` directories

---

## Common Pitfalls

- **Missing `ir.model.access.csv` entry** → `AccessError` at runtime, not at import
- **`_inherit` without `_name`** → extends the model in place (correct for adding fields)
- **`_inherit` with a new `_name`** → creates a new model that inherits fields (a copy)
- **Forgot `depends` in `__manifest__.py`** → silent failures when the module loads standalone
- **XML `id` conflicts** → prefix all XML IDs with your module name: `<module>.<id>`
- **`data` list out of order** → view references a security group that isn't loaded yet → `ValueError` on install
- **Missing `@api.depends`** → compute field never recalculates after its dependencies change
- **`store=False` on a filtered/grouped field** → the field works in form view but breaks in list/search

---

## Diagnostic Loop — When Something Fails

Do not swap approaches randomly. Attribute the failure to one of these five layers in order, fix it, then re-run:

1. **Task specification** — Is the requirement ambiguous? Re-read `feature_list.json` acceptance criteria before writing code.
2. **Context provision** — Is a convention missing from `CLAUDE.md`? Add it before retrying.
3. **Environment** — Does `python odoo-bin --version` succeed? Are all `depends` modules installed in the DB?
4. **Verification** — Did the test actually run, or did it error at import/setup? Read the full traceback.
5. **State** — Is `claude-progress.md` out of date? Is a prior failed attempt leaving dirty state in the DB?

**Rule: do not blame the model.** If a similar, well-scoped task succeeded before, the failure is in one of these five layers.
