import hashlib
import hmac
import json

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import urls

from odoo.addons.integration.tools.admission import Acknowledged
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paymob import const
from odoo.addons.payment_paymob.controllers.main import PaymobController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _receiver_for_paymob_return(self, **path_args):
        return self._resolve_notification(
            "paymob",
            request.get_http_params(),
            Acknowledged.redirect("/payment/status"),
        )

    @api.model
    def _receiver_for_paymob_webhook(self, **path_args):
        payment_data = request.get_json_data().get("obj") or {}
        normalized_data = self._normalize_paymob_response(
            payment_data, request.get_http_params().get("hmac")
        )
        tx, extra = self._resolve_notification(
            "paymob", normalized_data, Acknowledged("")
        )
        if normalized_data["order"] != tx.provider_reference:
            # The order the notification names is not the transaction's own.
            raise Acknowledged("", 403)
        return tx, extra

    def _inbound_notification_data(self, headers, body):
        if self.provider_code != "paymob":
            return super()._inbound_notification_data(headers, body)
        params = request.get_http_params()
        if request.httprequest.method == "GET":
            return params
        return self._normalize_paymob_response(
            request.get_json_data().get("obj") or {}, params.get("hmac")
        )

    def _verify_notification_signature(self, payment_data):
        if self.provider_code != "paymob":
            return super()._verify_notification_signature(payment_data)
        received_signature = payment_data.get("hmac", "")
        if not received_signature:
            _logger.warning("Received payment data with missing signature.")
            return False
        expected_signature = self._compute_paymob_signature(
            payment_data, self.provider_id.paymob_hmac_key
        )
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Received payment data with invalid signature.")
            return False
        return True

    @staticmethod
    def _normalize_paymob_response(payment_data, hmac_sig):
        """Webhook data (parsed values) and redirect data (strings, JSON-formatted
        booleans) in one shape."""
        response = {}
        for field in const.SIGNATURE_FIELDS:
            if isinstance(payment_data.get(field), bool):
                response[field] = json.dumps(payment_data.get(field))
            else:
                response[field] = str(payment_data.get(field, "false"))
        order_data = payment_data.get("order", {})
        response.update(
            {
                "data.message": payment_data.get("data", {}).get("message"),
                "hmac": hmac_sig,
                "order": str(order_data.get("id")),
                "merchant_order_id": order_data.get("merchant_order_id"),
                "source_data.pan": payment_data.get("source_data", {}).get("pan"),
                "source_data.sub_type": payment_data.get("source_data", {}).get(
                    "sub_type"
                ),
                "source_data.type": payment_data.get("source_data", {}).get("type"),
            }
        )
        return response

    @staticmethod
    def _compute_paymob_signature(payload, hmac_key):
        # See https://developers.paymob.com/pak/manage-callback/hmac-calculation.
        signing_string = "".join(
            payload.get(field, "false") for field in const.SIGNATURE_FIELDS
        ).encode("utf-8")
        signed_hmac = hmac.new(hmac_key.encode("utf-8"), signing_string, hashlib.sha512)
        return signed_hmac.hexdigest()

    @api.model
    def _get_unique_reference(
        self, provider_code, prefix=None, separator="-", **kwargs
    ):
        """Override of `payment` to ensure that Paymob references are unique.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        if provider_code == "paymob":
            if not prefix:
                # If no prefix is provided, it could mean that a module has passed a kwarg intended
                # for the `_get_reference_prefix` method, as it is only called if the prefix is
                # empty. We call it manually here because singularizing the prefix would generate a
                # default value if it was empty, hence preventing the method from ever being called
                # and the transaction from receiving a reference named after the related document.
                prefix = self.sudo()._get_reference_prefix(separator, **kwargs) or None
            prefix = payment_utils.singularize_reference_prefix(
                prefix=prefix, separator=separator
            )

        return super()._get_unique_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _prepare_redirect_form_values(self, processing_values):
        """Override of `payment` to return Paymob-specific rendering values.

        Note: self.check_singleton() from `_prepare_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        if self.provider_code != "paymob":
            return super()._prepare_redirect_form_values(processing_values)

        payload = self._paymob_prepare_payment_request_payload()
        try:
            payment_data = self._send_api_request(
                "POST", "/v1/intention/", json=payload, is_client_request=True
            )
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        # The provider reference is set to allow fetching the payment status after redirection.
        self.provider_reference = payment_data.get("id")
        paymob_client_secret = payment_data.get("client_secret")

        paymob_url = self.provider_id._paymob_get_api_url()
        api_url = f"{paymob_url}/unifiedcheckout/"
        url_params = {
            "publicKey": self.provider_id.paymob_public_key,
            "clientSecret": paymob_client_secret,
        }
        return {"api_url": api_url, "url_params": url_params}

    def _paymob_prepare_payment_request_payload(self):
        """Create the payload for the payment request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        partner_first_name, partner_last_name = payment_utils.split_partner_name(
            self.partner_name
        )
        payment_method_codes = [self.payment_method_code]

        # If the user selects the Oman Net Payment Method to pay, Integration ID for both Card and
        # Oman Net Integrations should be passed in the Intention API. The transaction will fail if
        # you only pass Oman Net Integration ID.
        if self.payment_method_code == "omannet":
            payment_method_codes.append("card")

        # Suffix to all payment methods with the environment.
        environment = "live" if self.provider_id.state == "enabled" else "test"
        payment_method_codes = [
            f"{code.replace('_', '')}{environment}" for code in payment_method_codes
        ]

        base_url = self.get_base_url()
        redirect_url = urls.urljoin(base_url, PaymobController._return_url)
        webhook_url = urls.urljoin(base_url, PaymobController._webhook_url)

        return {
            "special_reference": self.reference,
            "amount": payment_utils.major_to_minor_currency_units(
                self.amount, self.currency_id
            ),
            "currency": self.currency_id.name,
            "payment_methods": payment_method_codes,
            "notification_url": webhook_url,
            "redirection_url": redirect_url,
            "billing_data": {
                "first_name": partner_first_name or partner_last_name or "",
                "last_name": partner_last_name or "",
                "email": self.partner_email or "",
                "street": self.partner_address or "",
                "state": self.partner_state_id.name or "",
                "phone_number": (self.partner_phone or "").replace(" ", ""),
                "country": self.partner_country_id.code or "",
            },
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "paymob":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("merchant_order_id")

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != "paymob":
            return super()._extract_amount_data(payment_data)

        amount_cents = float(payment_data.get("amount_cents"))
        amount = payment_utils.minor_to_major_currency_units(
            amount_cents, self.currency_id
        )
        currency_code = payment_data.get("currency")
        return {
            "amount": amount,
            "currency_code": currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "paymob":
            return super()._apply_updates(payment_data)

        # Update the payment state.
        if payment_data.get("pending") == "true":
            self._set_pending()
        elif payment_data.get("success") == "true":
            self._set_done()
        else:
            _logger.info(
                "Received data with unsuccessful payment status for transaction %s.",
                self.reference,
            )
            message = payment_data.get("data.message")
            self._set_error(
                self.env._(
                    "An error occurred during the processing of your payment (%(msg)s). Please try"
                    " again.",
                    msg=message,
                )
            )
        return None
