# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import sha256

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .const import VALID_KEYS

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('ogone', "Ogone")], ondelete={'ogone': 'set default'})
    ogone_pspid = fields.Char(
        string="PSPID", help="The ID solely used to identify the account with Ogone",
        required_if_provider='ogone')
    ogone_userid = fields.Char(
        string="API User ID", help="The ID solely used to identify the API user with Ogone",
        required_if_provider='ogone')
    ogone_password = fields.Char(
        string="API User Password", required_if_provider='ogone', groups='base.group_system')
    ogone_shakey_in = fields.Char(
        string="SHA Key IN", size=32, required_if_provider='ogone', groups='base.group_system')
    ogone_shakey_out = fields.Char(
        string="SHA Key OUT", size=32, required_if_provider='ogone', groups='base.group_system')

    def _get_validation_amount(self):
        """ Override of payment to return the amount for Ogone validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.provider != 'ogone':
            return res

        return 1.0

    def _ogone_get_api_url(self, api_key):
        """ Return the appropriate URL of the requested API for the acquirer state.

        Note: self.ensure_one()

        :param str api_key: The API whose URL to get: 'flexcheckout' or 'directlink'
        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            api_urls = {
                'flexcheckout': 'https://secure.ogone.com/Tokenization/HostedPage',
                'directlink': 'https://secure.ogone.com/ncol/prod/orderdirect.asp',
                'maintenancedirect': 'https://secure.ogone.com/ncol/prod/maintenancedirect.asp',
            }
        else:  # 'test'
            api_urls = {
                'flexcheckout': 'https://ogone.test.v-psp.com/Tokenization/HostedPage',
                'directlink': 'https://ogone.test.v-psp.com/ncol/test/orderdirect.asp',
                'maintenancedirect': 'https://ogone.test.v-psp.com/ncol/test/maintenancedirect.asp',
            }
        return api_urls.get(api_key)

    def _ogone_generate_signature(self, values, incoming=True, format_keys=False):
        """ Generate the signature for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (Ogone to
                              Odoo) or outgoing (Odoo to Ogone) communication.
        :param bool format_keys: Whether the keys must be formatted as uppercase, dot-separated
                                 strings to comply with Ogone APIs. This must be used when the keys
                                 are formatted as underscore-separated strings to be compliant with
                                 QWeb's `t-att-value`.
        :return: The signature
        :rtype: str
        """

        def _filter_key(_key):
            return not incoming or _key in VALID_KEYS

        key = self.ogone_shakey_in if incoming else self.ogone_shakey_out
        if format_keys:
            formatted_items = [(k.upper().replace('_', '.'), v) for k, v in values.items()]
        else:
            formatted_items = [(k.upper(), v) for k, v in values.items()]
        sorted_items = sorted(formatted_items)
        signing_string = ''.join(f'{k}={v}{key}' for k, v in sorted_items if _filter_key(k) and v)
        shasign = sha256(signing_string.encode("utf-8")).hexdigest()
        return shasign

    def _ogone_make_request(self, api_key, payload=None, method='POST'):
        """ Make a request to one of Ogone APIs.

        Note: self.ensure_one()

        :param str api_key: The API to which the request is made: 'flexcheckout' or 'directlink'
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return The content of the response
        :rtype: bytes
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = self._ogone_get_api_url(api_key)
        try:
            response = requests.request(method, url, data=payload, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Ogone: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError:
            _logger.exception("invalid API request at %s with data %s", url, payload)
            raise ValidationError("Ogone: " + _("The communication with the API failed."))
        return response.content
