# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from werkzeug import urls

from odoo import fields, models

from odoo.addons.payment import const as payment_const
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_mercado_pago import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'}
    )
    mercado_pago_access_token = fields.Char(
        string="Mercado Pago Access Token",
        required_if_provider='mercado_pago',
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'mercado_pago':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _mercado_pago_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Mercado Pago API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        """
        self.ensure_one()

        url = urls.url_join('https://api.mercadopago.com', endpoint)
        headers = {
            'Authorization': f'Bearer {self.mercado_pago_access_token}',
            'X-Platform-Id': 'dev_cdf1cfac242111ef9fdebe8d845d0987',
        }
        try:
            if method == 'GET':
                response = requests.get(
                    url, params=payload, headers=headers, timeout=payment_const.TIMEOUT
                )
            else:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=payment_const.TIMEOUT
                )
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception(payment_const.UNABLE_TO_REACH_ENDPOINT, url)
            return payment_utils.format_error_response(payment_const.API_CONNECTION_ERROR)
        except requests.exceptions.HTTPError as err:
            _logger.exception(payment_const.INVALID_API_REQUEST, url, payload, err.response.text)
            response_content = err.response.json()
            return payment_utils.format_error_response(
                f'{payment_const.API_COMMUNICATION_ERROR}{response_content.get("code")}'
                f' {response_content.get("message")}'
            )
        return response.json()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'mercado_pago':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
