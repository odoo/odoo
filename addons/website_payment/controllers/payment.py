# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.account_payment.controllers import payment as account_payment


class PaymentPortal(account_payment.PaymentPortal):

    @route()
    def payment_pay(self, *args, **kwargs):
        """Override of `payment` to make the provider filtering website-aware."""
        website = request.env['website'].get_current_website()
        return super().payment_pay(*args, website_id=website.id, **kwargs)

    @route()
    def payment_method(self, **kwargs):
        """Override of `payment` to make the provider filtering website-aware."""
        website = request.env['website'].get_current_website()
        return super().payment_method(website_id=website.id, **kwargs)
