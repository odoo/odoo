# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from odoo import fields, models

from odoo.addons.payment_payulatam.const import DEFAULT_PAYMENT_METHODS_CODES


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payumoney', "PayUmoney")], ondelete={'payumoney': 'set default'})
    payumoney_merchant_key = fields.Char(
        string="Merchant Key", help="The key solely used to identify the account with PayU money",
        required_if_provider='payumoney')
    payumoney_merchant_salt = fields.Char(
        string="Merchant Salt", required_if_provider='payumoney', groups='base.group_system')

    def _get_supported_currencies(self):
        """ Override of `payment` to return INR as the only supported currency. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'payumoney':
            supported_currencies = supported_currencies.filtered(lambda c: c.name == 'INR')
        return supported_currencies

    def _payumoney_generate_sign(self, values, incoming=True):
        """ Generate the shasign for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (PayUmoney to
                              Odoo) or outgoing (Odoo to PayUMoney) communication.
        :return: The shasign
        :rtype: str
        """
        sign_values = {
            **values,
            'key': self.payumoney_merchant_key,
            'salt': self.payumoney_merchant_salt,
        }
        if incoming:
            keys = 'salt|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|' \
                   'txnid|key'
            sign = '|'.join(f'{sign_values.get(k) or ""}' for k in keys.split('|'))
        else:  # outgoing
            keys = 'key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt'
            sign = '|'.join(f'{sign_values.get(k) or ""}' for k in keys.split('|'))
        return hashlib.sha512(sign.encode('utf-8')).hexdigest()

    #=== BUSINESS METHODS ===#

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'payumoney':
            return default_codes
        return DEFAULT_PAYMENT_METHODS_CODES
