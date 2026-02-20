from urllib.parse import urlencode

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.errors.http import assert_bancontact_http_success


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # ----- Fields ----- #
    def _get_external_qr_provider_selection(self):
        return super()._get_external_qr_provider_selection() + [("bancontact_pay", "Bancontact Pay")]

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
    def create_bancontact_payment(self, **kwargs):
        """Create (or reuse) a Bancontact Pay payment and return updated PoS payment data."""
        payment_id = kwargs.get("payment_id")
        pos_payment = self.env["pos.payment"].search([("id", "=", payment_id)], limit=1)

        if not pos_payment.exists():
            raise ValidationError(_("Bancontact payment not found."))

        if not pos_payment.bancontact_id or pos_payment.payment_status not in ["waiting", "waitingScan", "waitingCancel"]:
            headers = {
                "Authorization": f"Bearer {self.bancontact_api_key}",
                "Content-Type": "application/json",
            }
            url, payload = self._prepare_bancontact_payment_request(**kwargs)
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            assert_bancontact_http_success(response)
            bancontact_data = response.json()

            pos_payment.bancontact_id = bancontact_data["paymentId"]
            pos_payment.qr_code = bancontact_data.get("_links", {}).get("qrcode", {}).get("href", "")

        return {
            "pos.payment": pos_payment._load_pos_data_read(
                pos_payment,
                pos_payment.pos_order_id.config_id,
            ),
        }

    def cancel_bancontact_payment(self, **kwargs):
        """Cancel a Bancontact Pay payment when possible and return updated PoS payment data."""
        payment_id = kwargs.get("payment_id")
        pos_payment = self.env["pos.payment"].search([("id", "=", payment_id)], limit=1)
        if not pos_payment.exists():
            raise ValidationError(_("Bancontact payment not found."))

        bancontact_id = pos_payment.bancontact_id
        if bancontact_id:
            url = f"{self._get_bancontact_api_url('merchant')}/v3/payments/{bancontact_id}"
            headers = {
                "Authorization": f"Bearer {self.bancontact_api_key}",
                "Content-Type": "application/json",
            }
            response = requests.delete(url, headers=headers, timeout=5)
            assert_bancontact_http_success(response,
                {422: (_("Unable to cancel payment. The payment may not be in a cancellable state."), ValidationError)},
            )

            pos_payment.bancontact_id = False
            pos_payment.qr_code = False

        return {
            "pos.payment": pos_payment._load_pos_data_read(
                pos_payment,
                pos_payment.pos_order_id.config_id,
            ),
        }

    # ----- Helpers ----- #
    def _get_callback_url(self):
        """Build the callback URL used by Bancontact Pay to notify payment status."""
        url = f"{self.get_base_url()}/bancontact_pay/webhook"
        if self.bancontact_test_mode:
            url += "?mode=test"
        return url

    def _prepare_bancontact_payment_request(self, **kwargs):
        """Prepare the endpoint and JSON payload for a Bancontact payment creation call."""
        usage = kwargs.get("usage")
        if usage == "sticker":
            return self._prepare_sticker_payment_request(**kwargs)
        return self._prepare_display_payment_request(**kwargs)

    def _prepare_display_payment_request(self, **kwargs):
        """Prepare the request data for a dynamic on-screen QR payment."""
        callback_url = self._get_callback_url()
        return [
            f"{self._get_bancontact_api_url('merchant')}/v3/payments",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _prepare_sticker_payment_request(self, **kwargs):
        """Prepare the request data for a static sticker-based QR payment."""
        callback_url = self._get_callback_url()
        return [
            f"{self._get_bancontact_api_url('merchant')}/v3/payments/pos",
            {
                "amount": round(kwargs.get("amount", 0.0) * 100),
                "currency": kwargs.get("currency", "EUR"),
                "description": kwargs.get("description", "")[:140],
                "posId": f'pm{kwargs.get("paymentMethodId", "")}'[:36],
                "shopId": f'pos{kwargs.get("posId", "")}'[:36],
                "shopName": kwargs.get("shopName", "")[:36],
                "identifyCallbackUrl": callback_url,
                "callbackUrl": callback_url,
            },
        ]

    def _get_bancontact_api_url(self, target):
        """Return the Bancontact endpoint URL for the current environment."""
        environment = "preprod" if self.bancontact_test_mode else "production"
        return const.API_URLS[environment][target]
