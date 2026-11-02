# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Smart button: from a payment (payment voucher) back to the vendor
    # "Prepare Payments" documents that group the bills it reconciles.
    # ------------------------------------------------------------------
    od19_prepayment_count = fields.Integer(
        string="Prepare Payment count",
        compute="_compute_od19_prepayment_count",
        groups="account.group_account_invoice",
    )

    def _compute_od19_prepayment_count(self):
        for payment in self:
            payment.od19_prepayment_count = len(payment._od19_prepayments())

    def _od19_prepayments(self):
        """Vendor "Prepare Payments" documents of the bills this payment pays."""
        self.ensure_one()
        return self.reconciled_bill_ids.billing_ids.filtered(
            lambda billing: billing.bill_type == "in_invoice"
        )

    def action_od19_open_prepayments(self):
        """Open the Prepare Payments documents linked to this payment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Prepare Payments"),
            "res_model": "account.billing",
            "view_mode": "list,form",
            "domain": [("id", "in", self._od19_prepayments().ids)],
            "context": {"create": False, "default_bill_type": "in_invoice"},
        }
