from odoo import _, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="POS Order",
        readonly=True,
        help="The Point of Sale order linked to this payment",
    )

    def action_view_pos_order(self):
        """Return the action for the view of the pos order linked to the payment."""
        self.check_singleton()

        return {
            "name": _("POS Order"),
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "target": "current",
            "res_id": self.pos_order_id.id,
            "view_mode": "form",
        }
