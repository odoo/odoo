# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from werkzeug.urls import url_join, url_encode

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_flutterwave.controllers.main import FlutterwaveController

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('flutterwave', "Flutterwave")], ondelete={'flutterwave': 'set default'}
    )
    flutterwave_public_key = fields.Char(
        string="Flutterwave Public Key",
        help="The key solely used to identify the account with Flutterwave",
        required_if_provider='flutterwave',
    )
    flutterwave_secret_key = fields.Char(
        string="Flutterwave Secret Key",
        required_if_provider='flutterwave',
        groups='base.group_system',
    )
    flutterwave_encryption_key = fields.Char(
        string="Flutterwave Encryption Key",
        required_if_provider='flutterwave',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _flutterwave_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Flutterwave API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = url_join('https://api.flutterwave.com/v3/', endpoint)
        headers = {'Authorization': f'Bearer {self.flutterwave_secret_key}'}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError(
                "Flutterwave: " + _("Could not establish the connection to the API.")
            )
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", url, payload, error.response.text
            )
            raise ValidationError("Flutterwave: " + _("The communication with the API failed."))
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'flutterwave':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_flutterwave.payment_method_flutterwave').id

    def _neutralize(self):
        super()._neutralize()
        self._neutralize_fields(
            'flutterwave',
            ['flutterwave_public_key', 'flutterwave_secret_key', 'flutterwave_encryption_key'],
        )
