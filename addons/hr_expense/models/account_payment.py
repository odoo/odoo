from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    expense_ids = fields.One2many(related="move_id.expense_ids")

    def _compute_outstanding_account_id(self):
        expense_company_payments = self.filtered(
            lambda payment: payment.expense_ids.payment_mode == "company_account"
        )
        for payment in expense_company_payments:
            payment.outstanding_account_id = (
                payment.expense_ids._get_expense_account_destination()
            )
        super(
            AccountPayment, self - expense_company_payments
        )._compute_outstanding_account_id()

    def _compute_show_require_partner_bank(self):
        expense_payments = self.filtered(lambda pay: pay.move_id.expense_ids)
        super()._compute_show_require_partner_bank()
        expense_payments.require_partner_bank_account = False

    def write(self, vals):
        trigger_fields = {
            "date",
            "amount",
            "payment_type",
            "partner_type",
            "payment_reference",
            "currency_id",
            "partner_id",
            "destination_account_id",
            "partner_bank_id",
            "journal_id",
            "ref",
            "payment_channel_id",
        }
        if self.expense_ids and any(
            field_name in trigger_fields for field_name in vals
        ):
            _debug.logic(
                "payment_write_refused",
                payments=self,
                expenses=self.expense_ids,
                fields=sorted(set(vals) & trigger_fields),
            )
            raise UserError(
                _(
                    "You cannot do this modification since the payment is linked to an expense."
                )
            )
        return super().write(vals)

    def action_view_expense(self):
        self.check_singleton()
        return {
            "name": self.expense_ids.name,
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": "hr.expense",
            "res_id": self.expense_ids.id,
        }

    def _creation_message(self):
        self.check_singleton()
        if self.move_id.expense_ids:
            return _(
                "Payment created for: %s", self.move_id.expense_ids._get_html_link()
            )
        return super()._creation_message()
