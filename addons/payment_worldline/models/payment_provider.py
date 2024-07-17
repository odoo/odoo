# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import hashlib
import hmac
import logging

import requests
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_worldline import const
from odoo.addons.payment_worldline.controllers.main import WorldlineController


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('worldline', "Worldline")], ondelete={'worldline': 'set default'})
    worldline_psp_id = fields.Char(
        string="Worldline Payment Provider ID",
        help="The name you choose when registering to Worldline",
        required_if_provider='worldline',
    )
    worldline_api_key = fields.Char(
        string="Worldline API Key",
        help="The API key of the webservice user",
        required_if_provider='worldline',
    )
    worldline_api_secret = fields.Char(
        string="Worldline API Secret",
        help="The API secret of the webservice user",
        required_if_provider='worldline',
    )
    worldline_webhook_key = fields.Char(
        string="Worldline Webhook Key",
        help="The API key of the webservice user",
        required_if_provider='worldline',
    )
    worldline_webhook_secret = fields.Char(
        string="Worldline Webhook Secret",
        help="The API secret of the webservice user",
        required_if_provider='worldline',
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

        :param str endpoint: The endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        api_url = self._worldline_get_api_url()
        url = api_url + endpoint
        content_type = 'application/json; charset=utf-8' if method == 'POST' else ''
        tz = datetime.timezone(datetime.timedelta(hours=0), 'GMT')
        dt = datetime.datetime.now(tz).strftime("%a, %d %b %Y %H:%M:%S %Z")  # Datetime in RFC1123
        signature = self._worldline_calculate_signature(method, endpoint, content_type, dt)
        authorization_header = 'GCS v1HMAC:' + self.worldline_api_key + ':' + signature
        headers = {
            'Authorization': authorization_header,
            'Date': dt,
            'Content-Type': content_type,
        }

        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "invalid API request at %s with data %s: %s", url, payload, response.text
                )
                msg = ', '.join(
                    [error.get('message', '') for error in response.json().get('errors', [])]
                )
                raise ValidationError(
                    "Worldline: " + _("The communication with the API failed. Details: %s", msg)
                )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError(
                "Worldline: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _worldline_get_api_url(self):
        if self.state == 'enabled':
            return 'https://payment.direct.worldline-solutions.com'
        else:  # 'test'
            return 'https://payment.preprod.direct.worldline-solutions.com'

    def _worldline_calculate_signature(self, method, endpoint, content_type, dt_rfc):
        # https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/authentication
        values_to_sign = [method, content_type, dt_rfc]
        values_to_sign.append(endpoint)
        signing_str = '\n'.join(values_to_sign) + '\n'
        signature = hmac.new(
            self.worldline_api_secret.encode(), signing_str.encode(), hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode("utf-8")

    def _worldline_create_hosted_checkout_session(self, transaction, converted_amount):
        self.ensure_one()
        transaction.ensure_one()

        # Flow overview: https://docs.direct.worldline-solutions.com/en/integration/basic-integration-methods/hosted-checkout-page
        # https://docs.direct.worldline-solutions.com/en/api-reference#tag/HostedCheckout
        endpoint = '/v2/' + self.worldline_psp_id + '/hostedcheckouts'
        return_url = urls.url_join(self.get_base_url(), WorldlineController._return_url)
        return_url_params = urls.url_encode({'provider': str(self.id)})

        # see: https://apireference.connect.worldline-solutions.com/s2sapi/v1/en_US/go/hostedcheckouts/create.html?paymentPlatform=ALL
        body = {
            'hostedCheckoutSpecificInput': {
                'locale': transaction.partner_id.lang or transaction.company_id.lang,
                'returnUrl': f'{return_url}?{return_url_params}',
            },
            'order': {
                'additionalInput': {},
                'amountOfMoney': {
                    'currencyCode': transaction.currency_id.name,
                    'amount': converted_amount,
                },
                'customer': {  # required to create a token and for some redirected payment methods
                    'billingAddress': {
                        'countryCode': transaction.partner_id.country_id.code,
                    },
                    'contactDetails': {
                        'emailAddress': transaction.partner_id.email,
                        'phoneNumber': transaction.partner_id.phone,
                    },
                },
                'references': {
                    'descriptor': transaction.reference,
                    'merchantReference': transaction.reference,
                },
            },
        }

        payment_method = transaction.payment_method_id
        if payment_method.code in const.REDIRECT_PAYMENT_METHODS:
            body['redirectPaymentMethodSpecificInput'] = {
                'requiresApproval': False,  # Force the capture
                'PaymentProductId': const.PAYMENT_METHODS_MAPPING[payment_method.code],
                'redirectionData': {
                    'returnUrl': f'{return_url}?{return_url_params}',
                },
            }
        else:
            body['cardPaymentMethodSpecificInput'] = {
                'authorizationMode': 'SALE',  # Force the capture
                'tokenize': transaction.tokenize,
            }
            if not payment_method.brand_ids and payment_method.code != 'card':
                worldline_code = const.PAYMENT_METHODS_MAPPING.get(payment_method.code, 0)
                body['cardPaymentMethodSpecificInput']['paymentProductId'] = worldline_code
            else:
                pm_codes = self.env['payment.method'].search([
                    ('active', 'in', [True, False]),
                    ('primary_payment_method_id', '=', payment_method.id),
                ]).mapped('code')
                worldline_codes = [
                    const.PAYMENT_METHODS_MAPPING[code] for code in pm_codes
                    if code in const.PAYMENT_METHODS_MAPPING
                ]
                body['hostedCheckoutSpecificInput']['paymentProductFilters'] = {
                    'restrictTo': {
                        'products': worldline_codes,
                    },
                }

        return self._worldline_make_request(endpoint, body)

    def _worldline_fetch_session_info(self, data):
        self.ensure_one()

        hosted_checkout_id = data['hostedCheckoutId']
        endpoint = '/v2/' + self.worldline_psp_id + '/hostedcheckouts/' + hosted_checkout_id

        return self._worldline_make_request(endpoint, method='GET')

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'worldline':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
