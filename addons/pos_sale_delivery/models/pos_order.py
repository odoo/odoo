# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        # Override of `point_of_sale` to cancel linked pending payment on delivery transaction. The
        # sale orders that are settled in the Point of Sale are paid there, so their promise of a
        # payment on delivery is superseded and must be canceled.
        data = super().sync_from_ui(orders)
        paid_pos_orders = self.browse(o['id'] for o in data['pos.order']).filtered(
            lambda po: po.state == 'paid'
        )
        transactions_sudo = paid_pos_orders.lines.sale_order_origin_id.sudo().transaction_ids
        transactions_sudo._filtered_pending_pay_on_delivery().with_context(
            payment_safe_write=True  # No API call was made; safe to replay
        )._set_canceled(
            state_message=self.env._("The order was settled in the Point of Sale.")
        ).is_post_processed = True

        return data
