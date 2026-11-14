# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

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
            if not provider.available_currency_ids or provider.available_currency_ids.filtered(
                lambda c: c.name not in const.SUPPORTED_CURRENCIES
            ):
                raise ValidationError(
                    self.env._("Only currencies supported by QFPay can be selected.")
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        if self.code != "qfpay":
            return super()._get_default_payment_method_codes()

        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _qfpay_calculate_signature(self, payload, is_webhook=False):
        """Generate the QFPay signature of an API request or of a webhook notification.

        API requests are signed from their parameters, sorted by key, with empty values filtered
        out and joined in query format. Webhook notifications are signed from their raw body.

        :param dict|bytes payload: The request parameters, or the raw body of the notification if
               `is_webhook` is set.
        :param bool is_webhook: Whether the signature is computed for a webhook notification.
        :return: The calculated signature.
        :rtype: str
        """
        if is_webhook:
            signing_string = payload
        else:
            items = sorted((k, str(v)) for k, v in (payload or {}).items() if v not in (None, ""))
            signing_string = "&".join(f"{k}={v}" for k, v in items).encode("utf-8")

        return hashlib.md5(signing_string + self.qfpay_app_key.encode("utf-8")).hexdigest().upper()

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the QFPay Element API URL."""
        if self.code != "qfpay":
            return super()._build_request_url(endpoint, **kwargs)

        if self.is_live:
            api_url = "https://openapi-hk.qfapi.com"
        else:
            api_url = "https://openapi-int.qfapi.com"
        return urljoin(api_url, endpoint)

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

    def _parse_response_content(self, response, **kwargs):
        """Override of `payment` to raise on QFPay error response codes."""
        if self.code != "qfpay":
            return super()._parse_response_content(response, **kwargs)

        response_content = response.json()
        if response_content.get("respcd") != "0000":
            raise ValidationError(
                self.env._(
                    "The payment provider rejected the request.\n%s",
                    response_content.get("respmsg") or response_content.get("resperr"),
                )
            )
        return response_content
