# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
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
    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'paypal').update({
            'support_manual_capture': 'full_only',
            'support_tokenization': True,
        })

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
            return 'https://api-m.paypal.com'
        else:
            return 'https://api-m.sandbox.paypal.com'

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paypal':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _paypal_get_inline_form_values(self, amount=None, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param str pm_code: The code of the payment method whose inline form to render.
        :param float amount: The transaction amount.
        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        inline_form_values = {
            'client_id': self.paypal_client_id,
            'amount': amount,
            'currency': currency and currency.name,
            'intent': "CAPTURE",
        }
        return json.dumps(inline_form_values)

    def _paypal_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Paypal API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the provider reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        url = self._paypal_get_api_url_v2() + endpoint
        if not (access_token := self._get_access_token()):
            raise ValidationError("Paypal: " + _("Can't get access token"))

        headers = {
            'Content-type': 'application/json',
            'Authorization': 'Bearer %s' % (access_token),
        }
        try:
            response = requests.request(
                method, url, json=payload,
                headers=headers, timeout=60)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "invalid API request at %s with data %s: %s", url, payload, response.text
                )
                msg = response.json().get('message', '')
                raise ValidationError(
                    "Paypal: " + _("The communication with the API failed. Details: %s", msg)
                )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Paypal: " + _("Could not establish the connection to the API."))
        return response.json()['id']

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
