from odoo import models, fields, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_line = fields.One2many(comodel_name="account.payment", inverse_name="sale_id")

    def action_advance_payment(self):
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payment.wizard",
            "view_id": self.env.ref("eg_advance_payment_for_sale.advance_payment_wizard_form_view").id,
            "type": "ir.actions.act_window",
            "target": "new"
        }
