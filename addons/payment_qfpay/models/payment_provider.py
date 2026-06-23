# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment_qfpay import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(selection_add=[("qfpay", "QFPay")], ondelete={"qfpay": "set default"})
    qfpay_app_code = fields.Char(string="App Code", required_if_provider="qfpay", copy=False)
    qfpay_app_key = fields.Char(
        string="App Key", required_if_provider="qfpay", groups="base.group_system", copy=False
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "qfpay":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    # === CONSTRAINT METHODS === #

    @api.constrains("available_currency_ids")
    def _check_currency_is_supported(self):
        for provider in self.filtered(lambda p: p.code == "qfpay"):
            if provider.available_currency_ids.filtered(
                lambda c: c.name not in const.SUPPORTED_CURRENCIES
            ):
                raise ValidationError(
                    self.env._(
                        "QFPay only supports the following currencies: %s",
                        ", ".join(const.SUPPORTED_CURRENCIES),
                    )
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        if self.code != "qfpay":
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _qfpay_get_env_config(self):
        """Return the environment config dict for the current provider state.

        :return: The environment config dict containing the API URL, SDK URL, SDK
                 environment, and SDK region.
        :rtype: dict
        """
        if self.is_live:
            return {
                "api_url": "https://openapi-hk.qfapi.com",
                "sdk_url": "https://cdn-hk.qfapi.com/qfpay_element/qfpay.js",
                "sdk_env": "prod",
                "sdk_region": "hk",
            }
        return {
            "api_url": "https://openapi-int.qfapi.com",
            "sdk_url": "https://cdn-int.qfapi.com/qfpay_element/qfpay.js",
            "sdk_env": "qa",
            "sdk_region": "qa",
        }

    def _qfpay_get_inline_form_values(self, pm_code):
        """Return a serialized JSON of the required values to render the inline form.

        Note: `self.ensure_one()`

        :param str pm_code: The code of the payment method whose inline form to render.
        :return: The JSON serial of the required values to render the inline form.
        :rtype: str
        """
        self.ensure_one()

        env_config = self._qfpay_get_env_config()
        inline_form_values = {
            "sdk_url": env_config["sdk_url"],
            "sdk_env": env_config["sdk_env"],
            "sdk_region": env_config["sdk_region"],
            "payment_method_code": pm_code,
            "picker_payment_type": const.PAYMENT_PICKER_TYPES.get(pm_code, ""),
        }
        return json.dumps(inline_form_values)

    def _qfpay_calculate_signature(self, data=None, signing_string=None):
        """Generate the QFPay signature from payload data or a prebuilt input.

        If `signing_string` is provided, it is signed directly.
        Otherwise, the signing string is built from `data` by filtering empty values,
        sorting by key and joining in query format.

        :param dict data: Optional mapping used to build the signing string.
        :param str|bytes signing_string: Optional raw signing input before app key.
        :return: The calculated signature.
        :rtype: str
        """
        if signing_string:
            if isinstance(signing_string, bytes):
                signing_input = signing_string
            else:
                signing_input = str(signing_string).encode("utf-8")
        else:
            data = data or {}
            items = sorted([(k, str(v)) for k, v in data.items()])
            signing_input = "&".join(f"{k}={v}" for k, v in items).encode("utf-8")

        payload = signing_input + (self.qfpay_app_key or "").encode("utf-8")
        return hashlib.md5(payload).hexdigest().upper()

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the QFPay Element API URL."""
        if self.code != "qfpay":
            return super()._build_request_url(endpoint, **kwargs)

        return urljoin(self._qfpay_get_env_config()["api_url"], endpoint)

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        """Override of `payment` to add QFPay authentication headers.

        QFPay's Element API requires:
        - X-QF-APPCODE: the store app code
        - X-QF-SIGN: MD5 signature of the request payload
        - X-QF-SIGNTYPE: the signature method, which is always MD5
        """
        if self.code != "qfpay":
            return super()._build_request_headers(method, endpoint, payload, **kwargs)

        return {
            "X-QF-APPCODE": self.qfpay_app_code,
            "X-QF-SIGN": self._qfpay_calculate_signature(payload),
            "X-QF-SIGNTYPE": "MD5",
        }

    def _parse_response_error(self, response):
        """Override of `payment` to parse the error message from QFPay JSON responses."""
        if self.code != "qfpay":
            return super()._parse_response_error(response)

        response_data = response.json()
        return response_data.get("respmsg") or response_data.get("resperr")
