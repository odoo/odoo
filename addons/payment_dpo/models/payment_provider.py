# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_dpo import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('dpo', "DPO")], ondelete={'dpo': 'set default'})
    dpo_service_ref = fields.Char(string="DPO Service ID", required_if_provider='dpo')
    dpo_company_token = fields.Char(
        string="DPO Company Token",
        required_if_provider='dpo',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _dpo_make_request(self, payload=None):
        """ Make a request to DPO API to create or verify the Transaction Token.

        Note: self.ensure_one()

        :param dict payload: The payload of the request.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        api_url = 'https://secure.3gdirectpay.com/API/v6/'
        headers = {'Content-Type': 'application/xml; charset=utf-8'}
        try:
            response = requests.post(url=api_url, data=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", api_url, pprint.pformat(payload)
                )
                raise ValidationError("DPO: " + _("The communication with the API failed."))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach %s", api_url)
            raise ValidationError("DPO: " + _("The communication with the API failed."))
        root = ET.fromstring(response.content.decode('utf-8'))
        transaction_data = {element.tag: element.text for element in root}

        return transaction_data

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'dpo':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
