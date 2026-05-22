# API Decorator Pattern

**Purpose:** Hook Python methods into the ORM lifecycle using decorators from `odoo.api`. These decorators declare dependencies, trigger recomputation, validate invariants, and react to UI changes — without requiring manual wiring.

**Source:** `odoo/api/`, `addons/account/models/account_move.py` (lines 803–2856), `addons/account/models/account_tax.py` (line 65)

---

## When to Use

| Decorator | When |
|-----------|------|
| `@api.depends` | A field value must be recomputed when other fields change |
| `@api.depends_context` | Recompute also when context keys change (e.g., `lang`, `uid`) |
| `@api.constrains` | Enforce a cross-field business rule; raise `ValidationError` on violation |
| `@api.onchange` | React to UI edits in real-time (form view only, not persisted) |
| `@api.model` | Method operates on the model class, not on a specific recordset (no `self` record) |
| `@api.model_create_multi` | Override `create()` to handle batch creation (replaces `@api.model` on create) |

---

## @api.depends — Computed Field Trigger

```python
# addons/account/models/account_move.py (lines 847–862)

@api.depends('invoice_date', 'company_id', 'move_type', 'taxable_supply_date')
def _compute_date(self):
    """Set accounting date from invoice date when not manually set."""
    for move in self:
        if not move.invoice_date:
            move.date = fields.Date.context_today(self)
        elif not move.date:
            move.date = move.invoice_date

# Multi-level dependency (dot notation traverses relations)
@api.depends('line_ids.account_id.account_type')
def _compute_always_tax_exigible(self):
    for move in self:
        move.always_tax_exigible = all(
            line.account_id.account_type in ('asset_cash', 'liability_credit_card')
            for line in move.line_ids
            if line.account_id
        )
```

---

## @api.depends_context — Context-Sensitive Recomputation

```python
# addons/account/models/account_move.py (lines 975–986)

@api.depends_context('lang')          # re-run when user language changes
@api.depends('move_type')
def _compute_type_name(self):
    type_name_mapping = {
        'entry':       _('Journal Entry'),
        'out_invoice': _('Invoice'),
        'in_invoice':  _('Vendor Bill'),
    }
    for move in self:
        move.type_name = type_name_mapping.get(move.move_type, '')
```

---

## @api.constrains — Business Rule Enforcement

```python
# addons/account/models/account_move.py (lines 2815–2856)

@api.constrains('auto_post', 'invoice_date')
def _require_bill_date_for_autopost(self):
    """Vendor bills must have an invoice date to be auto-posted."""
    for record in self:
        if record.auto_post != 'no' and record.is_purchase_document() and not record.invoice_date:
            raise ValidationError(
                _("For this entry to be automatically posted, it required a bill date.")
            )

@api.constrains('journal_id', 'move_type')
def _check_journal_move_type(self):
    for move in self:
        if move.is_purchase_document(include_receipts=True) and move.journal_id.type != 'purchase':
            raise ValidationError(_("Cannot create a purchase document in a non purchase journal"))

@api.constrains('invoice_currency_rate')
def _check_invoice_currency_rate(self):
    for move in self:
        if (
            move.currency_id
            and move.company_id
            and move.currency_id != move.company_id.currency_id
            and move.is_invoice(include_receipts=True)
            and move.invoice_currency_rate <= 0
        ):
            raise ValidationError(_("The currency rate must be strictly positive."))
```

---

## @api.onchange — Real-Time UI Reaction

```python
# addons/account/models/account_move.py (lines 2572–2637)

@api.onchange('partner_id')
def _onchange_partner_id(self):
    """Update payment term and bank account when partner changes in form."""
    if self.partner_id:
        self.invoice_payment_term_id = self.partner_id.property_payment_term_id
    else:
        self.invoice_payment_term_id = False

@api.onchange('journal_id')
def _onchange_journal(self):
    if self.journal_id and self.journal_id.currency_id:
        self.currency_id = self.journal_id.currency_id
```

---

## @api.model — Class-Level Method

```python
# addons/account/models/account_move.py (line 3225)

@api.model
def _get_default_journal(self):
    """Return the default journal for the current company and move type."""
    return self.env['account.journal'].search(
        self._search_default_journal(), limit=1
    )
```

---

## @api.model_create_multi — Batch Create Override

```python
# addons/account/models/account_move.py (lines 3853–3870)

@api.model_create_multi
def create(self, vals_list):
    """vals_list is always a list of dicts, even for single-record creation."""
    if any(vals.get('state') == 'posted' for vals in vals_list):
        raise UserError(_('You cannot create a move already in the posted state.'))
    for vals in vals_list:
        self._sanitize_vals(vals)
    moves = super().create(vals_list)
    moves.is_manually_modified = False
    return moves
```

---

## Decorator Rules and Interactions

```
Execution order for a field write:
  1. write() called
  2. @api.constrains methods checked (raise ValidationError to abort)
  3. @api.depends triggers recompute of dependent computed fields
  4. @api.onchange fires only in UI context (not on write/create)

@api.depends chains:
  - Transitive: if A depends on B and B depends on C, changing C reruns both
  - Dot notation: 'line_ids.tax_ids.country_id' traverses One2many → Many2many → Many2one
  - Use 'line_ids' (no dot) to trigger on any change to the One2many set itself
```

---

## Common Pitfalls

- **`@api.onchange` does not persist.** Changes it makes are only visible in the browser form until the record is saved. Server-side logic (cron, RPC) never triggers `@api.onchange`.
- **`@api.constrains` on relational fields:** Declare the field name, not the sub-field — `@api.constrains('line_ids')` fires on any child change; `@api.constrains('line_ids.tax_ids')` is not valid.
- **`@api.depends` with stored=False fields:** If the computed field has `store=False`, it is recomputed on every read, not on field change. `@api.depends` still controls cache invalidation.
- **`@api.model_create_multi` replaces `@api.model` on `create`** — never combine both on `create`. The ORM always passes a list; single-record creation is `vals_list = [vals]`.
- **Missing `for record in self` loop in `@api.constrains`:** The decorator receives the full recordset, not one record. Always iterate.

---

## Related Patterns

- [field-definition-pattern.md](./field-definition-pattern.md) — `compute=` and `store=` on fields
- [orm-model-pattern.md](./orm-model-pattern.md) — model class structure
- [test-case-pattern.md](./test-case-pattern.md) — testing constraint violations with `assertRaises`
