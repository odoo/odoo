# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import logging
import pprint
from wsgiref.handlers import format_date_time

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Datetime

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

    @api.model
    def _setup_provider(self, code):
        """Override of `payment` to migrate Ogone data including tokens to Worldline."""
        super()._setup_provider(code)
        if code != 'worldline':
            return

        ogone_providers = self.env['payment.provider'].search(
            [('code', '=', 'ogone'), ('state', '!=', 'disabled')]
        )
        if not ogone_providers:
            return

        default_worldline_provider = self.env.ref(
            'payment_worldline.payment_provider_worldline', raise_if_not_found=False
        )
        if not default_worldline_provider:
            return

        # Migrate data from each Ogone provider to Worldline.
        for ogone_provider in ogone_providers:
            company = ogone_provider.company_id

            # Create a new Worldline provider for every Ogone provider in the same company.
            worldline_provider = default_worldline_provider.copy({'company_id': company.id})

            # Copy the credentials from Ogone to Worldline.
            worldline_provider.write({
                'name': _(
                    "Worldline (migrated from %(ogone_provider_name)s)",
                    ogone_provider_name=ogone_provider.name,
                ),
                'allow_tokenization': ogone_provider.allow_tokenization,
                'maximum_amount': ogone_provider.maximum_amount,
                'available_country_ids': ogone_provider.available_country_ids.ids,
                'worldline_pspid': ogone_provider.ogone_pspid,
                'worldline_api_key': ogone_provider.ogone_userid,
                'worldline_api_secret': ogone_provider.ogone_password,
            })

            # Transfer tokens from Ogone to Worldline.
            tokens = self.env['payment.token'].search([('provider_id', '=', ogone_provider.id)])
            if tokens:
                tokens.provider_id = worldline_provider.id
                _logger.info(
                    "Transferred %d token(s) from Ogone provider %s to Worldline provider %s",
                    len(tokens), ogone_provider.name, worldline_provider.name
                )

        ogone_providers.with_context(skip_token_archival=True).state = 'disabled'

        # Remove the Ogone account payment method.
        account_payment_method = self.env.get('account.payment.method')
        if account_payment_method:
            account_payment_method.search([('code', '=', 'ogone')]).unlink()

    def _worldline_make_request(self, endpoint, payload=None, method='POST', idempotency_key=None):
        """ Make a request to Worldline API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :param str idempotency_key: The idempotency key to pass in the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        api_url = self._worldline_get_api_url()
        url = f'{api_url}/v2/{self.worldline_pspid}/{endpoint}'
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
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=10)
            try:
                if response.status_code not in const.VALID_RESPONSE_CODES:
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
