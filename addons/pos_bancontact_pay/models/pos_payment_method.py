from json import JSONDecodeError
from urllib.parse import urlencode

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.errors.http import HTTP_ERRORS


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # ----- Fields ----- #
    def _get_external_qr_provider_selection(self):
        return super()._get_external_qr_provider_selection() + [("bancontact_pay", "Bancontact Pay")]

    def _auto_init(self):
        if not column_exists(self.env.cr, "pos_payment_method", "bancontact_usage"):
            create_column(self.env.cr, "pos_payment_method", "bancontact_usage", "varchar")
        if not column_exists(self.env.cr, "pos_payment_method", "bancontact_sticker_size"):
            create_column(self.env.cr, "pos_payment_method", "bancontact_sticker_size", "varchar")
        if not column_exists(self.env.cr, "pos_payment_method", "bancontact_sticker_url"):
            create_column(self.env.cr, "pos_payment_method", "bancontact_sticker_url", "varchar")
        return super()._auto_init()

    bancontact_api_key = fields.Char("Bancontact API Key")
    bancontact_ppid = fields.Char("Bancontact PPID")
    bancontact_test_mode = fields.Boolean(help="Run transactions in the test environment.")
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
    bancontact_sticker_size = fields.Selection(
        selection=[
            ("S", "Small (180x180)"),
            ("M", "Medium (250x250)"),
            ("L", "Large (400x400)"),
            ("XL", "Extra Large (800x800)"),
        ],
        string="Sticker Size",
        required=True,
        default="S",
    )
    bancontact_sticker_url = fields.Char("Sticker URL", compute="_compute_bancontact_sticker_url", store=True)

    # ----- Model ----- #
    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ["bancontact_usage"]

    @api.depends("payment_provider", "bancontact_sticker_size", "bancontact_ppid", "bancontact_test_mode")
    def _compute_bancontact_sticker_url(self):
        """Compute the sticker QR code URL for Bancontact Pay sticker usage."""
        for record in self:
            if (record.bancontact_sticker_url and (record.payment_provider != "bancontact_pay" or record.bancontact_usage != "sticker")):
                record.bancontact_sticker_url = False
                continue

            params = urlencode({
                'f': 'PNG',
                's': record.bancontact_sticker_size,
                'c': f'https://payconiq.com/l/1/{record.bancontact_ppid}/pm{record.id}',
            })
            record.bancontact_sticker_url = f'{record._get_bancontact_api_url("qrcode")}?{params}'

    @api.constrains("payment_provider", "journal_id", "company_id")
    def _check_bancontact_currency(self):
        """Ensure Bancontact Pay methods are linked to a supported journal currency."""
        for record in self:
            if record.payment_provider != "bancontact_pay":
                continue

            currency = record.journal_id.currency_id or record.company_id.currency_id
            if currency.name not in const.SUPPORTED_CURRENCIES:
                raise ValidationError(
                    _(
                        "Bancontact Pay only supports these currencies: %(currencies)s.\n"
                        "The linked journal uses a different currency.",
                        currencies=", ".join(const.SUPPORTED_CURRENCIES),
                    ),
                )

    @api.constrains("payment_provider", "bancontact_usage", "config_ids")
    def _check_bancontact_sticker_one_pos_config(self):
        """Restrict Bancontact sticker methods to a single PoS configuration."""
        for record in self:
            if (
                record.payment_provider == "bancontact_pay"
                and record.bancontact_usage == "sticker"
                and len(record.config_ids) > 1
            ):
                raise ValidationError(_("One Bancontact Pay sticker payment method can only be linked to one POS configuration."))

    def download_bancontact_sticker(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.bancontact_sticker_url,
            "target": "download",
        }

    # ----- Bancontact Integration ----- #
    def create_bancontact_payment(self, data):
        self.ensure_one()
        if self.payment_provider != "bancontact_pay":
            raise ValidationError(_("Bancontact payments can only be created for payment methods using Bancontact Pay as provider."))

        headers = {
            "Authorization": f"Bearer {self.bancontact_api_key}",
            "Content-Type": "application/json",
        }
        url, payload = self._prepare_bancontact_payment_request(data)
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        self._assert_bancontact_http_success(response)
        bancontact_data = response.json()

        return {
            "bancontact_id": bancontact_data["paymentId"],
            "qr_code": bancontact_data.get("_links", {}).get("qrcode", {}).get("href", ""),
        }

    def cancel_bancontact_payment(self, bancontact_id):
        self.ensure_one()
        if self.payment_provider != "bancontact_pay":
            raise ValidationError(_("Bancontact payments can only be cancelled for payment methods using Bancontact Pay as provider."))

        url = f"{self._get_bancontact_api_url('merchant')}/v3/payments/{bancontact_id}"
        headers = {
            "Authorization": f"Bearer {self.bancontact_api_key}",
            "Content-Type": "application/json",
        }
        response = requests.delete(url, headers=headers, timeout=5)
        self._assert_bancontact_http_success(response,
            {422: (_("Unable to cancel payment. The payment may not be in a cancellable state."), ValidationError)},
        )

    # ----- Helpers ----- #
    def _get_callback_url(self, data):
        """Build the callback URL used by Bancontact Pay to notify payment status."""
        config_id = data.get("configId")
        url = f"{self.get_base_url()}/bancontact_pay/webhook?config_id={config_id}&ppid={self.bancontact_ppid}"
        if self.bancontact_test_mode:
            url += "&mode=test"
        return url

    def _prepare_bancontact_payment_request(self, data):
        """Prepare the endpoint and JSON payload for a Bancontact payment creation call."""
        if self.bancontact_usage == "sticker":
            return self._prepare_sticker_payment_request(data)
        return self._prepare_display_payment_request(data)

    def _prepare_display_payment_request(self, data):
        """Prepare the request data for a dynamic on-screen QR payment."""
        callback_url = self._get_callback_url(data)
        return [
            f"{self._get_bancontact_api_url('merchant')}/v3/payments",
            {
                "amount": round(data.get("amount", 0.0) * 100),
                "currency": data.get("currency", "EUR"),
                "description": data.get("description", "")[:140],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _prepare_sticker_payment_request(self, data):
        """Prepare the request data for a static sticker-based QR payment."""
        callback_url = self._get_callback_url(data)
        return [
            f"{self._get_bancontact_api_url('merchant')}/v3/payments/pos",
            {
                "amount": round(data.get("amount", 0.0) * 100),
                "currency": data.get("currency", "EUR"),
                "description": data.get("description", "")[:140],
                "posId": f'pm{self.id}'[:36],
                "shopId": f'pos{data.get("configId", "")}'[:36],
                "shopName": data.get("shopName", "")[:36],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _get_bancontact_api_url(self, target):
        """Return the Bancontact endpoint URL for the current environment."""
        environment = "preprod" if self.bancontact_test_mode else "production"
        return const.API_URLS[environment][target]

    def _assert_bancontact_http_success(self, response, extra_errors=None):
        errors = {**HTTP_ERRORS, **(extra_errors or {})}
        if response.status_code in errors:
            error_message, exception_class = errors[response.status_code]
            try:
                error_data = response.json()
            except JSONDecodeError:
                error_data = {}
            code = error_data.get("code", "")

            exception_msg = f"{error_message} (ERR: {response.status_code}"
            if code:
                exception_msg += f" - {code}"
            exception_msg += ")"
            raise exception_class(exception_msg)

        response.raise_for_status()
