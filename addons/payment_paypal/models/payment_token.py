# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentToken(models.Model):
    _inherit = "payment.token"

    paypal_customer_id = fields.Char(string="PayPal Customer ID", readonly=True)

    # === COMPUTE METHODS === #

    @api.depends("payment_details", "create_date")
    def _build_display_name(self, *args, should_pad=True, **kwargs):
        """Override of `payment` to only pad the display name of card tokens.

        The payment details of PayPal wallet tokens are not card digits, so they must not be padded.
        """
        if self.provider_code != "paypal" or self.payment_method_code == "card":
            return super()._build_display_name(*args, should_pad=should_pad, **kwargs)
        return super()._build_display_name(*args, should_pad=False, **kwargs)
