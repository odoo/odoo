# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.payment.controllers import portal


class PaymentPaypalPortal(portal.PaymentPortal):
    def _prepare_payment_form_values(self, *args, **kwargs):
        """Override of `payment` to forward the customer's user agent to PayPal.

        PayPal's `find-eligible-methods` endpoint derives the customer's browser, OS, and device
        type from the `User-Agent` header to refine the eligibility of its payment methods. The raw
        user agent string is forwarded so that PayPal parses it, rather than parsing it locally.
        """
        if request:
            kwargs.setdefault("paypal_customer_user_agent", request.httprequest.user_agent.string)
        return super()._prepare_payment_form_values(*args, **kwargs)
