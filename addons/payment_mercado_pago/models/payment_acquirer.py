# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

import requests
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_mercado_pago.const import SUPPORTED_CURRENCIES


_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'}
    )
    mercado_pago_access_token = fields.Char(
        string="Mercado Pago Access Token",
        required_if_provider='mercado_pago',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of `payment` to unlist Mercado Pago acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda a: a.provider != 'mercado_pago')

        return acquirers

    def _mercado_pago_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Mercado Pago API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = urls.url_join('https://api.mercadopago.com', endpoint)
        headers = {'Authorization': f'Bearer {self.mercado_pago_access_token}'}
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception(
                        "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                    )
                    response_content = response.json()
                    error_code = response_content.get('error')
                    error_message = response_content.get('message')
                    raise ValidationError("Mercado Pago: " + _(
                        "The communication with the API failed. Mercado Pago gave us the following "
                        "information: '%s' (code %s)", error_message, error_code
                    ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Mercado Pago: " + _("Could not establish the connection to the API.")
            )
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()

        if self.provider != 'mercado_pago':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mercado_pago.payment_method_mercado_pago').id

    def _neutralize(self):
        super()._neutralize()

        self._neutralize_fields('mercado_pago', [
            'mercado_pago_access_token',
        ])
