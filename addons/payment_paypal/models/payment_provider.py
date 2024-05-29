# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from odoo import _, fields, models

from odoo.addons.payment_paypal import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paypal', "Paypal")], ondelete={'paypal': 'set default'}
    )
    paypal_email_account = fields.Char(
        string="Email",
        help="The public business email solely used to identify the account with PayPal",
        required_if_provider='paypal',
        default=lambda self: self.env.company.email,
    )
    paypal_pdt_token = fields.Char(string="PDT Identity Token", groups='base.group_system')
    paypal_client_id = fields.Char(
        string="Client ID",
        help="Client ID found on the paypal dashboard",
        required_if_provider='paypal',
    )
    paypal_client_secret = fields.Char(
        string="Client Secret",
        help="Client ID found on the paypal dashboard",
        groups='base.group_system'
    )

    #=== BUSINESS METHODS ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'paypal':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _paypal_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://www.paypal.com/cgi-bin/webscr'
        else:
            return 'https://www.sandbox.paypal.com/cgi-bin/webscr'

    def _paypal_get_api_url_v2(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://api-m.sandbox.paypal.com'
        else:
            return 'https://api-m.paypal.com'

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paypal':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_access_token(self):
        response = requests.post(
            self._paypal_get_api_url_v2() + '/v1/oauth2/token',
            data={'grant_type': 'client_credentials'},
            headers={'Content-type': 'application/json'},
            auth=(self.paypal_client_id, self.paypal_client_secret)
        )
        if response.status_code == 200:
            return response.json()['access_token']
        return False
