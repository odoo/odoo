# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    sdd_mandate_id = fields.Many2one(
        string="SEPA Direct Debit Mandate", comodel_name='sdd.mandate', readonly=True,
        ondelete='set null')

    def _build_display_name(self, *args, max_length=34, should_pad=True, **kwargs):
        """ Override of `payment` to return the full bank account number for SEPA Direct Debit.

        Note: self.ensure_one()

        :param list args: The arguments passed by QWeb when calling this method.
        :param int max_length: The desired maximum length of the token name.
        :param bool should_pad: Whether the token should be padded or not.
        :param dict kwargs: Optional data.
        :return: The IBAN of the token.
        :rtype: str
        """
        payment_details = super()._build_display_name(
            *args, max_length=max_length, should_pad=should_pad, **kwargs
        )
        if self.provider_id.custom_mode != 'sepa_direct_debit':
            return payment_details

        if len(self.payment_details) <= max_length:
            return super()._build_display_name(
                *args, max_length=max_length, should_pad=False, **kwargs
            )
        else:  # Not enough room for the full IBAN.
            return f"{self.payment_details[:2]}*{self.payment_details[-4:]}"
