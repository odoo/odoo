import requests

from odoo import api, fields, models, tools
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)

from odoo.addons.pos_payconiq import const
from odoo.addons.pos_payconiq.utils.payconiq_errors import (
    check_payconiq_http_status,
)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    payconiq_api_key = fields.Char("Payconiq API Key")
    payconiq_ppid = fields.Char("Payconiq PPID")

    def _get_payment_external_qr_selection(self):
        return super()._get_payment_external_qr_selection() + [("payconiq", "Payconiq")]

    @api.constrains("use_payment_terminal", "journal_id", "company_id")
    def _check_use_payment_terminal(self):
        """
        Ensure that Payconiq payment methods use a supported currency.
        """
        for record in self:
            if record.use_payment_terminal == "payconiq":
                currency = (
                    record.journal_id.currency_id or record.company_id.currency_id
                )
                if currency.name not in const.SUPPORTED_CURRENCIES:
                    raise ValidationError(
                        record.env._(
                            "Payconiq only supports the following currencies: %s.\n"
                            "Please make sure the journal uses one of them.",
                        )
                        % ", ".join(const.SUPPORTED_CURRENCIES),
                    )

    def _compute_external_qr_sticker_url_payload(self):
        for record in self:
            if record.use_payment_terminal != "payconiq":
                continue

            record.external_qr_sticker_url = const.QR_GENERATOR_URL % (
                record.external_qr_sticker_size,
                record.payconiq_ppid,
                record.id,
            )

    # ================================ #
    #     Payconiq Payment Methods     #
    # ================================ #
    def create_payconiq_payment(self, **kwargs):
        # ----- TEST MODE -----
        if tools.config["test_enable"]:
            payload = {
                "uuid": kwargs.get("paymentUuid", ""),
                "payconiq_id": kwargs.get("paymentUuid", ""),
                "qr_code": "https://example.com/test_qr_code.png",
            }
            self.env["pos.payment.payconiq"].create(payload)
            return payload

        # ----- PRODUCTION MODE -----
        headers = {
            "Authorization": f"Bearer {self.payconiq_api_key}",
            "Content-Type": "application/json",
        }

        url, payload = self._prepare_payconiq_payment_request(**kwargs)
        response = requests.post(url, json=payload, headers=headers, timeout=5)

        errors = {
            400: (
                "Invalid request to Payconiq. Please check the payment details.",
                MissingError,
            ),
            401: (
                "Authentication with Payconiq failed. Please verify your API key.",
                AccessDenied,
            ),
            403: (
                "Access denied. Please check your Payconiq API permissions.",
                AccessDenied,
            ),
            404: (
                "Merchant profile not found on Payconiq. Please check your Payment Profile ID.",
                UserError,
            ),
            422: (
                "Unable to process payment. Please verify your configuration or try again later.",
                ValidationError,
            ),
            429: (
                "Rate limit reached with Payconiq. Please wait and try again.",
                AccessDenied,
            ),
            500: (
                "Payconiq is currently unavailable. Please try again later.",
                AccessError,
            ),
            503: (
                "Payconiq is currently unavailable. Please try again later.",
                AccessError,
            ),
        }
        check_payconiq_http_status(response, errors)

        result = response.json()

        payload = {
            "uuid": kwargs.get("paymentUuid", ""),
            "payconiq_id": result["paymentId"],
            "qr_code": result.get("_links", {}).get("qrcode", {}).get("href", ""),
        }

        self.env["pos.payment.payconiq"].create(payload)
        return payload

    def _get_callback_url(self):
        """
        Construct the callback URL for Payconiq to send payment status updates.
        """
        base_url = const.BASE_CALLBACK_URL or self.get_base_url()
        return f"{base_url}/webhook/payconiq"

    def _prepare_payconiq_payment_request(self, **kwargs):
        """
        Wrapper to prepare the appropriate Payconiq payment request.
        """
        is_sticker = kwargs.get("is_sticker", False)
        if is_sticker:
            return self._prepare_sticker_payment_request(**kwargs)
        return self._prepare_display_payment_request(**kwargs)

    def _prepare_display_payment_request(self, **kwargs):
        """
        Prepare the payload for creating a Payconiq payment for a on display QR code.
        https://docs.payconiq.be/apis/merchant-payment.openapi/merchant-endpoints/create

        Field notes:
            - `amount`: Payconiq expects the amount in cents (integer), so we multiply the float by 100.
            - `callbackUrl`: Endpoint that receives Payconiq's payment status updates.
        """
        callback_url = self._get_callback_url()
        return [
            f"{const.API_URL}/v3/payments",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _prepare_sticker_payment_request(self, **kwargs):
        """
        Prepare the payload for creating a Payconiq payment for a static QR (sticker)
        https://docs.payconiq.be/apis/merchant-payment.openapi/merchant-endpoints/create_static_qr_payment

        Field notes:
            - `amount`: Payconiq expects the amount in cents (integer), so we multiply the float by 100.
            - `posId`: We use the payment method ID here instead of the POS config ID
            because each Payconiq sticker is tied to a unique Payconiq POS entity.
            By creating one payment method per sticker, we can support multiple stickers
            under the same POS config.
            - `shopId`: Based on the POS config ID, representing the shop as defined in Odoo.
            - `shopName`: Human-readable name of the POS, shown to the customer.
            - `callbackUrl`: Endpoint that receives Payconiq's payment status updates.
        """
        callback_url = self._get_callback_url()
        return [
            f"{const.API_URL}/v3/payments/pos",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "posId": ("PM" + str(kwargs.get("paymentMethodId", "")))[:36],
                "shopId": ("POS" + str(kwargs.get("posId", "")))[:36],
                "shopName": kwargs.get("shopName", "")[:36],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def cancel_payconiq_payment(self, **kwargs):
        # ----- TEST MODE -----
        if tools.config["test_enable"]:
            return True

        # ----- PRODUCTION MODE -----
        headers = {
            "Authorization": f"Bearer {self.payconiq_api_key}",
            "Content-Type": "application/json",
        }

        payconiq_id = kwargs.get("payconiq_id")
        if not payconiq_id:
            msg = "Missing Payconiq payment ID for cancellation."
            raise MissingError(msg)

        url = f"{const.API_URL}/v3/payments/{payconiq_id}"
        response = requests.delete(url, headers=headers, timeout=5)

        errors = {
            401: (
                "Authentication with Payconiq failed. Please verify your API key.",
                AccessDenied,
            ),
            403: (
                "Access denied. You may not have permission to cancel this Payconiq payment.",
                AccessDenied,
            ),
            404: (
                "Payment not found on Payconiq. Please check the payment ID.",
                UserError,
            ),
            422: (
                "Unable to cancel payment. The payment may not be in a cancellable state.",
                ValidationError,
            ),
            429: (
                "Rate limit reached with Payconiq. Please wait and try again.",
                AccessDenied,
            ),
            500: (
                "Technical error from Payconiq. Please try again later.",
                AccessError,
            ),
            503: (
                "Payconiq service is currently unavailable. Please try again later.",
                AccessError,
            ),
        }
        check_payconiq_http_status(response, errors)

        pos_payment_payconiq = self.env["pos.payment.payconiq"].search(
            [("payconiq_id", "=", payconiq_id)],
            limit=1,
        )
        pos_payment_payconiq.write({"state": "cancelled"})

        return True
