# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.account_payment.controllers import payment as account_payment
from odoo.http import request, route


class PaymentPortal(account_payment.PaymentPortal):
    @route()
    def payment_pay(self, *args, **kwargs):
        kwargs.update({
            "website_id": request.website.id,
        })
        return super().payment_pay(*args, **kwargs)

    @route()
    def payment_method(self, **kwargs):
        kwargs.update({
            "website_id": request.website.id,
        })
        return super().payment_method(**kwargs)
