# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import hmac
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_aba_payway import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("aba_payway", "ABA PayWay")], ondelete={"aba_payway": "set default"},
    )
    aba_payway_merchant_id = fields.Char(
        string="ABA PayWay Merchant ID",
        help="The Merchant ID of the ABA PayWay account.",
        required_if_provider="aba_payway",
        copy=False,
    )
    aba_payway_api_key = fields.Char(
        string="ABA PayWay API Key",
        help="The API key of the ABA PayWay account.",
        required_if_provider="aba_payway",
        copy=False,
        groups="base.group_system",
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        if self.code != "aba_payway":
            return super()._get_supported_currencies()

        return (
            super()
            ._get_supported_currencies()
            .filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)
        )

    # === CONSTRAINT METHODS === #

    @api.constrains("available_currency_ids")
    def _check_currency_is_supported(self):
        for provider in self.filtered(lambda p: p.code == "aba_payway"):
            if provider.available_currency_ids.filtered(
                lambda c: c.name not in const.SUPPORTED_CURRENCIES,
            ):
                raise ValidationError(
                    self.env._(
                        "ABA PayWay only supports the following currencies: %s",
                        ", ".join(const.SUPPORTED_CURRENCIES),
                    ),
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        if self.code != "aba_payway":
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _aba_payway_get_api_url(self):
        """Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        if self.is_live:
            return "https://checkout.payway.com.kh"
        return "https://checkout-sandbox.payway.com.kh"

    def _aba_payway_calculate_signature(self, data, keys=const.PURCHASE_SIGNATURE_KEYS):
        """Compute the signature of the provided data according to ABA PayWay's documentation.

        The signature is computed by concatenating the values of the data for the given keys, in
        the given order, hashing the result with HMAC-SHA512 using the API key as secret, and
        encoding the hash in Base64.

        :param dict data: The data to sign.
        :param Iterable[str] keys: The keys of the values to sign, in the order in which they must
                                   be concatenated.
        :return: The signature.
        :rtype: str
        """
        signing_string = "".join(_to_php_string(data.get(key)) for key in keys)
        signature = hmac.new(
            self.aba_payway_api_key.encode(), signing_string.encode(), hashlib.sha512,
        ).digest()
        return base64.b64encode(signature).decode()


def _to_php_string(value):
    """Convert a value to a string following PHP's type juggling rules.

    ABA PayWay computes signatures from values converted to strings by PHP, which formats some
    values differently from Python (e.g., `100.0` -> `'100'`, `None` -> `''`, `True` -> `'1'`).

    :param value: The value to convert.
    :return: The string representation of the value.
    :rtype: str
    """
    if value is None or value is False:
        return ""
    if value is True:
        return "1"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, dict | list):
        return json.dumps(value, separators=(",", ":")).replace("/", "\\/")
    return str(value)
