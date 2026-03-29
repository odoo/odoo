# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_bictorys import const

_logger = logging.getLogger(__name__)

BICTORYS_API_URLS = {
    'test': 'https://api.test.bictorys.com',
    'enabled': 'https://api.bictorys.com',
}


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('bictorys', "Bictorys")], ondelete={'bictorys': 'set default'}
    )
    bictorys_secret_key = fields.Char(
        string="Secret Key",
        required_if_provider='bictorys',
        groups='base.group_system',
    )
    bictorys_webhook_secret = fields.Char(
        string="Webhook Secret",
        groups='base.group_system',
    )

    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'bictorys').update({
            'support_tokenization': False,
            'support_manual_capture': False,
            'support_refund': False,
        })

    def _bictorys_get_api_url(self):
        self.ensure_one()
        return BICTORYS_API_URLS.get(self.state, BICTORYS_API_URLS['test'])

    def _bictorys_make_request(self, endpoint, payload=None, method='POST'):
        self.ensure_one()
        url = f"{self._bictorys_get_api_url()}/{endpoint.strip('/')}"
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-API-Key': self.bictorys_secret_key,
        }
        _logger.info("Bictorys: '%s' request to %s:\n%s", method, url, pprint.pformat(payload))
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.exception("Bictorys: invalid API request at %s", url)
            try:
                error_msg = response.json().get('message', response.text)
            except Exception:
                error_msg = response.text
            raise ValidationError(
                "Bictorys: " + _("The communication with the API failed. Details: %s", error_msg)
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ValidationError("Bictorys: " + _("Could not establish the connection to the API."))
        return response.json()

    def _get_supported_currencies(self):
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'bictorys':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'bictorys':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)
        # Exclude Bictorys from validation flows.
        return providers.filtered(lambda p: not (p.code == 'bictorys' and is_validation))

    def _is_published(self):
        """ Override to prevent Bictorys from appearing as an online POS payment provider.

        pos_online_payment searches published providers to auto-create online payment methods.
        Bictorys is a terminal provider, not an online POS payment provider.
        """
        if self.code == 'bictorys':
            return False
        return super()._is_published()
