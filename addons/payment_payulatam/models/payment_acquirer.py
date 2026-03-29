# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import md5

from odoo import api, fields, models
from odoo.tools.float_utils import float_split, float_repr

SUPPORTED_CURRENCIES = ('ARS', 'BRL', 'CLP', 'COP', 'MXN', 'PEN', 'USD')


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
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

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist PayU Latam acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda a: a.provider != 'payulatam')

        return acquirers

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
            ])
        return md5(data_string.encode('utf-8')).hexdigest()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'payulatam':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_payulatam.payment_method_payulatam').id
