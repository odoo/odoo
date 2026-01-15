# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
from wsgiref.handlers import format_date_time

from odoo import fields, models
from odoo.fields import Datetime

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_worldline import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('worldline', "Worldline")], ondelete={'worldline': 'set default'}
    )
    worldline_pspid = fields.Char(
        string="Worldline PSPID",
        required_if_provider='worldline',
        copy=False,
    )
    worldline_api_key = fields.Char(
        string="Worldline API Key",
        required_if_provider='worldline',
        copy=False,
    )
    worldline_api_secret = fields.Char(
        string="Worldline API Secret",
        required_if_provider='worldline',
        copy=False,
    )
    worldline_webhook_key = fields.Char(
        string="Worldline Webhook Key",
        required_if_provider='worldline',
        copy=False,
    )
    worldline_webhook_secret = fields.Char(
        string="Worldline Webhook Secret",
        required_if_provider='worldline',
        copy=False,
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'worldline').update({
            'support_tokenization': True,
        })

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'worldline':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'worldline':
            return super()._build_request_url(endpoint, **kwargs)
        api_url = self._worldline_get_api_url()
        return f'{api_url}/v2/{self.worldline_pspid}/{endpoint}'

    def _worldline_get_api_url(self):
        """ Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        if self.state == 'enabled':
            return 'https://payment.direct.worldline-solutions.com'
        else:  # 'test'
            return 'https://payment.preprod.direct.worldline-solutions.com'

    def _build_request_headers(self, method, endpoint, *args, idempotency_key=None, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'worldline':
            return super()._build_request_headers(
               method, endpoint, *args, idempotency_key=idempotency_key, **kwargs
            )

        content_type = 'application/json; charset=utf-8' if method == 'POST' else ''
        dt = format_date_time(Datetime.now().timestamp())  # Datetime in locale-independent RFC1123
        signature = self._worldline_calculate_signature(
            method, endpoint, content_type, dt, idempotency_key=idempotency_key
        )
        authorization_header = f'GCS v1HMAC:{self.worldline_api_key}:{signature}'
        headers = {
            'Authorization': authorization_header,
            'Date': dt,
            'Content-Type': content_type,
        }
        if method == 'POST' and idempotency_key:
            headers['X-GCS-Idempotence-Key'] = idempotency_key
        return headers

    def _worldline_calculate_signature(
        self, method, endpoint, content_type, dt_rfc, idempotency_key=None
    ):
        """ Compute the signature for the provided data.

        See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/authentication.

        :param str method: The HTTP method of the request
        :param str endpoint: The endpoint to be reached by the request.
        :param str content_type: The 'Content-Type' header of the request.
        :param datetime.datetime dt_rfc: The timestamp of the request, in RFC1123 format.
        :param str idempotency_key: The idempotency key to pass in the request.
        :return: The calculated signature.
        :rtype: str
        """
        # specific order required: method, content_type, date, custom headers, endpoint
        values_to_sign = [method, content_type, dt_rfc]
        if idempotency_key:
            values_to_sign.append(f'x-gcs-idempotence-key:{idempotency_key}')
        values_to_sign.append(f'/v2/{self.worldline_pspid}/{endpoint}')

        signing_str = '\n'.join(values_to_sign) + '\n'
        signature = hmac.new(
            self.worldline_api_secret.encode(), signing_str.encode(), hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message."""
        if self.code != 'worldline':
            return super()._parse_response_error(response)
        msg = ', '.join([error.get('message', '') for error in response.json().get('errors', [])])
        return msg
