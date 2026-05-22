# ORM Model Pattern

**Purpose:** Define a persistent database-backed business object in Odoo using the built-in ORM. Every feature-level entity (invoice, order, partner, etc.) is expressed as a Python class that inherits from `models.Model`.

**Source:** `odoo/orm/models.py`, `addons/account/models/account_move.py`, `addons/account/models/account_tax.py`

---

## When to Use

- Creating any new business entity that needs a database table
- Extending or inheriting an existing model (`_inherit`)
- Adding mixin capabilities to multiple models (`_name` only, abstract base)

---

## Code Example

```python
# addons/account/models/account_move.py  (lines 72–82)
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _name = 'account.move'           # technical name → database table name
    _inherit = [                     # list of mixins / parent models to merge
        'portal.mixin',
        'mail.thread.main.attachment',
        'mail.activity.mixin',
        'sequence.mixin',
    ]
    _description = "Journal Entry"  # human-readable label
    _order = 'date desc, name desc, id desc'  # default sort for search()
    _check_company_auto = True       # auto-enforce company consistency on M2o fields

    _rec_names_search = ['name', 'partner_id.name', 'ref']  # fields searched in name_search

    # --- Fields ---
    name = fields.Char(compute='_compute_name', inverse='_inverse_name',
                       readonly=False, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', copy=False)
    partner_id = fields.Many2one('res.partner', string='Customer/Vendor')
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items')

    # --- SQL-level constraints (faster than @api.constrains) ---
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name, journal_id, company_id)',
         'Journal entry names must be unique per journal and company.'),
    ]
```

---

## Key Model Attributes

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `_name` | Technical name; maps to DB table (`account_move`) | `'account.move'` |
| `_inherit` | Prototype or mixin list | `['mail.thread']` |
| `_description` | UI label | `"Journal Entry"` |
| `_order` | Default ORDER BY clause | `'date desc, id desc'` |
| `_rec_name` | Field used in display_name | `'name'` (default) |
| `_rec_names_search` | Fields searched in name_search | `['name', 'ref']` |
| `_table` | Override auto-generated table name | rarely needed |
| `_check_company_auto` | Auto-validate company on relational fields | `True` |
| `_sql_constraints` | DB-level UNIQUE/CHECK constraints | see example above |

## Three Model Base Classes

```
models.Model          → persistent table (most common)
models.TransientModel → temporary table, auto-vacuumed (wizards)
models.AbstractModel  → no table, only for inheritance/mixins
```

---

## Common Pitfalls

- **`_name` vs `_inherit` confusion:** Use only `_inherit` (no `_name`) to extend an existing model in-place. Use both `_name` and `_inherit` to create a new model that copies fields from another.
- **`_sql_constraints` vs `@api.constrains`:** SQL constraints are enforced by PostgreSQL and are faster but cannot express Python logic. Use `@api.constrains` for complex cross-field validation.
- **`_order` syntax:** Uses SQL column names (underscored), not Python field names. Wrong: `'partnerName'`. Right: `'partner_id'`.
- **Mixin order matters:** Earlier mixins have higher priority when methods clash. Order mixins intentionally.

---

## Related Patterns

- [field-definition-pattern.md](./field-definition-pattern.md) — field types and attributes
- [api-decorator-pattern.md](./api-decorator-pattern.md) — `@api.depends`, `@api.constrains`
- [security-model-pattern.md](./security-model-pattern.md) — access control for models
