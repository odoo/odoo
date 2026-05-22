# Domain / Filter Pattern

**Purpose:** Express record-set filters using Odoo's domain language — a structured list syntax that the ORM translates to SQL WHERE clauses. Domains appear in `search()` calls, field `domain=` attributes, record rules, search views, and the `Domain` class API.

**Source:** `odoo/orm/domains.py` (lines 3–275), `addons/account/models/account_move.py` (lines 21, 167, 2503–2505, 4567–4639), `addons/sale/models/sale_order.py` (lines 11, 471–862)

---

## When to Use

- Filtering records in `search()`, `search_count()`, `search_read()`
- Restricting Many2one / Many2many field choices via `domain=`
- Defining record rules (`domain_force`)
- Building dynamic queries in business logic

---

## Domain Syntax — List Form

```python
# Basic condition tuple: (field_name, operator, value)
[('state', '=', 'posted')]
[('amount_total', '>', 1000.0)]
[('partner_id', '!=', False)]

# Multiple conditions are AND-ed by default
[('state', '=', 'posted'), ('company_id', '=', 1)]
# Equivalent explicit form:
['&', ('state', '=', 'posted'), ('company_id', '=', 1)]

# OR combinator (prefix notation)
['|', ('state', '=', 'draft'), ('state', '=', 'posted')]

# NOT combinator
['!', ('active', '=', True)]

# Nested: (A OR B) AND C
['&', '|', ('type', '=', 'out_invoice'), ('type', '=', 'in_invoice'),
           ('state', '=', 'posted')]
```

---

## Domain Operators

| Operator | Meaning | Notes |
|----------|---------|-------|
| `=` | Equal | Works on all scalar types |
| `!=` | Not equal | |
| `>`, `>=`, `<`, `<=` | Comparison | Numeric, date, datetime |
| `like` | SQL LIKE (case-sensitive) | `%value%` not added automatically |
| `ilike` | Case-insensitive LIKE | Most common text search |
| `not ilike` | Inverse ilike | |
| `in` | Value in list | `('state', 'in', ['draft', 'posted'])` |
| `not in` | Value not in list | |
| `=like` | Pattern match (SQL LIKE) | Use `%` and `_` wildcards |
| `=ilike` | Case-insensitive pattern | |
| `child_of` | Hierarchical: record or its descendants | Requires `_parent_name` on model |
| `parent_of` | Hierarchical: record or its ancestors | |
| `any` | At least one related record matches sub-domain | x2many fields |
| `not any` | No related record matches sub-domain | x2many fields |

---

## Domain Class API (Odoo 17+)

```python
# addons/account/models/account_move.py (lines 21, 2503–2505, 4567–4570)
from odoo.fields import Domain

# Constructor forms
Domain('state', '=', 'posted')                        # single condition
Domain([('state', '=', 'posted'), ('active', '=', True)])  # from list

# Boolean algebra
d1 = Domain('state', '=', 'posted')
d2 = Domain('company_id', '=', 1)

combined_and = d1 & d2          # AND
combined_or  = d1 | d2          # OR
negated      = ~d1              # NOT

# Class-level combinators
Domain.AND([d1, d2, Domain.TRUE])
Domain.OR([d1, d2, Domain.FALSE])

# Sentinel values
Domain.TRUE    # matches everything: []
Domain.FALSE   # matches nothing

# Real usage from account_move.py
domain = Domain('state', '=', 'posted')
domain &= Domain('restrict_mode_hash_table', '=', True)
domain &= Domain('sequence_number', '>', last_move_hashed.sequence_number)

# OR across journal groups
Domain.OR([
    Domain('journal_id', 'not in', group.excluded_journal_ids.ids)
    & Domain('journal_id.company_id', '=?', group.company_id.id)
    for group in groups
])
```

---

## Traversing Relations in Domains

```python
# Dot notation traverses Many2one chains
[('journal_id.type', '=', 'sale')]
[('partner_id.country_id.code', '=', 'US')]
[('line_ids.account_id.account_type', '=', 'asset_receivable')]

# x2many field: 'any' / 'not any' with sub-domain (Odoo 17+)
Domain('line_ids', 'any', Domain('tax_ids', '!=', False))

# Older form still supported:
[('line_ids.tax_ids', '!=', False)]   # implicit EXISTS on x2many
```

---

## Using Domains in Code

```python
# addons/sale/models/sale_order.py (line 1306)

# search() with domain list
pending_orders = self.env['sale.order'].search([
    ('state', 'in', ['draft', 'sent']),
    ('pending_email_template_id', '!=', False),
])

# filtered() on an existing recordset (Python-side, no SQL)
confirmed = self.filtered(lambda so: so.state == 'sale')
invoiceable = order.order_line.filtered(lambda l: not l.display_type)

# mapped() to extract a field value list
dates = order.order_line.mapped('date_planned')
names = partners.mapped('display_name')

# search_count()
count = self.env['account.move'].search_count([('state', '=', 'posted')])
```

---

## Domains on Field Definitions

```python
# addons/account/models/account_move.py (lines 167, 194, 333)

# Domain on a Many2one field restricts selectable values in the UI
journal_id = fields.Many2one(
    'account.journal',
    domain="[('id', 'in', suitable_journal_ids)]",   # string form: evaluated client-side
)

# Domain on One2many restricts which children are included
invoice_line_ids = fields.One2many(
    'account.move.line', 'move_id',
    domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
)

# Domain using res_model for attachment filtering
attachment_ids = fields.One2many(
    'ir.attachment', 'res_id',
    domain=[('res_model', '=', 'account.move')],
)
```

---

## Dynamic Domains (Context-Dependent)

```python
# String domains are evaluated client-side with form record values as context
journal_id = fields.Many2one(
    domain="[('type', '=', move_type), ('company_id', '=', company_id)]"
)
```

In search views, domains can reference `uid`, `context`, `current_date`:

```xml
<filter string="My Orders" domain="[('user_id','=',uid)]"/>
<filter string="This Month"
        domain="[('date_order','&gt;=', (context_today() + relativedelta(day=1)).strftime('%Y-%m-%d'))]"/>
```

---

## Common Pitfalls

- **Prefix AND/OR is easy to get wrong.** `['|', A, B, C]` means `A OR B` AND `C` (the `|` consumes exactly two operands). Use `Domain` class operators (`|`, `&`) to avoid miscount.
- **`filtered()` runs in Python, not SQL** — it fetches all matching records first, then filters. Use `search()` with a domain for large datasets.
- **`False` vs `None` in domains:** Odoo uses `False` for empty Many2one. `('partner_id', '=', False)` finds records with no partner. Python `None` is not valid in domain tuples.
- **String domains on field definitions** are evaluated in the browser with form field values as local variables. Python domains in `search()` calls use Python values directly.
- **`=?` operator** (seen in account_move.py): matches if value is `False`/`None` (accepts all) or performs `=` otherwise. Useful for optional filter fields.
- **`child_of` requires the model to have `_parent_name`** defined (default `'parent_id'`). It generates a recursive SQL query — avoid on large unbounded trees.

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — `search()` and `_order` on models
- [field-definition-pattern.md](./field-definition-pattern.md) — `domain=` on relational fields
- [security-model-pattern.md](./security-model-pattern.md) — `domain_force` in record rules
- [api-decorator-pattern.md](./api-decorator-pattern.md) — `_search_<field>` for searchable computed fields
