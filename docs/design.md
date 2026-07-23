# Invoice Agent — Design & Architecture

## 1. Core Accounting Mechanics: `account.move` & `account.move.line`

### 1.1 Header vs. Lines

| Concept | `account.move` (Header) | `account.move.line` (Legs) |
|---------|------------------------|----------------------------|
| Represents | The journal entry / invoice as a whole | Each debit/credit leg of the entry |
| Lifecycle | Draft → Posted → Cancel | Tied to parent `move_id`; cascade-deleted |
| Amount fields | `amount_untaxed`, `amount_tax`, `amount_total` (computed from lines) | `debit`, `credit`, `balance`, `amount_currency` |
| Key FK | `line_ids` (all), `invoice_line_ids` (subset: `display_type` in product/section/note) | `move_id` (required) |
| State machine | `state` = draft → posted → cancel | `parent_state` = related (stored) |

### 1.2 `display_type` Values

Only these `display_type` values exist on `account.move.line`:

| Value | Purpose | Accountable? | Counts in `_compute_amount`? |
|-------|---------|-------------|------------------------------|
| `product` | Invoice line item | Yes | Untaxed amount |
| `tax` | Auto-generated tax line | Yes | Tax amount |
| `rounding` | Cash rounding line | Yes | Depends on `tax_repartition_line_id` |
| `payment_term` | Receivable/Payable due | Yes | Residual amount |
| `epd` | Early payment discount | Yes | Reduces total |
| `discount` | Discount allocation | Yes | --- |
| `line_section` | Visual section header | No | No |
| `line_subsection` | Visual subsection header | No | No |
| `line_note` | Visual note | No | No |
| `cogs` | Cost of goods sold | Yes | --- |
| `non_deductible_product` | Partial ded. product line | Yes | Untaxed |
| `non_deductible_product_total` | Sum of non-deductible | Yes | Untaxed |
| `non_deductible_tax` | Tax on non-deductible | Yes | Tax |

### 1.3 Debit/Credit Balance Invariant

Every `account.move` **must** satisfy: `SUM(line.debit) = SUM(line.credit)`.

The field chain:

```
Manual input via form:
  debit/credit  →  _inverse_debit / _inverse_credit
                    → sets line.balance = debit - credit
                    → calls _compute_balance (for entries, auto-balances)
                    
Programmatic create/write:
  balance (preferred)  →  _compute_debit_credit
                          → debit = balance if > 0 else 0
                          → credit = -balance if < 0 else 0
```

**Enforcement**: `_check_balanced` runs inside `create()` and `write()` for the **container** (moves being mutated). It queries:

```sql
SELECT line.move_id,
       ROUND(SUM(line.debit), currency.decimal_places) debit,
       ROUND(SUM(line.credit), currency.decimal_places) credit
  FROM account_move_line line
  JOIN account_move move ON move.id = line.move_id
  JOIN res_company company ON company.id = move.company_id
  JOIN res_currency currency ON currency.id = company.currency_id
 WHERE line.move_id IN %s
 GROUP BY line.move_id, currency.decimal_places
HAVING ROUND(SUM(line.balance), currency.decimal_places) != 0
```

If **any** move in the batch is unbalanced, a `UserError("The entry is not balanced.")` is raised.

### 1.4 `move_type` Selections

| Value | Direction | Doc Type |
|-------|-----------|----------|
| `entry` | Neutral | Misc journal entry |
| `out_invoice` | Outbound | Customer invoice |
| `out_refund` | Inbound | Customer credit note |
| `in_invoice` | Inbound | Vendor bill |
| `in_refund` | Outbound | Vendor credit note |
| `out_receipt` | Outbound | Sales receipt |
| `in_receipt` | Inbound | Purchase receipt |

Helpers: `is_invoice()`, `is_sale_document()`, `is_purchase_document()`, `is_inbound()`, `is_outbound()`.

### 1.5 State Machine

```
  ┌──────────┐
  │  Draft   │ ◄─────────────────────┐
  └────┬─────┘                       │
       │ action_post() / _post()     │ button_draft()
       ▼                             │
  ┌──────────┐     button_cancel()   │
  │  Posted  │ ──────────────────► ┌────────┐
  │          │                     │ Cancel │
  │  (hashed)│                     └────────┘
  └──────────┘
```

- `button_draft()` resets posted/cancel moves back to draft (only if no hash, no CABA entries, no exchange diff).
- `button_cancel()` first calls `button_draft()` then sets `state = 'cancel'`.
- `_post(soft=True)` sets `auto_post='at_date'` for future-dated moves; `_post(soft=False)` immediately posts.

---

## 2. Balance, `amount_currency`, `price_subtotal`, `_compute_totals`

### 2.1 Field Definitions & Compute Chains

```
balance (stored, computed)
  │ depends: move_id (for entries: auto-balance from other lines)
  │ For invoices: defaults to 0 (derived from amount_currency/rate)
  ▼
debit / credit (stored, computed)
  │ @api.depends('balance')
  │ debit = balance > 0 ? balance : 0
  │ credit = balance < 0 ? -balance : 0
  │ (inverted for storno)
  ▼
amount_currency (stored, computed)
  │ @api.depends('currency_rate', 'balance')
  │ = currency_id.round(balance * currency_rate)
  ▼
currency_rate (computed)
  │ @api.depends('currency_id', 'company_id', 
  │              'move_id.invoice_currency_rate', 'move_id.date')
  │ For invoices: = invoice_currency_rate (from header)
  │ For entries: rate lookup on date
```

For **invoice lines** (display_type='product'):

```
price_unit (stored, computed)
  │ @api.depends('product_id', 'product_uom_id')
  │ Default from product list/cost price
  ▼
price_subtotal / price_total (stored, computed)
  │ @api.depends('quantity', 'discount', 'price_unit', 
  │              'tax_ids', 'currency_id')
  │ Uses _prepare_product_base_line_for_taxes_computation()
  │ → AccountTax._add_tax_details_in_base_line()
  │ → AccountTax._round_base_lines_tax_details()
  │ Result: price_subtotal = total_excluded_currency
  │         price_total     = total_included_currency
```

### 2.2 Header `_compute_amount` Chain

```python
@api.depends(
    'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
    'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    ...  # many reconciliation + line balance deps
    'line_ids.balance',
    'line_ids.currency_id',
    'line_ids.amount_currency',
    'line_ids.amount_residual',
    'line_ids.amount_residual_currency',
    'line_ids.payment_id.state',
    'line_ids.full_reconcile_id',
    'state')
```

Iterates lines, groups by `display_type`:
- `product` / `rounding` / `non_deductible_product*` → untaxed
- `tax` / `non_deductible_tax` → tax
- `payment_term` → residual

Then applies `direction_sign` (±1).

### 2.3 What Happens When an Agent Writes Programmatically

If an **LLM/agent calls `line.write({'price_unit': ...})`** or creates lines via `Command.create(...)`, the recompute cascade is:

```
write(price_unit)
  → _compute_totals triggered (price_subtotal/price_total recompute)
  → _sync_tax_lines triggered (within write's _sync_dynamic_lines)
  → tax lines created/updated/deleted
  → _compute_amount triggered on header (amount_untaxed, amount_total etc.)
  → _check_balanced validates debits = credits
```

Key: `@api.depends` chains fire automatically. The agent never needs to call recompute manually — the ORM handles it.

---

## 3. Creating a Vendor Bill from the Shell

### 3.1 Minimal Create

```python
partner = env.ref('base.res_partner_1')
product = env.ref('product.product_product_4')
account_payable = env['account.account'].search([('account_type', '=', 'liability_payable')], limit=1)
account_expense = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
tax = env['account.tax'].search([('type_tax_use', '=', 'purchase')], limit=1)

bill = env['account.move'].create({
    'move_type': 'in_invoice',
    'partner_id': partner.id,
    'journal_id': journal.id,
    'invoice_date': '2026-07-01',
    'invoice_date_due': '2026-08-01',
    'ref': 'INV-2026-001',
    'invoice_line_ids': [
        Command.create({
            'product_id': product.id,
            'quantity': 10,
            'price_unit': 100.0,
            'tax_ids': [Command.set(tax.ids)],
            'account_id': account_expense.id,
            'name': 'Widget consulting',
        }),
    ],
})
```

### 3.2 Post and Inspect

```python
bill.action_post()

# Lines Odoo auto-generated:
for line in bill.line_ids:
    print(f"{line.display_type:30s} | {line.account_id.code:10s} | "
          f"{line.debit:>10.2f} | {line.credit:>10.2f} | {line.name or ''}")
```

Output will show:

| display_type | Account | Debit | Credit | Name |
|-------------|---------|-------|--------|------|
| product | Expense | 1000.00 | 0.00 | Widget consulting |
| tax | Tax account | 150.00 | 0.00 | 15% VAT |
| payment_term | Payable | 0.00 | 1150.00 | INV-2026-001 |

Odoo generated:
1. **Tax line** (display_type='tax') — computed from `tax_ids` on the product line
2. **Payment term line** (display_type='payment_term') — the payable account leg balancing the entry

You never wrote these — they come from `_sync_tax_lines` and `_sync_dynamic_line` (payment_term) inside the `_sync_dynamic_lines` context manager on `create()` and `write()`.

---

## 4. LLM Extraction → Create Dict Mapping

### 4.1 Payload Mapping

| LLM Extraction Field | `create()` key | Notes |
|---------------------|---------------|-------|
| Vendor name/ID | `partner_id` | Resolve via `res.partner` search |
| Invoice number | `ref` | Stored as Char, indexed |
| Invoice date | `invoice_date` | Must be set for posting |
| Due date | `invoice_date_due` | Computed from payment terms if omitted |
| Currency | `currency_id` | Defaults to company currency |
| Line items | `invoice_line_ids: [Command.create({...})]` | See below |

**Per line-item mapping:**

| LLM Field | `Command.create` key | Notes |
|-----------|---------------------|-------|
| Description | `name` | Line label |
| Quantity | `quantity` | Default 1 if missing |
| Unit price | `price_unit` | Float |
| Tax rate(s) | `tax_ids: [Command.set([ids])]` | Resolve tax by % + country |
| Line total | *Never force* | Computed from `qty × price_unit × tax` |
| Account | `account_id` | Default from product or journal |

### 4.2 Fields Odoo Computes — NEVER Force in Create Dict

These fields are **strictly computed** — writing them will either be ignored or cause conflicts:

| Field | Why never force |
|-------|----------------|
| `debit` / `credit` | Derived from `balance` |
| `balance` | On invoices: computed from `amount_currency` / `currency_rate` |
| `amount_currency` | Computed from `balance × currency_rate` |
| `price_subtotal` | Computed from `qty × price_unit × taxes` |
| `price_total` | Computed from `qty × price_unit × taxes` |
| `amount_untaxed` / `amount_tax` / `amount_total` | Header fields computed from line aggregation |
| `currency_rate` | From header `invoice_currency_rate` or date lookup |
| `display_type` | Defaults to `'product'` for invoice lines |
| `sequence` | Defaults to 100, auto-sequenced |
| `date` | Related to `move_id.date` |
| `partner_id` | Related from header on invoice lines |

### 4.3 Example: Full Create Dict from LLM Output

```python
# Assuming resolved references:
partner_id, product_id, account_expense_id, tax_ids = ...

vals = {
    'move_type': 'in_invoice',
    'partner_id': partner_id,
    'ref': 'INV-AI-0042',
    'invoice_date': '2026-07-15',
    'invoice_date_due': '2026-08-14',
    'currency_id': env.ref('base.EUR').id,
    'invoice_line_ids': [
        Command.create({
            'product_id': product_id,          # optional; helps default account/taxes
            'name': 'AI Consulting Services',
            'quantity': 1.0,
            'price_unit': 1500.00,
            'tax_ids': [Command.set(tax_ids)],  # resolved tax IDs
            'account_id': account_expense_id,   # fallback if product lacks account
        }),
        Command.create({
            'name': 'Software License',
            'quantity': 3,
            'price_unit': 200.00,
            'tax_ids': [Command.set(tax_ids)],
            'account_id': account_expense_id,
        }),
    ],
}

bill = env['account.move'].create(vals)
bill.action_post()
```

---

## 5. Posting Flow Trace

When `action_post()` is called on a vendor bill:

```
action_post()
  │
  ├─ _post(soft=False)
  │    │
  │    ├─ Validates: no negative total, partner required, invoice_date required
  │    │             (for purchase docs), journal active, no archived accounts
  │    │
  │    ├─ Checks lock dates; adjusts date if locked
  │    │
  │    ├─ line_ids._create_analytic_lines()
  │    │
  │    ├─ _copy_recurring_entries() [if auto_post != 'no']
  │    │
  │    ├─ write({'state': 'posted', 'posted_before': True})
  │    │    │
  │    │    ├─ _sync_dynamic_lines (inside write)
  │    │    │    ├─ _sync_dynamic_line(payment_term) → creates payable leg
  │    │    │    ├─ _sync_rounding_lines
  │    │    │    ├─ _sync_dynamic_line(discount)
  │    │    │    ├─ _sync_tax_lines → creates/updates tax lines
  │    │    │    ├─ _sync_non_deductible_base_lines
  │    │    │    ├─ _sync_dynamic_line(epd)
  │    │    │    └─ _sync_invoice → syncs partner on lines
  │    │    │
  │    │    ├─ _check_balanced → SUM(debits) = SUM(credits)
  │    │    │
  │    │    └─ _hash_moves() [if journal.restrict_mode_hash_table]
  │    │
  │    ├─ line_ids._reconcile_marked()
  │    │
  │    └─ Partner rank update (supplier/customer)
  │
  └─ _show_autopost_bills_wizard() [returns wizard or False]
```

---

## 6. Extending Core Safely

### 6.1 Adding Fields is Cheap

Adding a stored field (no compute, no inverse) to `account.move` via `_inherit` is safe and does not interfere with Odoo's accounting logic.

```python
class AccountMove(models.Model):
    _inherit = 'account.move'
    my_field = fields.Char()
```

### 6.2 What NOT to Do

| Action | Risk | Alternative |
|--------|------|-------------|
| Override `create()` without `super()` and `_check_balanced` | Break balance invariant | Add `@api.model_create_multi` with `super().create()` |
| Override `write()` without `_sync_dynamic_lines` | Tax/payable lines out of sync | Use `write()` → add fields in `vals`, call `super().write()` |
| Override `_post()` | Break state machine | Use `_post` as hook point carefully, always `super()._post()` |
| **Redefine a core field's compute** | Conflict with core module | **Never do this** — use a new field |
| Override `action_post()` | Break validations | Use `_post()` or add a method that calls `super().action_post()` |

### 6.3 `super()` Discipline

Always follow this pattern:

```python
def create(self, vals_list):
    # Pre-processing: enrich vals_list
    moves = super().create(vals_list)
    # Post-processing: operate on the created records
    for move in moves:
        move._do_something()
    return moves
```

### 6.4 View Inheritance with `xpath`

```xml
<xpath expr="//notebook" position="inside">
    <page string="My Page">
        ...
    </page>
</xpath>
```

Key `position` attributes:
- `inside` — append inside the matched element
- `after` / `before` — insert sibling after/before
- `replace` — replace the element entirely
- `attributes` — modify element attributes

Use specific, stable XPath expressions (e.g., `//notebook[@class='o_notebook']`) to avoid conflicts with other modules.

---

## 7. AI Extraction Fields on `account.move`

The following fields are added via `_inherit = 'account.move'` in `invoice_agent`:

| Field | Type | Purpose |
|-------|------|---------|
| `ai_source_attachment_id` | Many2one → `ir.attachment` | The scanned PDF/image that was processed |
| `ai_ocr_text` | Text | Raw extracted OCR text |
| `ai_model_used` | Char | AI model identifier |
| `ai_review_required` | Boolean (tracking) | Needs human review |
| `ai_extraction_status` | Selection | pending/extracted/validated/failed |
| `ai_confidence` | Float (0–1) | Overall confidence |
| `ai_extracted_json` | Json | Raw LLM response payload |
| `ai_extracted_on` | Datetime | Extraction completion |
| `ai_validated_on` | Datetime | Validation timestamp |
| `extraction_line_ids` | One2many | Per-field extraction lines |

No compute conflicts: all fields are simple stored fields with no `@api.depends`, no `compute`, no `inverse`. They do not intersect with any core accounting field.

---

## 8. Filesystem Store Persistence (EC2)

`ir.attachment` binary data is stored in the filestore at `{data_dir}/filestore/{db_name}/`.

On EC2 with Docker:

```yaml
volumes:
  - odoo-filestore:/var/lib/odoo/filestore
```

The `/var/lib/odoo/filestore` directory persists across `docker compose restart` because it's a named volume. The actual binary files live in subdirectories by first two hex chars of their checksum.

To verify on EC2:

```bash
docker compose exec odoo ls -la /var/lib/odoo/filestore/{db_name}/
```

Attachments linked through `ai_source_attachment_id` will survive restarts if the volume is not deleted.

---

## 9. Invoice Agent Module Structure

```
custom_addons/invoice_agent/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── account_move.py              # AI fields on account.move
│   └── invoice_agent_extraction_line.py  # Per-field extraction lines
├── views/
│   └── account_move_views.xml       # AI Extraction notebook page
├── security/
│   └── ir.model.access.csv          # ACLs for extraction lines
├── data/
├── static/
└── runbook.md
