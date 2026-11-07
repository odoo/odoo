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
    xendit_secret_key = fields.Char(
        string="Xendit Secret Key", groups='base.group_system', required_if_provider='xendit'
    )
    xendit_webhook_token = fields.Char(
        string="Xendit Webhook Token", groups='base.group_system', required_if_provider='xendit'
    )

    # === BUSINESS METHODS ===#

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
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _xendit_make_request(self, payload=None):
        """ Make a request to Xendit API and return the JSON-formatted content of the response.

        Note: self.ensure_one()

        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        auth = (self.xendit_secret_key, '')
        url = "https://api.xendit.co/v2/invoices"
        try:
            response = requests.post(url, json=payload, auth=auth, timeout=10)
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
