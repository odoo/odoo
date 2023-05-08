# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import md5

from odoo import fields, models
from odoo.tools.float_utils import float_repr, float_split

from odoo.addons.payment_payulatam.const import SUPPORTED_CURRENCIES

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payulatam', 'PayU Latam')], ondelete={'payulatam': 'set default'})
    payulatam_merchant_id = fields.Char(
        string="PayU Latam Merchant ID",
        help="The ID solely used to identify the account with PayULatam",
        required_if_provider='payulatam')
    payulatam_account_id = fields.Char(
        string="PayU Latam Account ID",
        help="The ID solely used to identify the country-dependent shop with PayULatam",
        required_if_provider='payulatam')
    payulatam_api_key = fields.Char(
        string="PayU Latam API Key", required_if_provider='payulatam',
        groups='base.group_system')

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'payulatam':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _payulatam_generate_sign(self, values, incoming=True):
        """ Generate the signature for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (PayU Latam to
                              Odoo) or outgoing (Odoo to PayU Latam) communication.
        :return: The signature
        :rtype: str
        """
        if incoming:
            # "Confirmation" and "Response" pages have a different way to calculate what they call the `new_value`
            if self.env.context.get('payulatam_is_confirmation_page'):
                # https://developers.payulatam.com/latam/en/docs/integrations/webcheckout-integration/confirmation-page.html#signature-validation
                # For confirmation page, PayU Latam round to the first digit if the second one is a zero
                # to generate their signature.
                # e.g:
                #  150.00 -> 150.0
                #  150.26 -> 150.26
                # This happens to be Python 3's default behavior when casting to `float`.
                new_value = "%d.%d" % float_split(float(values.get('TX_VALUE')), 2)
            else:
                # https://developers.payulatam.com/latam/en/docs/integrations/webcheckout-integration/response-page.html#signature-validation
                # PayU Latam use the "Round half to even" rounding method
                # to generate their signature. This happens to be Python 3's
                # default rounding method.
                new_value = float_repr(float(values.get('TX_VALUE')), 1)
            data_string = '~'.join([
                self.payulatam_api_key,
                self.payulatam_merchant_id,
                values['referenceCode'],
                new_value,
                values['currency'],
                values.get('transactionState'),
            ])
        else:
            data_string = '~'.join([
                self.payulatam_api_key,
                self.payulatam_merchant_id,
                values['referenceCode'],
                float_repr(float(values['amount']), 2),
                values['currency'],
                values['paymentMethods'],
            ])
        return md5(data_string.encode('utf-8')).hexdigest()
