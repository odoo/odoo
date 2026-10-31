from odoo import models


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    def action_paypal_enable_apple_pay(self):
        """Redirect user to documentation to manually register the domain on PayPal.
        TODO When possible register the web domain with PayPal apis to enable Apple Pay directly
        through a request.

        :return: A client action with a redirection url.
        :rtype: dict
        """
        return {
            "type": "ir.actions.act_url",
            "url": "https://www.odoo.com/documentation/latest/applications/finance/payment_providers/paypal.html#configuration-in-odoo",
            "target": "new",
        }
