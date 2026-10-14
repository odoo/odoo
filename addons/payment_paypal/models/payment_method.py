# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from urllib.parse import urlparse

from odoo import models
from odoo.exceptions import UserError


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    def action_paypal_verify_apple_pay_domain(self):
        """Register the web domain with PayPal to enable Apple Pay.

        PayPal verifies the domain by making a request to the
        `/.well-known/apple-developer-merchantid-domain-association` route. If the domain is valid,
        it is registered to use with Apple Pay.
        See https://developer.paypal.com/docs/checkout/apm/apple-pay/#register-your-live-domain.

        :return: A client action with a success message.
        :rtype: dict
        """
        self.ensure_one()

        provider = self.provider_id
        base_domain = urlparse(provider.get_base_url()).netloc
        try:
            provider._send_api_request(
                "POST",
                "/v1/customer/wallet-domains",
                json={"provider_type": "APPLE_PAY", "domain": {"name": base_domain}},
                idempotency_key=uuid.uuid4().hex,
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": self.env._("Your domain was successfully registered."),
                    "type": "success",
                },
            }
        except UserError as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "title": self.env._("Could not register your domain"),
                    "message": str(e),
                    "sticky": True,
                },
            }
