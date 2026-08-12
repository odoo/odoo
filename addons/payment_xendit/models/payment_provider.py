# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_xendit import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('xendit', "Xendit")], ondelete={'xendit': 'set default'}
    )
    # Kept for backward compatibility with existing databases; no longer used or shown in the
    # provider form since the inline card flow it configured was replaced by hosted redirect
    # flows. Not removed, as dropping a field is not allowed in stable versions.
    xendit_public_key = fields.Char(string="Xendit Public Key", groups='base.group_system')
    xendit_secret_key = fields.Char(
        string="Xendit Secret Key", groups='base.group_system', required_if_provider='xendit'
    )
    xendit_webhook_token = fields.Char(
        string="Xendit Webhook Token", groups='base.group_system', required_if_provider='xendit'
    )

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'xendit').support_tokenization = True

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'xendit':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'xendit':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_validation_currency(self):
        """ Override of `payment` to prefer the company's currency for validation operations.

        Xendit's payment channels are activated per country, and picking an arbitrary supported
        currency unrelated to the merchant's own country (as the base implementation would for a
        company whose currency isn't the first found) can make Xendit reject the request.

        Note: `self.ensure_one()`

        :return: The validation currency.
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        if self.code == 'xendit' and self.company_id.currency_id.name in const.SUPPORTED_CURRENCIES:
            return self.company_id.currency_id
        return super()._get_validation_currency()

    def _xendit_make_request(self, endpoint, payload=None, api_version=None, method='POST'):
        """ Make a request to Xendit API and return the JSON-formatted content of the response.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str api_version: The API version to be used for the request, if any.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = f'https://api.xendit.co/{endpoint}'
        auth = (self.xendit_secret_key, '')
        headers = {}
        if api_version:
            headers['api-version'] = api_version
        try:
            if method == 'GET':
                response = requests.get(url, auth=auth, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, auth=auth, headers=headers, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError("Xendit: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as err:
            error_message = err.response.json().get('message')
            _logger.exception(
                "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload)
            )
            raise ValidationError(
                "Xendit: " + _(
                    "The communication with the API failed. Xendit gave us the following"
                    " information: '%s'", error_message
                )
            )
        return response.json()
