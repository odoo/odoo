# Field Definition Pattern

**Purpose:** Declare the data schema of an Odoo model using typed field descriptors. Fields are class-level attributes that the ORM maps to database columns (scalar) or virtual joins (relational/computed).

**Source:** `odoo/orm/fields.py`, `odoo/orm/fields_relational.py`, `odoo/orm/fields_numeric.py`, `odoo/orm/fields_temporal.py`, `addons/account/models/account_journal.py`, `addons/account/models/account_move.py`

---

## When to Use

- Defining any persistent or computed attribute on a model
- Adding relational links between models (Many2one, One2many, Many2many)
- Computed/related fields that derive from other fields without DB storage

---

## Scalar Field Types

```python
from odoo import fields

# Text
name      = fields.Char(string='Name', required=True, size=128, translate=True)
note      = fields.Text(string='Notes')
body      = fields.Html(string='Description', translate=True)

# Numeric
sequence  = fields.Integer(default=10)
amount    = fields.Float(digits=(16, 2))
price     = fields.Monetary(currency_field='currency_id')

# Date / Time
date      = fields.Date(default=fields.Date.today)
datetime  = fields.Datetime(default=fields.Datetime.now)

# Boolean / Binary
active    = fields.Boolean(default=True)
image     = fields.Binary(attachment=True)

# Enumeration
state     = fields.Selection([
    ('draft', 'Draft'),
    ('posted', 'Posted'),
    ('cancel', 'Cancelled'),
], string='Status', default='draft', copy=False, tracking=True)

# Structured
payload   = fields.Json()
```

---

## Relational Field Types

```python
# addons/account/models/account_move.py (lines 161–230, condensed)

# Many2one: FK to another model (N records → 1 parent)
company_id = fields.Many2one(
    comodel_name='res.company',
    string='Company',
    required=True,
    readonly=True,
    index=True,
    default=lambda self: self.env.company,
    ondelete='restrict',        # restrict | cascade | set null
    check_company=True,         # enforce same company
)

# One2many: inverse of a Many2one (1 parent → N children)
line_ids = fields.One2many(
    comodel_name='account.move.line',
    inverse_name='move_id',     # Many2one field on child pointing back
    string='Journal Items',
    copy=True,
)

# Many2many: N-to-N via an implicit join table
matched_payment_ids = fields.Many2many(
    comodel_name='account.payment',
    relation='account_payment_move_rel',   # explicit join table name (optional)
    column1='move_id',
    column2='payment_id',
    string='Matched Payments',
)
```

---

## Computed Fields

```python
# addons/account/models/account_journal.py (lines 96, 125, 174)

# Computed + stored (recalculated on dependency change, written to DB)
code = fields.Char(
    compute='_compute_code',
    inverse='_inverse_code',    # allows writing back via UI
    readonly=False,
    store=True,
    precompute=True,            # compute at record creation time
)

# Related shortcut (thin wrapper around compute + store=False)
country_code = fields.Char(
    related='company_id.account_fiscal_country_id.code',
    readonly=True,
)

# Context-dependent computed field (re-evaluated per language)
# addons/account/models/account_move.py (lines 975–986)
type_name = fields.Char(
    compute='_compute_type_name',
    string='Type Name',
)

@api.depends_context('lang')
@api.depends('move_type')
def _compute_type_name(self):
    type_name_mapping = {
        'entry':       _('Journal Entry'),
        'out_invoice': _('Invoice'),
        'in_invoice':  _('Vendor Bill'),
        # ... other move types
    }
    for move in self:
        move.type_name = type_name_mapping.get(move.move_type, '')
```

---

## Common Field Attributes

| Attribute | Type | Purpose |
|-----------|------|---------|
| `string` | str | UI label |
| `required` | bool | NOT NULL constraint |
| `readonly` | bool | Disallow UI edit |
| `default` | value / lambda | Default on create |
| `store` | bool | Write to DB (computed fields) |
| `compute` | str | Method name for computed value |
| `inverse` | str | Method to write back computed field |
| `related` | str | Dot-chain shortcut |
| `copy` | bool | Include in record duplication |
| `tracking` | bool | Log changes in chatter |
| `index` | bool / `'btree'` / `'btree_not_null'` | DB index |
| `translate` | bool | Multi-language support |
| `digits` | tuple | `(total, decimal)` precision for Float |
| `precompute` | bool | Compute before INSERT |
| `help` | str | Tooltip text |

---

## Common Pitfalls

- **`store=False` computed fields are not searchable** by default. Implement `_search_<field>` to enable domain-based searches.
- **`precompute=True` requires `store=True`** — otherwise it has no effect.
- **`One2many` fields are never stored** in the parent table; they are read by querying children.
- **`related` vs `compute`:** `related` is a thin wrapper, always readonly unless `readonly=False` is set explicitly. Use `compute` + `inverse` for writable derived fields.
- **`Many2many` without explicit `relation`** auto-generates a join table name. Collisions can occur with long model names — use explicit `relation` for cross-addon M2M.
- **`lambda self: self.env.company`** is the correct pattern for company default; avoid using a module-level function for defaults.

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — model class structure
- [api-decorator-pattern.md](./api-decorator-pattern.md) — `@api.depends` for computed fields
- [domain-filter-pattern.md](./domain-filter-pattern.md) — filtering on field values
