# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging

from odoo import fields, models

from odoo.addons.payment_nuvei import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('nuvei', "Nuvei")], ondelete={'nuvei': 'set default'}
    )
    nuvei_merchant_identifier = fields.Char(
        string="Nuvei Merchant Identifier",
        help="The code of the merchant account to use with this provider.",
        required_if_provider='nuvei',
    )
    nuvei_site_identifier = fields.Char(
        string="Nuvei Site Identifier",
        help="The site identifier code associated with the merchant account.",
        required_if_provider='nuvei',
        groups='base.group_system',
    )
    nuvei_secret_key = fields.Char(
        string="Nuvei Secret Key",
        required_if_provider='nuvei',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _nuvei_get_api_url(self):
        if self.state == 'enabled':
            return 'https://secure.safecharge.com/ppp/purchase.do'
        else:  # 'test'
            return 'https://ppp-test.safecharge.com/ppp/purchase.do'

    def _nuvei_calculate_signature(self, data, incoming=True):
        """ Compute the signature for the provided data according to the Nuvei documentation.

        :param dict data: The data to sign.
        :param bool incoming: If the signature must be generated for an incoming (Nuvei to Odoo) or
                              outgoing (Odoo to Nuvei) communication.
        :return: The calculated signature.
        :rtype: str
        """
        self.ensure_one()
        signature_keys = const.SIGNATURE_KEYS if incoming else data.keys()
        sign_data = ''.join([str(data.get(k, '')) for k in signature_keys])
        key = self.nuvei_secret_key
        signing_string = f'{key}{sign_data}'
        return hashlib.sha256(signing_string.encode()).hexdigest()

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'nuvei':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'nuvei':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
