# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------------------------------------------------------
    # Smart button: from a Vendor Bill back to the "Prepare Payments"
    # documents (OCA ``account.billing`` with ``bill_type='in_invoice'``)
    # it has been grouped into.  The ``billing_ids`` link itself is provided
    # by the OCA ``account_billing`` module, this field only exposes the
    # count for the stat button.
    # ------------------------------------------------------------------
    od19_prepayment_count = fields.Integer(
        string="Prepare Payment count",
        compute="_compute_od19_prepayment_count",
        groups="account.group_account_invoice",
    )

    def _compute_od19_prepayment_count(self):
        for move in self:
            move.od19_prepayment_count = len(move._od19_prepayments())

    def _od19_prepayments(self):
        """Return the vendor "Prepare Payments" documents of this entry.

        Only the payable side is exposed; the customer side keeps the plain
        OCA "Billing" wording.
        """
        self.ensure_one()
        return self.billing_ids.filtered(lambda billing: billing.bill_type == "in_invoice")

    def action_od19_open_prepayments(self):
        """Open the Prepare Payments documents linked to this entry."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Prepare Payments"),
            "res_model": "account.billing",
            "view_mode": "list,form",
            "domain": [("id", "in", self._od19_prepayments().ids)],
            "context": {"create": False, "default_bill_type": "in_invoice"},
        }
