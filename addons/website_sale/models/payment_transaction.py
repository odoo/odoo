# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from markupsafe import Markup

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _send_invoice(self):
        """Override of `sale` to archive guest contacts."""
        super()._send_invoice()
        self.sale_order_ids.filtered(
            lambda so: so.state == "sale" and so.website_id
        )._archive_partner_if_no_user()

    def _process(self, provider_code, payment_data):
        """Override of `payment` to allow retrying if the transaction is canceled or has an error,
        redirecting to the payment page."""
        tx = super()._process(provider_code, payment_data)
        if tx.sale_order_ids.website_id and tx.state in ["cancel", "error"]:
            default_msg = self.env._("Payment was not successful, please try again.")
            params = {"error_msg": tx.state_message or default_msg}
            tx.landing_route = f"/shop/payment?{urlencode(params)}"
        return tx

    def _get_status_message(self, *, order=None, **kwargs):
        """Override of `payment` to add custom messages for website orders.

        :param sale.order order: The current cart linked to the transaction.
        """
        is_website_order = order and order.website_id
        if is_website_order and self.state == "done" and order.amount_total != self.amount:
            return Markup("<p>%s</p>") % self.env._(
                "Unfortunately your order can not be confirmed as the amount of your payment"
                " does not match the amount of your cart. Please contact the responsible of"
                " the shop for more information."
            )
        if is_website_order and self.state == "pending":
            provider_sudo = self.provider_id.sudo()
            if (
                provider_sudo.code == "custom"
                and provider_sudo.custom_mode in provider_sudo._get_custom_bank_related_modes()
            ):
                return Markup("<p>%s</p>") % self.env._(
                    "Your order will be confirmed after payment is received."
                )
        return super()._get_status_message(order=order, **kwargs)
