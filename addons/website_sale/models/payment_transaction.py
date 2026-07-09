# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from markupsafe import Markup

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _process(self, payment_data):
        """Override of `payment` to append payment status message to the landing route."""
        super()._process(payment_data)
        if self.sale_order_ids.website_id:
            url_params = {}
            if self.state in ["cancel", "error"]:
                # Prepare the failed payment notification message
                default_msg = self.env._("Payment was not successful, please try again.")
                url_params = {
                    "payment_msg": self.state_message or default_msg,
                    "payment_msg_type": "danger",
                }
            elif self.state in {"authorized", "done"} and self.sale_order_ids._is_partially_paid():
                # Prepare the split payment notification message
                url_params = {
                    "payment_msg": self.env._(
                        "Your payment of %(formatted_amount)s has been processed. Pay the remaining"
                        " amount to confirm your order.",
                        formatted_amount=self.currency_id.format(self.amount),
                    ),
                    "payment_msg_type": "success",
                }
            # Update the landing route with the payment status message
            if url_params:
                self.landing_route = f"/shop/payment?{urlencode(url_params)}"

    def _get_status_message(self, *, order=None, **kwargs):
        """Override of `payment` to add custom messages for website orders.

        :param sale.order order: The current cart linked to the transaction.
        """
        if order and order.website_id:
            if self.state == "done" and not order._is_paid():
                return Markup("<p>%s</p>") % self.env._(
                    "Unfortunately your order can not be confirmed as the amount of your payment"
                    " does not match the amount of your cart. Please contact the responsible of"
                    " the shop for more information."
                )
            if self.state == "pending" and self._requires_payment_instructions():
                return Markup("<p>%s</p>") % self.env._(
                    "Your order will be confirmed after payment is received."
                )
        return super()._get_status_message(order=order, **kwargs)
