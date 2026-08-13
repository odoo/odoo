# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests

from datetime import timedelta
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal.controllers.main import PaypalController


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paypal', "PayPal")], ondelete={'paypal': 'set default'}
    )
    paypal_email_account = fields.Char(
        string="Email",
        help="The public business email solely used to identify the account with PayPal",
        required_if_provider='paypal',
        default=lambda self: self.env.company.email,
    )
    paypal_client_id = fields.Char(string="PayPal Client ID", required_if_provider='paypal')
    paypal_client_secret = fields.Char(string="PayPal Client Secret", groups='base.group_system')
    paypal_access_token = fields.Char(
        string="PayPal Access Token",
        help="The short-lived token used to access Paypal APIs",
        groups='base.group_system',
    )
    paypal_access_token_expiry = fields.Datetime(
        string="PayPal Access Token Expiry",
        help="The moment at which the access token becomes invalid.",
        default='1970-01-01',
        groups='base.group_system',
    )
    paypal_webhook_id = fields.Char(string="PayPal Webhook ID")

    # === ACTION METHODS === #

    def action_paypal_create_webhook(self):
        """ Create a new webhook.

        Note: This action only works for instances using a public URL.

        :return: None
        :raise UserError: If the base URL is not in HTTPS.
        """
        base_url = self.get_base_url()
        if 'localhost' in base_url:
            raise UserError(
                "PayPal: " + _("You must have an HTTPS connection to generate a webhook.")
            )
        data = {
            'url': urls.url_join(base_url, PaypalController._webhook_url),
            'event_types': [{'name': event_type} for event_type in const.HANDLED_WEBHOOK_EVENTS]
        }
        webhook_data = self._paypal_make_request('/v1/notifications/webhooks', json_payload=data)
        self.paypal_webhook_id = webhook_data.get('id')

    #=== BUSINESS METHODS ===#

    def _paypal_make_request(
        self, endpoint, data=None, json_payload=None, auth=None, is_refresh_token_request=False,
        idempotency_key=None,
    ):
        """ Make a request to Paypal API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict data: The string payload of the request.
        :param dict json_payload: The JSON-formatted payload of the request.
        :param tuple auth: The authentication data.
        :param bool is_refresh_token_request: Whether the request is for refreshing the access
                                              token.
        :param str idempotency_key: The idempotency key to pass in the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        url = self._paypal_get_api_url() + endpoint
        headers = {
            'Content-Type': 'application/json',  # PayPal always wants JSON content-type.
            # PayPal requires a reference specific to Odoo to be able to track Odoo customers.
            'PayPal-Partner-Attribution-Id': 'OdooInc_SP_EC',
        }
        if idempotency_key:
            headers['PayPal-Request-Id'] = idempotency_key
        if not is_refresh_token_request:
            headers['Authorization'] = f'Bearer {self._paypal_fetch_access_token()}'
        try:
            response = requests.post(
                url, headers=headers, data=data, json=json_payload, auth=auth, timeout=10
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                payload = data or json_payload
                # PayPal errors https://developer.paypal.com/api/rest/reference/orders/v2/errors/
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
                )
                msg = response.json().get('message', '')
                raise ValidationError(
                    "PayPal: " + _("The communication with the API failed. Details: %s", msg)
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError("PayPal: " + _("Could not establish the connection to the API."))
        return response.json()

    def _paypal_fetch_access_token(self):
        """ Generate a new access token if it's expired, otherwise return the existing access token.

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        if fields.Datetime.now() > self.paypal_access_token_expiry - timedelta(minutes=5):
            response_content = self._paypal_make_request(
                '/v1/oauth2/token',
                data={'grant_type': 'client_credentials'},
                auth=(self.paypal_client_id, self.paypal_client_secret),
                is_refresh_token_request=True,
            )
            access_token = response_content['access_token']
            if not access_token:
                raise ValidationError("PayPal: " + _("Could not generate a new access token."))
            self.write({
                'paypal_access_token': access_token,
                'paypal_access_token_expiry': fields.Datetime.now() + timedelta(
                    seconds=response_content['expires_in']
                ),
            })
        return self.paypal_access_token

    # === BUSINESS METHODS - GETTERS === #

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
            return 'https://api-m.paypal.com'
        else:
            return 'https://api-m.sandbox.paypal.com'

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paypal':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _paypal_get_inline_form_values(self, currency=None):
        """ Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param res.currency currency: The transaction currency.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        inline_form_values = {
            'provider_id': self.id,
            'client_id': self.paypal_client_id,
            'currency_code': currency and currency.name,
        }
        return json.dumps(inline_form_values)
