# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import hashlib
from urllib.parse import quote_plus

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_ecpay import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("ecpay", "ECPay")], ondelete={"ecpay": "set default"})
    ecpay_merchant_id = fields.Char(
        string="ECPay Merchant ID",
        help="The Merchant ID solely used to identify your ECPay account.",
        required_if_provider="ecpay",
        copy=False,
    )
    ecpay_hash_key = fields.Char(
        string="ECPay Secure Hash Key",
        required_if_provider="ecpay",
        groups="base.group_system",
        copy=False,
    )
    ecpay_hash_iv = fields.Char(
        string="ECPay Secure Hash IV",
        required_if_provider="ecpay",
        groups="base.group_system",
        copy=False,
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return TWD as the only supported currency."""
        if self.code != "ecpay":
            return super()._get_supported_currencies()

        return (
            super()
            ._get_supported_currencies()
            .filtered(lambda c: c.name == const.SUPPORTED_CURRENCY)
        )

    # === CONSTRAINT METHODS === #

    @api.constrains("available_currency_ids")
    def _check_currency_is_supported(self):
        for provider in self.filtered(lambda p: p.code == "ecpay"):
            if provider.available_currency_ids.filtered(
                lambda c: c.name != const.SUPPORTED_CURRENCY
            ):
                raise ValidationError(self.env._("ECPay only supports TWD."))

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        if self.code != "ecpay":
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS ===#

    def _ecpay_get_api_url(self):
        """Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        if self.is_live:
            return "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5"
        return "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"

    def _ecpay_calculate_signature(self, data):
        """Compute the signature for the provided data.

        ECPay steps for calculating the checksum are as follows:
        Calculation Formula: CheckMacValue = SHA256(URLEncode(HashKey + Data plaintext + HashIV))

        Steps:
        1. Extract the plaintext parameter Data as a string.
        2. The string is sandwiched by HashKey in the beginning and HashIV at the end.
        3. The entire string goes through URL encoding.
        4. Switch to lowercase.
        5. The string is encrypted using SHA256 to generate a hash value.
        6. It is converted into upper case to generate a CheckMacValue.

        :param dict data: The data to sign.
        :return: The calculated signature.
        :rtype: str
        """
        ordered_data = collections.OrderedDict(sorted(data.items(), key=lambda k: k[0].lower()))
        encoding_lst = [
            f"HashKey={self.ecpay_hash_key}&",
            "".join([f"{key}={value}&" for key, value in ordered_data.items()]),
            f"HashIV={self.ecpay_hash_iv}",
        ]
        safe_characters = "-_.!*()"
        encoding_str = "".join(encoding_lst)
        encoding_str = quote_plus(encoding_str, safe=safe_characters).lower()
        return hashlib.sha256(encoding_str.encode("utf-8")).hexdigest().upper()
