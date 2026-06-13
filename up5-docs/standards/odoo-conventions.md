# Odoo Conventions — UP5 TECH

Full reference for writing Odoo 19.0 code in this project.
For hard constraints (what is non-negotiable), see [CLAUDE.md](../../CLAUDE.md).

---

## Module Structure

```
addons/<module_name>/
├── __manifest__.py       # metadata: name, version, depends, data, license
├── __init__.py
├── models/
│   ├── __init__.py
│   └── *.py
├── views/                # XML view definitions
├── data/                 # data files loaded on install
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── static/               # JS/CSS/img assets
├── security/
│   └── ir.model.access.csv
└── NOTES.md              # create when module has non-obvious architecture
```

**`__manifest__.py` required fields:**
```python
{
    'name': '...',
    'version': '19.0.1.0.0',   # always prefix with Odoo version
    'depends': ['base'],
    'data': [                   # order matters
        'security/ir.model.access.csv',
        'data/my_data.xml',
        'views/my_views.xml',
    ],
    'license': 'LGPL-3',
}
```

---

## Models

```python
class MyModel(models.Model):
    _name = 'my.model'           # new model
    _description = 'My Model'   # required
    _rec_name = 'name'           # set explicitly if display name is not 'name'

    # _inherit without _name → extends in place (adds fields/methods)
    # _inherit with new _name  → copies the model (rarely what you want)
```

**Method prefixes:**

| Prefix | Decorator | Purpose |
|---|---|---|
| `_compute_` | `@api.depends('f1','f2')` | Computed field — decorator required |
| `_onchange_` | `@api.onchange('field')` | UI-only, does not persist until save |
| `_check_` | `@api.constrains('field')` | Raise `ValidationError` to block save |
| `_default_` | — | Referenced as `default=_default_x` |

**Compute fields:**
- `@api.depends(...)` is required — without it the field never recalculates
- Add `store=True` when the field needs to be searchable or filterable
- Use `_sql_constraints` for DB-level uniqueness; `@api.constrains` alone is not safe under concurrent writes

**`@api.model`** — no recordset; operates on the model class (e.g. `create`, `default_get`)

---

## Relational Fields

```python
# Many2one — ondelete MUST be explicit
partner_id = fields.Many2one('res.partner', ondelete='restrict')  # or 'cascade'
# default is 'set null' — never rely on it silently

# One2many — inverse_name must point to the Many2one on the child
line_ids = fields.One2many('my.model.line', 'model_id')

# Many2many write commands
record.tag_ids = [(6, 0, [id1, id2])]   # replace all
record.tag_ids = [(4, id)]              # add one
record.tag_ids = [(3, id)]              # remove one
record.tag_ids = [(0, 0, {'name': 'x'})]  # create and link
# Never assign .ids directly to a Many2many
```

---

## Views

- Always use `inherit_id` when extending — never duplicate base views
- Use `position="after"`, `"before"`, or `"replace"` in xpath
- Every view must declare `model="module.model_name"`
- Use `groups` attribute on fields/buttons to restrict by security group

---

## Security

**`ir.model.access.csv` format:**
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model user,model_my_model,base.group_user,1,1,1,0
```
- Every new `_name` model needs a row here — missing entries cause `AccessError` at runtime
- Record-level rules → `ir.rule` XML records in `security/`
- Field-level visibility → `groups=` attribute on the field definition

---

## Tests

| Class | Use case |
|---|---|
| `TransactionCase` | Unit tests — each method rolls back; standard choice |
| `SavepointCase` | Faster for large suites — uses savepoints |
| `HttpCase` | UI/tour tests only — slow, spins up real HTTP server |

- Fixtures go in `setUpClass` with `@classmethod` — shared across all test methods
- Test files must be in `tests/test_*.py` and imported in `tests/__init__.py`

---

## Common Pitfalls

| Symptom | Cause |
|---|---|
| `AccessError` at runtime, not import | Missing `ir.model.access.csv` entry |
| Compute field never updates | Missing `@api.depends(...)` |
| Field works in form, breaks in list/search | `store=False` on a filtered/grouped field |
| `ValueError` on module install | `data` list out of order (views before security) |
| Silent failure loading standalone | Missing entry in `depends` in `__manifest__.py` |
| XML ID conflict | Not prefixed with module name — use `<module>.<id>` |
| Race condition on unique constraint | Using only `@api.constrains` — add `_sql_constraints` |
