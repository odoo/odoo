# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Override of `account` to cancel the pending payment on delivery transactions of the
        orders that are now paid: their promise of a payment on delivery is superseded."""
        res = super().action_post()
        paid_orders = self.sale_order_id.filtered(lambda order: order._is_paid())
        paid_orders.sudo().transaction_ids._filtered_pending_pay_on_delivery().with_context(
            payment_safe_write=True  # No API call was made; safe to replay
        )._set_canceled(
            state_message=self.env._("The order was marked as paid.")
        ).is_post_processed = True
        return res
