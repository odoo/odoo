# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_payfast import const
from odoo.addons.payment_payfast.controllers.main import PayfastController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return Payfast-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        if self.provider_code != "payfast":
            return super()._get_specific_rendering_values(processing_values)

        payload = self._payfast_prepare_payment_request_payload()
        payload["signature"] = self.provider_id._payfast_generate_signature(payload)

        api_url = f"{self.provider_id._payfast_get_api_url()}/eng/process"
        return {"api_url": api_url, "http_method": "post", "url_params": payload}

    def _payfast_prepare_payment_request_payload(self):
        """Create the payload for the payment request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        payment_method_code = const.PAYMENT_METHODS_MAPPING.get(self.payment_method_code)

        base_url = self.get_base_url()
        return_url = urls.urljoin(base_url, PayfastController._return_url)
        cancel_url = urls.urljoin(base_url, PayfastController._cancel_url)
        notify_url = urls.urljoin(base_url, PayfastController._notify_url)

        payload = {
            "merchant_id": self.provider_id.payfast_merchant_id,
            "merchant_key": self.provider_id.payfast_merchant_key,
            "return_url": return_url,
            "cancel_url": cancel_url,
            "notify_url": notify_url,
            "name_first": partner_first_name or partner_last_name or "",
            "name_last": partner_last_name or "",
            "email_address": self.partner_email or "",
            "cell_number": self.partner_phone or "",
            "m_payment_id": self.reference,
            "amount": f"{self.amount:.2f}",
            "item_name": self.reference,
        }
        if payment_method_code:
            payload["payment_method"] = payment_method_code
        if self.tokenize:
            if not self.provider_id.payfast_passphrase:
                raise ValidationError(
                    self.env._(
                        "A Passphrase must be set on the Payfast provider to enable tokenized "
                        "payments."
                    )
                )
            payload["subscription_type"] = const.TOKENIZATION_SUBSCRIPTION_TYPE
        return payload

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "payfast":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("m_payment_id")

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "payfast":
            return super()._apply_updates(payment_data)

        # Store Payfast's own transaction id.
        self.provider_reference = payment_data.get("pf_payment_id")

        payment_status = payment_data.get("payment_status")
        if payment_status == "COMPLETE":
            self._set_done()
        elif payment_status == "CANCELLED":
            self._set_canceled()
        else:
            _logger.info(
                "Received data with unsupported payment status (%s) for transaction %s.",
                payment_status,
                self.reference,
            )
            self._set_error(
                self.env._("Received data with unsupported payment status: %s", payment_status)
            )

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != "payfast":
            return super()._extract_amount_data(payment_data)

        amount = float(payment_data.get("amount_gross", "0.0"))
        # Payfast only supports ZAR; the currency is not sent back in the notification.
        return {"amount": amount, "currency_code": "ZAR"}

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract token values from the payment data."""
        if self.provider_code != "payfast":
            return super()._extract_token_values(payment_data)

        token = payment_data.get("token")
        if not token:
            return {}
        return {"provider_ref": token, "payment_details": self.payment_method_id.name}

    def _send_payment_request(self):
        """Override of `payment` to charge a saved token on demand through Payfast."""
        if self.provider_code != "payfast":
            return super()._send_payment_request()

        token = self.token_id.provider_ref
        body = {
            "amount": payment_utils.to_minor_currency_units(self.amount, self.currency_id),
            "item_name": self.reference,
        }
        response = self.provider_id._send_api_request(
            "POST", f"subscriptions/{token}/adhoc", json=body
        )

        # The adhoc-charge endpoint confirms or rejects the charge synchronously in its response
        # (a non-2xx status, already turned into a `ValidationError` by `_send_api_request`, means
        # the charge was rejected); reaching this point means it was successful.
        # `amount_gross` must be included: `_validate_amount` re-derives the amount from this same
        # payload via `_extract_amount_data` and errors out (even reverting a `done` transaction)
        # if it comes back empty.
        self._record({
            "payment_status": "COMPLETE",
            "amount_gross": f"{self.amount:.2f}",
            "pf_payment_id": response.get("data", {}).get("pf_payment_id"),
        })
