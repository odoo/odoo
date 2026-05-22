# Wizard / TransientModel Pattern

**Purpose:** Implement multi-step or confirmation dialogs that collect user input before executing a batch operation. Wizards use `models.TransientModel` — records are stored temporarily in the database and auto-vacuumed; they are never part of the permanent business data.

**Source:** `odoo/orm/models_transient.py`, `addons/account/wizard/account_payment_register_views.xml`, `addons/account/wizard/account_move_reversal_view.xml`, `addons/account/__manifest__.py` (wizard/ entries in `data`)

---

## When to Use

- Collecting parameters before a batch operation (e.g., "Register Payment" on invoices)
- Confirming a destructive action (e.g., "Cancel Invoice" with reason field)
- Multi-record actions triggered from list view action buttons
- Any workflow that needs transient state between user and server

---

## Python Model (models/TransientModel)

```python
# addons/account/wizard/account_payment_register.py
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _name = 'account.payment.register'
    _description = 'Register Payment'
    # No _order needed — transient records are short-lived

    # --- Input fields (collected from the user) ---
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('type', 'in', ('bank', 'cash'))],
    )
    memo = fields.Char(string='Memo')

    # --- Link back to the records being acted upon ---
    line_ids = fields.Many2many(
        'account.move.line',
        string='Journal Items',
    )

    # --- Computed / derived fields ---
    @api.depends('line_ids')
    def _compute_amount(self):
        for wizard in self:
            wizard.amount = sum(wizard.line_ids.mapped('amount_residual'))

    # --- Action method: the "Confirm" button calls this ---
    def action_create_payments(self):
        """Validate input, create real records, return window action to close dialog."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError("No invoice lines selected.")

        payments = self.env['account.payment'].create(
            self._prepare_payment_vals_list()
        )
        payments.action_post()

        # Return an action that closes the dialog and optionally opens a result view
        return {
            'type': 'ir.actions.act_window_close',
        }

    def _prepare_payment_vals_list(self):
        """Private helper: build the list of payment create dicts."""
        return [{
            'date': self.payment_date,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'journal_id': self.journal_id.id,
            'ref': self.memo,
        }]
```

---

## Wizard View (XML)

```xml
<!-- addons/account/wizard/account_payment_register_views.xml -->
<odoo>
    <record id="view_account_payment_register_form" model="ir.ui.view">
        <field name="name">account.payment.register.form</field>
        <field name="model">account.payment.register</field>
        <field name="arch" type="xml">
            <form string="Register Payment">
                <sheet>
                    <group>
                        <group>
                            <field name="payment_date"/>
                            <field name="journal_id"/>
                        </group>
                        <group>
                            <field name="amount"/>
                            <field name="currency_id" options="{'no_create': True}"/>
                        </group>
                    </group>
                    <group>
                        <field name="memo"/>
                    </group>
                </sheet>

                <!-- Footer: action buttons -->
                <footer>
                    <button name="action_create_payments"
                            string="Pay"
                            type="object"
                            class="btn-primary"/>
                    <button string="Cancel" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <!-- Action to open the wizard as a dialog -->
    <record id="action_account_payment_register" model="ir.actions.act_window">
        <field name="name">Register Payment</field>
        <field name="res_model">account.payment.register</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>   <!-- "new" = modal dialog -->
        <field name="binding_model_id" ref="account.model_account_move"/>
        <field name="binding_view_types">list,form</field>
    </record>
</odoo>
```

---

## Opening a Wizard from a Button (Python)

```python
# In a model method triggered by a button in a list/form view
def action_open_payment_wizard(self):
    """Create a wizard pre-populated with the selected records."""
    wizard = self.env['account.payment.register'].create({
        'line_ids': [Command.set(self.line_ids.ids)],
    })
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'account.payment.register',
        'res_id': wizard.id,
        'view_mode': 'form',
        'target': 'new',           # modal dialog
        'context': self.env.context,
    }
```

---

## Wizard in __manifest__.py

```python
# Wizard view XML goes in 'data', after security but before other views
{
    'data': [
        'security/ir.model.access.csv',             # must include wizard model ACL
        'wizard/account_payment_register_views.xml',
        'wizard/account_move_reversal_view.xml',
        'views/account_move_views.xml',              # views that reference wizard actions
    ],
}
```

---

## TransientModel vs Model

| Aspect | `models.TransientModel` | `models.Model` |
|--------|------------------------|----------------|
| DB table | Yes (temporary) | Yes (permanent) |
| Auto-cleanup | Yes (vacuumed periodically) | No |
| Appears in search | No (excluded by default) | Yes |
| Use case | Wizards, dialogs, batch params | Business entities |
| `_transient_max_count` | Configurable (default 100) | N/A |
| `_transient_max_hours` | Configurable (default 1 hr) | N/A |

---

## Return Actions from Wizard Methods

```python
class MyWizard(models.TransientModel):
    _name = 'my.wizard'

    def action_confirm(self):
        # Close the dialog (most common)
        return {'type': 'ir.actions.act_window_close'}

    def action_open_result(self):
        # Open a resulting record after creation
        payment = self.env['account.payment'].create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_notify_and_close(self):
        # Show a notification and close
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment registered.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
```

---

## Common Pitfalls

- **Wizard records are not permanent** — never reference a `TransientModel` record ID after the request completes. The record may be vacuumed at any time.
- **`target: 'new'`** in the action is what makes it a dialog. Without it the view opens as a full page, which is confusing for wizard-style flows.
- **Missing ACL in `ir.model.access.csv`** — TransientModels still require access rules. Typically grant `base.group_user` read+write+create+unlink.
- **`ensure_one()` in action methods** — wizard action methods should always call `self.ensure_one()` first since they operate on a single wizard instance.
- **`special="cancel"` on Cancel button** closes the dialog without calling any Python method — it does not call `unlink()`. Transient records are cleaned up by the vacuum cron.
- **Context passing:** The `active_ids` and `active_model` context keys are automatically set when a wizard is opened from a list-view action. Read them via `self.env.context.get('active_ids', [])` to know which records the wizard was invoked on.

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — `models.TransientModel` base class
- [view-definition-pattern.md](./view-definition-pattern.md) — form view with `<footer>` buttons
- [module-addon-structure-pattern.md](./module-addon-structure-pattern.md) — `wizard/` directory and manifest registration
- [api-decorator-pattern.md](./api-decorator-pattern.md) — `@api.depends` and `@api.model_create_multi` on wizard fields
