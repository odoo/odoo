# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # ------------------------------------------------------------------
    # Smart button: from a Purchase Order back to the vendor
    # "Prepare Payments" documents that group its vendor bills.
    # ------------------------------------------------------------------
    od19_prepayment_count = fields.Integer(
        string="Prepare Payment count",
        compute="_compute_od19_prepayment_count",
        groups="account.group_account_invoice",
    )

    def _compute_od19_prepayment_count(self):
        for order in self:
            order.od19_prepayment_count = len(order._od19_prepayments())

    def _od19_prepayments(self):
        """Vendor "Prepare Payments" documents of the bills of this order."""
        self.ensure_one()
        return self.invoice_ids.billing_ids.filtered(
            lambda billing: billing.bill_type == "in_invoice"
        )

    def action_od19_open_prepayments(self):
        """Open the Prepare Payments documents linked to this order."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Prepare Payments"),
            "res_model": "account.billing",
            "view_mode": "list,form",
            "domain": [("id", "in", self._od19_prepayments().ids)],
            "context": {"create": False, "default_bill_type": "in_invoice"},
        }
