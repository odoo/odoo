# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    def _get_available_tokens(self, *args, is_express_checkout=False, **kwargs):
        """ Override of `payment` not to return the tokens in case of express checkout.

        :param dict args: Locally unused arguments.
        :param bool is_express_checkout: Whether the payment is made through express checkout.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The available tokens.
        :rtype: payment.token
        """
        if is_express_checkout:
            return self.env['payment.token']

        return super()._get_available_tokens(*args, **kwargs)
