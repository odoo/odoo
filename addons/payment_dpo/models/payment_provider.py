# Part of Odoo. See LICENSE file for full copyright and licensing details.

import xml.etree.ElementTree as ET

from odoo import fields, models

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_dpo import const


_logger = get_payment_logger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('dpo', "DPO")], ondelete={'dpo': 'set default'})
    dpo_service_ref = fields.Char(string="DPO Service ID", required_if_provider='dpo', copy=False)
    dpo_company_token = fields.Char(
        string="DPO Company Token",
        required_if_provider='dpo',
        copy=False,
        groups='base.group_system',
    )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'dpo':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != 'dpo':
            return super()._build_request_url(endpoint, **kwargs)
        return 'https://secure.3gdirectpay.com/API/v6/'

    def _build_request_headers(self, *args, **kwargs):
        """Override of `payment` to build the request headers."""
        if self.code != 'dpo':
            return super()._build_request_headers(*args, **kwargs)
        return {'Content-Type': 'application/xml; charset=utf-8'}

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to parse the response content."""
        if self.code != 'dpo':
            return super()._parse_response_content(response, **kwargs)

        root = ET.fromstring(response.content.decode('utf-8'))
        transaction_data = {element.tag: element.text for element in root}
        return transaction_data
