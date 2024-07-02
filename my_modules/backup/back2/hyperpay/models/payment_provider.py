# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import pprint

import requests
from werkzeug.urls import url_join

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.hyperpay import const

try:
    from urllib.parse import urlencode
    from urllib.request import build_opener, Request, HTTPHandler
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib import urlencode
    from urllib2 import build_opener, Request, HTTPHandler, HTTPError, URLError
import json

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('hyperpay', "Hyperpay")], ondelete={'hyperpay': 'set default'}
    )
    hyperpay_key_id = fields.Char(
        string="Hyperpay Entity Id",
        help="The key solely used to identify the account with Hyperpay.",
        required_if_provider='hyperpay',
    )
    hyperpay_key_secret = fields.Char(
        string="Hyperpay Key Secret",
        required_if_provider='hyperpay',
        groups='base.group_system',
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'hyperpay').update({
            'support_manual_capture': 'full_only',
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    # === BUSINESS METHODS ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'hyperpay':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _hyperpay_make_request(self, payload=None, method='POST'):
        """ Make a request to Hyperpay API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        auth = self.hyperpay_key_secret
        url = 'https://eu-test.oppwa.com/v1/checkouts'
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, auth=auth, timeout=10)
            else:
                response = requests.post(url, data=payload, headers={
                    'Authorization': 'Bearer OGE4Mjk0MTc0YjdlY2IyODAxNGI5Njk5MjIwMDE1Y2N8c3k2S0pzVDg='}, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                )
                raise ValidationError("Razorpay: " + _(
                    "Hyperpay gave us the following information: '%s'",
                    response.json().get('error', {}).get('description')
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Hyperpay: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _hyperpay_get_status(self, orderid=None):
        self.ensure_one()
        url = "https://eu-test.oppwa.com/v1/checkouts/"
        url += orderid
        url += '/payment?entityId=8a8294174b7ecb28014b9699220015ca'
        try:
            response = requests.get(url, headers={
                        'Authorization': 'Bearer OGE4Mjk0MTc0YjdlY2IyODAxNGI5Njk5MjIwMDE1Y2N8c3k2S0pzVDg='}, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(url),
                )
                raise ValidationError("Hyperpay: " + _(
                    "Hyperpay gave us the following information: '%s'",
                    response.json().get('error', {}).get('description')
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Hyperpay: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _get_redirect_form_view(self, is_validation=False):
        """ Return the view of the template used to render the redirect form.

        For a provider to return a different view depending on whether the operation is a
        validation, it must override this method and return the appropriate view.

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        return self.redirect_form_view_id

    def _hyperpay_calculate_signature(self, data, is_redirect=True):
        """ Compute the signature for the request's data according to the Hyperpay documentation.

        See https://hyperpay.com/docs/webhooks/validate-test#validate-webhooks and
        https://hyperpay.com/docs/payments/payment-gateway/web-integration/hosted/build-integration.

        :param dict|bytes data: The data to sign.
        :param bool is_redirect: Whether the data should be treated as redirect data or as coming
                                 from a webhook notification.
        :return: The calculated signature.
        :rtype: str
        """
        if is_redirect:
            secret = self.hyperpay_key_secret
            signing_string = f'{data["hyperpay_order_id"]}|{data["hyperpay_payment_id"]}'
            return hmac.new(
                secret.encode(), msg=signing_string.encode(), digestmod=hashlib.sha256
            ).hexdigest()
        else:  # Notification data.

            return hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256).hexdigest()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'hyperpay':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _get_validation_amount(self):
        """ Override of `payment` to return the amount for Hyperpay validation operations.

        :return: The validation amount.
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'hyperpay':
            return res

        return 1.0
