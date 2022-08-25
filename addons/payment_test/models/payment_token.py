# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    test_simulated_state = fields.Selection(
        string="Simulated State",
        help="The state in which transactions created from this token should be set.",
        selection=[
            ('pending', "Pending"),
            ('done', "Confirmed"),
            ('cancel', "Canceled"),
            ('error', "Error"),
        ],
    )

    def _build_display_name(self, *args, should_pad=True, **kwargs):
        """ Override of `payment` to build the display name without padding.

        Note: self.ensure_one()

        :param list args: The arguments passed by QWeb when calling this method.
        :param bool should_pad: Whether the token should be padded or not.
        :param dict kwargs: Optional data.
        :return: The test token name.
        :rtype: str
        """
        if self.provider != 'test':
            return super()._build_display_name(*args, should_pad=should_pad, **kwargs)
        return super()._build_display_name(*args, should_pad=False, **kwargs)
