# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment_aba_payway import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("aba_payway", "ABA PayWay")], ondelete={"aba_payway": "set default"})
    payway_merchant_id = fields.Char(
        string="PayWay Merchant ID",
        help="Enter your PayWay Merchant ID. You can find it in the email registered for your PayWay account.",
        required_if_provider="aba_payway",
        copy=False,
    )
    payway_api_key = fields.Char(
        string="PayWay API Key",
        help="Enter your production PayWay API Key. You can find it in the email registered for your PayWay account.",
        groups="base.group_system",
        required_if_provider="aba_payway",
        copy=False,
    )

    # === COMPUTE METHODS ===#

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        if self.code != "aba_payway":
            return super()._get_supported_currencies()

        return super()._get_supported_currencies().filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)

    # === BUSINESS METHODS === #

    def _payway_get_api_url(self):
        """Return the URL of the API corresponding to the selected PayWay environment.

        :return: The API URL.
        :rtype: str
        """
        if self.state == "enabled":
            return "https://checkout.payway.com.kh"
        return "https://checkout-sandbox.payway.com.kh"

    def _payway_calculate_signature(self, data, keys=const.PURCHASE_PAYMENT_SECURE_HASH_KEYS):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        The signature (hash) is computed following these steps:
        1.  Concatenate the fields from `data` in the exact order specified by `keys`
        2.  Apply HMAC-SHA512 encryption to the concatenated string using the ABA PayWay API Key (Public Key) as the secret.
        3.  Base64 encode the resulting binary hash to produce the final signature string.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        data_to_sign = [str(data.get(k, "")) for k in keys]
        signing_string = "".join(data_to_sign)
        hmac_hash = hmac.new(self.payway_api_key.encode(), signing_string.encode(), hashlib.sha512).digest()
        return base64.b64encode(hmac_hash).decode()

    # === CONSTRAINT METHODS === #

    @api.constrains("available_currency_ids", "state")
    def _limit_available_currency_ids(self):
        for provider in self.filtered(lambda p: p.code == "aba_payway"):
            unsupported_currency_codes = [
                currency.name
                for currency in provider.available_currency_ids
                if currency.name not in const.SUPPORTED_CURRENCIES
            ]

            if provider.available_currency_ids.filtered(lambda c: c.name not in const.SUPPORTED_CURRENCIES):
                raise ValidationError(
                    self.env._(
                        "ABA PayWay does not support the following currencies: %(currencies)s.",
                        currencies=", ".join(unsupported_currency_codes),
                    ),
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        if self.code != "aba_payway":
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "aba_payway":
            return super()._build_request_url(endpoint, **kwargs)

        return urljoin(self._payway_get_api_url(), endpoint)
