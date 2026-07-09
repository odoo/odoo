# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from markupsafe import Markup

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _process(self, payment_data):
        """Override of `payment` to redirect the user back to the payment page, in case of
        error/canceled transaction, or if we are awaiting the next split payment."""
        super()._process(payment_data)
        if self.sale_order_ids.website_id:
            params = {}
            if self.state in ["cancel", "error"]:
                default_msg = self.env._("Payment was not successful, please try again.")
                params = {
                    "payment_msg": self.state_message or default_msg,
                    "payment_msg_type": "danger",
                }
            elif self.sale_order_ids._is_awaiting_split_payment():
                params = {
                    "payment_msg": self.env._(
                        "A payment of %(formatted_amount)s has been processed. "
                        "Continue with the next payment to confirm your order.",
                        formatted_amount=self.currency_id.format(self.amount),
                    ),
                    "payment_msg_type": "success",
                }
                if self.state in ["authorized", "pending"]:
                    params["payment_msg_type"] = "info"
            if params:
                self.landing_route = f"/shop/payment?{urlencode(params)}"

    def _get_status_message(self, *, order=None, **kwargs):
        """Override of `payment` to add custom messages for website orders.

        :param sale.order order: The current cart linked to the transaction.
        """
        if order and order.website_id:
            if self.state == "done" and not order._is_paid_or_pending():
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
