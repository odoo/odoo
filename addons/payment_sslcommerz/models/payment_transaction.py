# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_sslcommerz import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # === BUSINESS METHODS - PRE-PROCESSING === #

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Override of `payment` to satisfy SSLCOMMERZ's reference length limit."""
        reference = super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )
        if provider_code != "sslcommerz" or len(reference) <= 30:
            return reference

        if not prefix:
            prefix = self.sudo()._compute_reference_prefix(separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(
            prefix=prefix, separator=separator, max_length=28
        )
        return super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return SSLCOMMERZ-specific rendering values."""
        if self.provider_code != "sslcommerz":
            return super()._get_specific_rendering_values(processing_values)

        payload = self._sslcommerz_prepare_session_payload()
        try:
            session_data = self._send_api_request(
                "POST", "/gwprocess/v4/api.php", data=payload, operation="create_session"
            )
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        return {"api_url": session_data["GatewayPageURL"], "http_method": "get"}

    def _sslcommerz_prepare_session_payload(self):
        """Create the payload for the hosted checkout session request."""
        self.ensure_one()

        def format_value(value, fallback="N/A", max_length=None):
            value = (value or "").strip() or fallback
            return value[:max_length] if max_length else value

        base_url = self.provider_id.get_base_url()
        return_url = urls.urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        payload = {
            "store_id": self.provider_id.sslcommerz_store_id,
            "store_passwd": self.provider_id.sslcommerz_store_passwd,
            "total_amount": f"{self.amount:.2f}",
            "currency": self.currency_id.name,
            "tran_id": self.reference,
            "success_url": return_url,
            "fail_url": return_url,
            "cancel_url": return_url,
            "ipn_url": urls.urljoin(base_url, const.IPN_ROUTE),
            "cus_name": format_value(self.partner_name, "Customer", 50),
            "cus_email": format_value(self.partner_email, "no-reply@example.com", 50),
            "cus_add1": format_value(self.partner_address, max_length=50),
            "cus_city": format_value(self.partner_city, max_length=50),
            "cus_postcode": format_value(self.partner_zip, max_length=30),
            "cus_country": format_value(self.partner_country_id.name, "Bangladesh", 50),
            "cus_phone": format_value(self.partner_phone, max_length=20),
            "shipping_method": "NO",
            "product_name": "Online Payment",
            "product_category": "general",
            "product_profile": "non-physical-goods",
        }
        if self.payment_method_code in const.PAYMENT_METHODS_MAPPING:
            payload["multi_card_name"] = const.PAYMENT_METHODS_MAPPING[self.payment_method_code]
        return payload

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "sslcommerz":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("tran_id")

    # === BUSINESS METHODS - PROCESSING === #

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "sslcommerz":
            return super()._apply_updates(payment_data)

        if bank_tran_id := payment_data.get("bank_tran_id"):
            self.provider_reference = bank_tran_id

        payment_method_code = (
            (payment_data.get("card_type") or "").split("-", maxsplit=1)[0].strip().lower()
        )
        payment_method = self.env["payment.method"]._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        status = payment_data.get("status")
        if status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        elif status in const.PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(
                self.env._(
                    "An error occurred during the processing of your payment"
                    " (status %(status)s: %(reason)s).",
                    status=status,
                    reason=payment_data.get("error") or payment_data.get("errorReason") or "",
                )
            )
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction %s.",
                status,
                self.reference,
            )
            self._set_error(self.env._("Unknown payment status: %s", status))

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "sslcommerz":
            return super()._extract_amount_data(payment_data)

        return {
            "amount": float(payment_data.get("currency_amount")),
            "currency_code": payment_data.get("currency_type"),
        }
