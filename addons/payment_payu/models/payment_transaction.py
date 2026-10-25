# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_payu import const

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return PayU-specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "payu":
            return res

        base_url = self.provider_id.get_base_url()
        return_url = urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        webhook_url = urljoin(base_url, const.WEBHOOK_ROUTE)
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        payload = {
            "key": self.provider_id.payu_key_id,
            "txnid": self.reference,
            "amount": str(self.amount),  # Despite the docs, PayU expects a string.
            "productinfo": "Odoo Payment",
            "firstname": first_name,
            "lastname": last_name,
            "email": self.partner_email or "",
            "phone": self.partner_phone or "",
            "surl": return_url,
            "furl": return_url,
            "partner_webhook_success": webhook_url,
            "partner_webhook_failure": webhook_url,
            "enforce_paymethod": const.PAYMENT_METHODS_MAPPING.get(self.payment_method_code, ""),
        }
        payload["hash"] = self.provider_id._payu_generate_signature(payload)

        return {"api_url": self.provider_id._build_request_url("_payment"), "url_params": payload}

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "payu":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("txnid")

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "payu":
            return super()._extract_amount_data(payment_data)

        # PayU does not include the currency in the callback payload. Fall back to the transaction
        # currency, which effectively disables the currency validation while still allowing the
        # amount to be verified.
        return {"amount": float(payment_data.get("amount")), "currency_code": self.currency_id.name}

    def _apply_updates(self, payment_data):
        """Override of `payment' to update the transaction based on the payment data."""
        if self.provider_code != "payu":
            return super()._apply_updates(payment_data)

        # Update the provider reference
        self.provider_reference = payment_data.get("mihpayid")

        # Update the payment method
        payment_method_code = payment_data.get("mode")

        if payment_method_code in ("CC", "DC"):
            payment_method_code = "card"

        payment_method = self.env["payment.method"]._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_RESPONSE_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state
        status = payment_data["status"]
        if status in const.PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(
                self.env._(
                    "%(code)s: %(explanation)s",
                    code=status,
                    explanation=payment_data.get("error_Message"),
                )
            )
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s",
                status,
                self.reference,
            )
            self._set_error(self.env._("Unknown status code: %s", status))
