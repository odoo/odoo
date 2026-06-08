# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from markupsafe import Markup

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _process(self, payment_data):
        """Override of `payment` to allow retrying if the transaction is canceled or has an error,
        by redirecting the user back to the payment page."""
        super()._process(payment_data)
        if self.sale_order_ids.website_id and self.state in ["cancel", "error"]:
            default_msg = self.env._("Payment was not successful, please try again.")
            params = {"error_msg": self.state_message or default_msg}
            self.landing_route = f"/shop/payment?{urlencode(params)}"

    def _get_status_message(self, *, order=None, **kwargs):
        """Override of `payment` to add a custom message when the cart amount is different after
        payment in `website_sale`.

        :param sale.order order: The current cart linked to the transaction.
        """
        if (
            order
            and order.website_id
            and self.state == "done"
            and order.amount_total != self.amount
        ):
            return Markup("<p>%s</p>") % self.env._(
                "Unfortunately your order can not be confirmed as the amount of your payment"
                " does not match the amount of your cart. Please contact the responsible of"
                " the shop for more information."
            )
        return super()._get_status_message(order=order, **kwargs)
