# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import new as hashnew

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_ogone import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
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
        string="SHA Key IN", required_if_provider='ogone', groups='base.group_system')
    ogone_shakey_out = fields.Char(
        string="SHA Key OUT", required_if_provider='ogone', groups='base.group_system')
    ogone_hash_function = fields.Selection(
        [('sha1', 'SHA1'), ('sha256', 'SHA256'), ('sha512', 'SHA512')], default='sha512',
        string="Hash function", required_if_provider='ogone',
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'ogone').update({
            'support_tokenization': True,
        })

    #=== BUSINESS METHODS ===#

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of payment to unlist Ogone providers for validation operations. """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'ogone')

        return providers

    def _ogone_get_api_url(self, api_key):
        """ Return the appropriate URL of the requested API for the provider state.

        Note: self.ensure_one()

        :param str api_key: The API whose URL to get: 'hosted_payment_page' or 'directlink'
        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            api_urls = {
                'hosted_payment_page': 'https://secure.ogone.com/ncol/prod/orderstandard_utf8.asp',
                'directlink': 'https://secure.ogone.com/ncol/prod/orderdirect_utf8.asp',
            }
        else:  # 'test'
            api_urls = {
                'hosted_payment_page': 'https://ogone.test.v-psp.com/ncol/test/orderstandard_utf8.asp',
                'directlink': 'https://ogone.test.v-psp.com/ncol/test/orderdirect_utf8.asp',
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
            return not incoming or _key in const.VALID_KEYS

        key = self.ogone_shakey_out if incoming else self.ogone_shakey_in  # Swapped for Ogone's POV
        if format_keys:
            formatted_items = [(k.upper().replace('_', '.'), v) for k, v in values.items()]
        else:
            formatted_items = [(k.upper(), v) for k, v in values.items()]
        sorted_items = sorted(formatted_items)
        signing_string = ''.join(f'{k}={v}{key}' for k, v in sorted_items if _filter_key(k) and v)
        shasign = hashnew(self.ogone_hash_function)
        shasign.update(signing_string.encode())
        return shasign.hexdigest()

    def _ogone_make_request(self, payload=None, method='POST'):
        """ Make a request to one of Ogone APIs.

        Note: self.ensure_one()

        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return The content of the response
        :rtype: bytes
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = self._ogone_get_api_url('directlink')
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
