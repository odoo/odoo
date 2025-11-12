# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PayOnDelivery(models.TransientModel):
    _name = "pay.on.delivery"
    _description = "Pay on Delivery"

    order_id = fields.Many2one(comodel_name="sale.order", required=True, readonly=True)
    amount_on_delivery = fields.Monetary(related="order_id.amount_on_delivery")
    currency_id = fields.Many2one(related="order_id.currency_id")

    def action_confirm_payment(self):
        self.ensure_one()
        if self.order_id._confirm_payment_on_delivery():
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "message": self.env._("The payment was collected successfully!"),
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                },
            }
        return True
