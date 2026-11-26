import logging
from uuid import uuid4

import requests

from odoo import fields, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_payment_method_bancontact_pay import const
from odoo.addons.pos_payment_method_bancontact_pay.errors.http import HTTP_ERRORS

_logger = logging.getLogger(__name__)


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    bancontact_api_key = fields.Char("Bancontact API Key", groups="pos_payment_method.group_payment_method_admin", help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a product > Manage API keys > View API key")
    bancontact_ppid = fields.Char("Bancontact PPID", help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a shop > Read the product ID from the card")
    bancontact_test_mode = fields.Boolean("Preprod", help="Run transactions in Bancontact's preprod environment.")
    bancontact_usage = fields.Selection(
        selection=[
            ("display", "On-Screen Display"),
            ("sticker", "Static Sticker"),
        ],
        string="QR Usage",
        default="display",
        required=True,
        help=(
            "Defines how the QR Code is presented to the customer:\n"
            "- On-Screen Display: A new QR code is dynamically shown on the screen for each order.\n"
            "- Static Sticker: A fixed QR sticker placed near the counter is used for scanning with every order."
        ),
    )

    def _get_qr_provider_selection(self):
        return super()._get_qr_provider_selection() + [("bancontact_pay", "Bancontact Pay")]

    def bancontact_download_sticker(self):
        self._check_access()
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/bancontact_pay/sticker/{self.id}",
            "target": "new",
        }

    def _bancontact_check_currency(self, currency):
        if currency.name not in const.SUPPORTED_CURRENCIES:
            raise ValidationError(
                self.env._(
                    "Bancontact Pay only supports these currencies: %(currencies)s.",
                    currencies=", ".join(const.SUPPORTED_CURRENCIES),
                ),
            )

    def _bancontact_prepare_payment_request(self, amount: float, currency, extra_args: dict):
        """Prepare the endpoint and JSON payload for a Bancontact payment creation call."""
        callback_url = self._bancontact_get_callback_url()
        shop_name = extra_args.get("shop_name", "")
        description = self.env._("Payment at %(company)s\nPOS %(shop)s", company=self.env.company.name, shop=shop_name)

        payment_request = {
            "reference": extra_args.get("payment_uuid", str(uuid4())).replace("-", ""),
            "amount": self._convert_amount_to_units(amount, currency),
            "currency": currency.name,
            "description": description[:140],
            "identifyCallbackUrl": callback_url,
            "callbackUrl": callback_url,
        }
        url = f"{self._bancontact_get_api_url("merchant")}/v3/payments"
        if self.bancontact_usage == "sticker":
            payment_request |= {
                "posId": f"pm{self.id}",
                "shopName": shop_name[:36],
            }
            url = f"{self._bancontact_get_api_url("merchant")}/v3/payments/pos"

        return url, payment_request

    def _bancontact_get_api_url(self, target):
        """Return the Bancontact endpoint URL for the current environment."""
        environment = "preprod" if self.bancontact_test_mode else "production"
        return const.API_URLS[environment][target]

    def _bancontact_get_callback_url(self):
        """Build the callback URL used by Bancontact Pay to notify payment status."""
        return f"{self.get_base_url()}/bancontact_pay/webhook?payment_method_id={self.id}"

    def _bancontact_assert_http_success(self, response: requests.Response, extra_errors: dict | None = None):
        errors = {**HTTP_ERRORS, **(extra_errors or {})}
        if response.status_code in errors:
            error_message, exception_class = errors[response.status_code]
            try:
                error_data = response.json()
            except requests.exceptions.JSONDecodeError:
                error_data = {}
            code = error_data.get("code", "")

            exception_msg = f"{error_message} (ERR: {response.status_code}"
            if code:
                exception_msg += f" - {code}"
            exception_msg += ")"
            raise exception_class(exception_msg)

        response.raise_for_status()

    def _bancontact_status_to_result(self, bancontact_status: str):
        if bancontact_status == "SUCCEEDED":
            return {"status": "paid"}
        if bancontact_status in ["PENDING", "IDENTIFIED", "AUTHORIZED", "PENDING_MERCHANT_ACKNOWLEDGEMENT"]:
            return {"status": "pending"}
        if bancontact_status == "EXPIRED":
            error = self.env._("The QR code has expired.")
        elif bancontact_status == "CANCELLED":
            error = None
        else:
            error = self.env._("The QR code payment failed.")
        return {"status": "failed", "error": error}

    def _bancontact_fetch_sticker_image(self):
        self.ensure_one()
        if self.payment_provider != "bancontact_pay":
            raise ValidationError(self.env._("Bancontact sticker URL can only be generated for payment methods using Bancontact Pay as provider."))
        if self.bancontact_usage != "sticker":
            raise ValidationError(self.env._("Bancontact sticker URL can only be generated for payment methods configured with 'Static Sticker' usage."))
        if not self.bancontact_ppid:
            raise ValidationError(self.env._("Bancontact PPID must be set to generate the sticker URL."))
        qr_url = self._bancontact_get_api_url("qrcode")
        response = requests.get(qr_url, params={
            "f": "PNG",
            "s": "XL",
            "c": f"https://payconiq.com/l/1/{self.bancontact_ppid}/pm{self.id}",
        }, timeout=10)
        response.raise_for_status()
        return response.content

    def _start_payment(self, amount: float, currency, extra_args: dict) -> dict:
        if self.payment_provider != "bancontact_pay":
            return super()._start_payment(amount, currency, extra_args)

        self._bancontact_check_currency(currency)
        headers = {
            "Authorization": f"Bearer {self.sudo().bancontact_api_key}",
        }
        url, payload = self._bancontact_prepare_payment_request(amount, currency, extra_args)

        response = None
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            self._bancontact_assert_http_success(response)
            bancontact_data = response.json()
        except Exception as e:
            reason = response.text if response is not None else str(e)
            _logger.warning("%s payment creation failed: ppid=%s, reason=%s, payload=%s", const.LOG_PREFIX, self.bancontact_ppid, reason, payload)
            raise

        bancontact_id = bancontact_data["paymentId"]
        bancontact_qr = self.bancontact_usage == "display" and bancontact_data.get("_links", {}).get("qrcode", {}).get("href", "")
        if bancontact_qr:
            bancontact_qr += "&f=SVG"

        _logger.info("%s payment creation succeeded: ppid=%s, bancontact_id=%s", const.LOG_PREFIX, self.bancontact_ppid, bancontact_id)
        return {
            "transaction_id": bancontact_id,
            "qr_code": bancontact_qr,
        }

    def _get_transaction_status(self, transaction_id: str) -> dict:
        if self.payment_provider != "bancontact_pay":
            return super()._get_transaction_status(transaction_id)

        url = f"{self._bancontact_get_api_url("merchant")}/v3/payments/{transaction_id}"
        headers = {
            "Authorization": f"Bearer {self.sudo().bancontact_api_key}",
        }

        try:
            response = requests.get(url, headers=headers, timeout=5)
            response_body = response.json()
            self._bancontact_assert_http_success(response)
        except Exception as e:
            reason = response.text if response is not None else str(e)
            _logger.warning("%s get payment status failed: ppid=%s, transaction_id=%s, reason=%s", const.LOG_PREFIX, self.bancontact_ppid, transaction_id, reason)
            raise

        return self._bancontact_status_to_result(response_body["status"])

    def _cancel_transaction(self, transaction_id: str) -> dict:
        if self.payment_provider != "bancontact_pay":
            return super()._cancel_transaction(transaction_id)

        url = f"{self._bancontact_get_api_url("merchant")}/v3/payments/{transaction_id}"
        headers = {
            "Authorization": f"Bearer {self.sudo().bancontact_api_key}",
        }

        response = None
        try:
            response = requests.delete(url, headers=headers, timeout=5)
            self._bancontact_assert_http_success(response, {
                422: (self.env._(
                        "The customer is currently completing the payment, so it cannot be cancelled at this time.\n"
                        "If you need to cancel it, please ask the customer to do so on their device."),
                    ValidationError,
                ),
            })
        except Exception as e:
            reason = response.text if response is not None else str(e)
            _logger.warning("%s payment cancellation failed: ppid=%s, transaction_id=%s, reason=%s", const.LOG_PREFIX, self.bancontact_ppid, transaction_id, reason)
            raise

        return {}
