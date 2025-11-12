# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        # Override to cancel linked `payment.transaction`s pending a payment on delivery. The sale
        # orders that are settled in the Point of Sale are paid there, so their promise of a payment
        # on delivery is superseded and must be canceled.
        data = super().sync_from_ui(orders)
        pos_orders = self.browse([o['id'] for o in data["pos.order"]])
        for pos_order in pos_orders.filtered(lambda po: po.state == "paid"):
            sale_orders = pos_order.lines.sale_order_line_id.order_id
            transactions = sale_orders.sudo().transaction_ids
            transactions._filtered_pending_delivery_payment().with_context(
                payment_safe_write=True
            )._set_canceled(
                state_message=self.env._("The order was settled in the Point of Sale.")
            ).is_post_processed = True

        return data
