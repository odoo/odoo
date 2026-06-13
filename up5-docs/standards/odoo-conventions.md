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

### Layer mapping

| Class | Verification layer | Use when |
|---|---|---|
| `TransactionCase` | Layer 2 — Runtime | Model logic, compute fields, constraints — most tests |
| `SavepointCase` | Layer 2 — Runtime | Large suites — uses DB savepoints for speed |
| `HttpCase` | Layer 2/3 boundary | HTTP endpoints, JSON-RPC controllers, URL routing |
| JS `tour` via `HttpCase` | Layer 3 — System | UI features — button clicks, form flows, end-to-end |

For any change that crosses two layers (e.g. model + controller, or controller + view), a
`HttpCase` test or documented manual smoke test is required before marking the task `passing`.

### Always include a failure scenario

Every feature test file must include at least one test of expected failure, not only happy paths:

```python
def test_create_ok(self):
    record = self.env['up5.foo'].create({'name': 'Test'})
    self.assertTrue(record.id)

def test_create_rejects_empty_name(self):
    with self.assertRaises(ValidationError):
        self.env['up5.foo'].create({'name': False})
```

Unit tests that test only happy paths miss the failure propagation errors that E2E surfaces.

### Test structure

```python
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError

class TestMyModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

    def test_something(self):
        result = self.env['my.model'].method()
        self.assertEqual(result, expected_value)
```

- Fixtures go in `setUpClass` with `@classmethod` — shared across all test methods
- Test files must be in `tests/test_*.py` and imported in `tests/__init__.py`
- Assert on observable behavior, not implementation details

### Error message structure

When writing validation errors or exceptions in `up5_*` modules, use the ERROR/WHY/FIX pattern:

```python
raise ValidationError(
    "ERROR: 'start_date' cannot be after 'end_date' on %s.\n"
    "WHY: date range is used for availability filtering — inverted range returns zero results.\n"
    "FIX: set start_date ≤ end_date before saving." % self.name
)
```

This gives the agent (and developer) a self-correction path without needing to read source code.

---

## Module Layer Architecture

Dependencies in an `up5_*` module flow strictly forward. Never import backwards.

```
models/        ← data + business logic (no HTTP, no views)
    ↓
wizards/       ← transient operations (depends on models only)
    ↓
controllers/   ← HTTP endpoints (depends on models + wizards)
    ↓
views/ (XML)   ← presentation (references models by field name only)
```

A model must never import a controller. A view must never contain business logic.
Violations here cause circular imports or untestable code — enforce at code review.

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
