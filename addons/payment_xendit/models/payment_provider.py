# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
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
    xendit_public_key = fields.Char(
        string="Xendit Public Key", groups='base.group_system',
        compute="_compute_xendit_public_key", inverse="_inverse_xendit_public_key", readonly=False
    )

    # === COMPUTE METHODS === #
    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'xendit').update({
            'support_tokenization': True,
        })

    def _compute_xendit_public_key(self):
        """ Get frokm system parameter"""
        for provider in self:
            if provider.code == 'xendit':
                xnd_public_key = self.env['ir.config_parameter'].sudo().get_param('xendit_public_key_%s' % provider.id, '')
                provider.xendit_public_key = xnd_public_key
            else:
                provider.xendit_public_key = ''

    def _inverse_xendit_public_key(self):
        for provider in self:
            if provider.code == 'xendit':
                self.env['ir.config_parameter'].sudo().set_param('xendit_public_key_%s' % provider.id, provider.xendit_public_key)

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

    def _xendit_make_request(self, endpoint, endpoint_param=None, payload=None, method='POST'):
        """ Make a request to Xendit API and return the JSON-formatted content of the response.

        Note: self.ensure_one()

        :param dict payload: The payload of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        auth = (self.xendit_secret_key, '')
        endpoint = endpoint if not endpoint_param else endpoint.format(**endpoint_param)
        url = f'https://api.xendit.co/{endpoint}'

        try:
            response = requests.request(method, url, json=payload, auth=auth, timeout=10)
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

    def _xendit_get_inline_form_values(self):
        """Return a serialized JSON of the required values to render the inline form

        Note: `self.ensure_one()`
        """
        self.ensure_one()

        inline_form_values = {
            "public_key": self.xendit_public_key,
        }
        return json.dumps(inline_form_values)

    def _get_redirect_form_view(self, is_validation=False):
        """ Override

        Since Xendit enables both direct and redirect_form, during operation='validation',
        will force use redirect_form (eventhough it's related to card payment)

        Note: `self.ensure_one()`

        :param bool is_validation: Whether the operation is a validation.
        :return: The view of the redirect form template.
        :rtype: record of `ir.ui.view`
        """
        self.ensure_one()
        if self.code == 'xendit' and is_validation:
            return False
        return super()._get_redirect_form_view(is_validation)
