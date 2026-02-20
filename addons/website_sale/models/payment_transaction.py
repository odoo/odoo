# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        """Override of `sale` to archive guest contacts."""
        confirmed_orders = super()._check_amount_and_confirm_order()
        confirmed_orders.filtered('website_id')._archive_partner_if_no_user()
        return confirmed_orders

    def _process(self, provider_code, payment_data):
        """Override of `payment` to allow retrying if transaction is canceled or has an error, by
        redirecting to payment page."""
        tx = super()._process(provider_code, payment_data)
        if tx.sale_order_ids.website_id and tx.state in ["cancel", "error"]:
            tx.landing_route = "/shop/payment"
        return tx

    def _get_transaction_status_message(self, **kwargs):
        """Override of `payment` to add a custom message when cart amount is different after payment
        in `website_sale`.
        :param sale.order order: The current cart linked to the transaction.
        """
        status_message = super()._get_transaction_status_message(**kwargs)
        order = kwargs.get('order')
        if (
            order and
            order.website_id and
            self.state == 'done' and
            order.amount_total != self.amount
        ):
            return Markup(f'''<p>{
                _("Unfortunately your order can not be confirmed as the amount of your payment does"
                " not match the amount of your cart. Please contact the responsible of the shop for"
                " more information."
                )}
            ''')
        return status_message
