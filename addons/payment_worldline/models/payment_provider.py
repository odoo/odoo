# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import hashlib
import hmac
import logging
import pprint

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_worldline import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('worldline', "Worldline")], ondelete={'worldline': 'set default'}
    )
    worldline_pspid = fields.Char(string="Worldline PSPID", required_if_provider='worldline')
    worldline_api_key = fields.Char(string="Worldline API Key", required_if_provider='worldline')
    worldline_api_secret = fields.Char(
        string="Worldline API Secret", required_if_provider='worldline'
    )
    worldline_webhook_key = fields.Char(
        string="Worldline Webhook Key", required_if_provider='worldline'
    )
    worldline_webhook_secret = fields.Char(
        string="Worldline Webhook Secret", required_if_provider='worldline'
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'worldline').update({
            'support_tokenization': True,
        })

    # === BUSINESS METHODS === #

    def _worldline_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Worldline API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        api_url = self._worldline_get_api_url()
        url = f'{api_url}/v2/{self.worldline_pspid}/{endpoint}'
        content_type = 'application/json; charset=utf-8' if method == 'POST' else ''
        tz = datetime.timezone(datetime.timedelta(hours=0), 'GMT')
        dt = datetime.datetime.now(tz).strftime('%a, %d %b %Y %H:%M:%S %Z')  # Datetime in RFC1123.
        signature = self._worldline_calculate_signature(method, endpoint, content_type, dt)
        authorization_header = f'GCS v1HMAC:{self.worldline_api_key}:{signature}'
        headers = {
            'Authorization': authorization_header,
            'Date': dt,
            'Content-Type': content_type,
        }
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
                )
                msg = ', '.join(
                    [error.get('message', '') for error in response.json().get('errors', [])]
                )
                raise ValidationError(
                    "Worldline: " + _("The communication with the API failed. Details: %s", msg)
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Worldline: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _worldline_get_api_url(self):
        """ Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        if self.state == 'enabled':
            return 'https://payment.direct.worldline-solutions.com'
        else:  # 'test'
            return 'https://payment.preprod.direct.worldline-solutions.com'

    def _worldline_calculate_signature(self, method, endpoint, content_type, dt_rfc):
        """ Compute the signature for the provided data.

        See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/authentication.

        :param str method: The HTTP method of the request
        :param str endpoint: The endpoint to be reached by the request.
        :param str content_type: The 'Content-Type' header of the request.
        :param datetime.datetime dt_rfc: The timestamp of the request, in RFC1123 format.
        :return: The calculated signature.
        :rtype: str
        """
        values_to_sign = [method, content_type, dt_rfc, f'/v2/{self.worldline_pspid}/{endpoint}']
        signing_str = '\n'.join(values_to_sign) + '\n'
        signature = hmac.new(
            self.worldline_api_secret.encode(), signing_str.encode(), hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'worldline':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
