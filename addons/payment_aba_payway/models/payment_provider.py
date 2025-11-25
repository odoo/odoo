# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime

import requests
from odoo.addons.payment_aba_payway import const

from odoo import _, models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('aba_payway', "ABA PayWay")], ondelete={'aba_payway': 'set default'})
    payway_merchant_id = fields.Char(
        string='PayWay Merchant ID',
        help="Enter your PayWay Merchant ID. You can find it in the email registered for your PayWay account.",
        required_if_provider="aba_payway",
        copy=False,
    )
    payway_api_key = fields.Char(
        string='PayWay API Key',
        help="Enter your production PayWay API Key. You can find it in the email registered for your PayWay account.",
        groups='base.group_system',
        required_if_provider="aba_payway",
        copy=False,
    )

    # === COMPUTE METHODS ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        if self.code != 'aba_payway':
            return super()._get_supported_currencies()

        return super()._get_supported_currencies().filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)

    # === BUSINESS METHODS === #

    def _make_payway_api_request(self, endpoint, payload):
        """Make a request to the PayWay API.

        :return: The API response.
        :rtype: dict
        """
        url = urljoin(self._payway_get_api_url(), endpoint)
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=True, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            _logger.warning('Error: %r with the given URL %r', error, url)
            raise ValidationError(_("Could not establish a connection to PayWay API. Error: %s", error))
        except json.decoder.JSONDecodeError as error:
            _logger.warning('JSONDecodeError: %r', error)
            raise ValidationError(_("Could not establish a connection to PayWay API. Error: %s", error))
        except ValueError as error:
            raise ValidationError(_("Could not establish a connection to PayWay API. Error: %s", error))

    def _payway_get_api_url(self):
        """Return the URL of the API corresponding to the selected PayWay environment.

        :return: The API URL.
        :rtype: str
        """
        if self.state == 'enabled':
            return 'https://checkout.payway.com.kh'
        else:
            return 'https://checkout-sandbox.payway.com.kh'

    def _payway_calculate_signature(self, data, keys=None):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        if keys is None:
            keys = const.PURCHASE_PAYMENT_SECURE_HASH_KEYS
        data_to_sign = [str(data.get(k, '')) for k in keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(self.payway_api_key.encode(), signing_string.encode(), hashlib.sha512).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded

    def _payway_api_check_transaction(self, tran_id):
        """Check the status of a PayWay transaction.

        :param str tran_id: The transaction ID to check.
        :return: An object containing the transaction status.
        :rtype: dict
        """
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': self.payway_merchant_id,
            'tran_id': tran_id,
        }
        payload.update({'hash': self._payway_calculate_signature(payload)})
        response = self._make_payway_api_request('/api/payment-gateway/v1/payments/check-transaction-2', payload)
        _logger.info('PayWay API response: %r', response)
        return response

    # === CONSTRAINT METHODS === #

    @api.constrains('available_currency_ids', 'state')
    def _limit_available_currency_ids(self):
        allowed_codes = set(const.SUPPORTED_CURRENCIES)
        for provider in self.filtered(lambda p: p.code == 'aba_payway'):
            unsupported_currency_codes = [
                currency.name
                for currency in provider.available_currency_ids
                if currency.name not in allowed_codes
            ]

            if provider.available_currency_ids.filtered(lambda c: c.name not in allowed_codes):
                raise ValidationError(_(
                    "ABA PayWay does not support the following currencies: %(currencies)s.",
                    currencies=", ".join(unsupported_currency_codes)))

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        if self.code != 'aba_payway':
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES
