from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.integration.tools.admission import Acknowledged
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal import utils as paypal_utils
from odoo.addons.payment_paypal.const import PAYMENT_STATUS_MAPPING

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _receiver_for_paypal_webhook(self, **path_args):
        data = request.get_json_data()
        if data.get("event_type") not in const.HANDLED_WEBHOOK_EVENTS:
            raise Acknowledged.json("")
        normalized_data = self._normalize_paypal_data(
            data.get("resource"), from_webhook=True
        )
        return self._resolve_notification(
            "paypal", normalized_data, Acknowledged.json("")
        )

    def _verify_inbound_request(self, headers, body):
        if self.provider_code != "paypal":
            return super()._verify_inbound_request(headers, body)
        # See https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature_post.
        data = {
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
            "cert_url": headers.get("PAYPAL-CERT-URL"),
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "webhook_id": self.provider_id.paypal_webhook_id,
            "webhook_event": request.get_json_data(),
        }
        try:
            verification = self._send_api_request(
                "POST", "/v1/notifications/verify-webhook-signature", json=data
            )
        except ValidationError:
            # PayPal could not be asked: the transaction records the failure
            # and the notification is still processed, as before.
            self._set_error(self.env._("Unable to verify the payment data"))
            return True
        if verification.get("verification_status") != "SUCCESS":
            _logger.warning("Received payment data that was not verified by PayPal.")
            return False
        return True

    @api.model
    def _normalize_paypal_data(self, data, from_webhook=False):
        """One shape for the payment request's response and the webhook's resource."""
        purchase_unit = data["purchase_units"][0]
        result = {
            "payment_source": data["payment_source"].keys(),
            "reference_id": purchase_unit.get("reference_id"),
        }
        if from_webhook:
            result.update(
                {
                    **purchase_unit,
                    "txn_type": data.get("intent"),
                    "id": data.get("id"),
                    "status": data.get("status"),
                }
            )
        elif captured := purchase_unit.get("payments", {}).get("captures"):
            result.update({**captured[0], "txn_type": "CAPTURE"})
        else:
            _logger.warning(self.env._("Invalid response format, can't normalize."))
        return result

    # See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNandPDTVariables/
    # this field has no use in Odoo except for debugging
    paypal_type = fields.Char(string="PayPal Transaction Type")

    def _prepare_provider_processing_values(self, processing_values):
        """Override of `payment` to return the Paypal-specific processing values.

        Note: self.check_singleton() from `_prepare_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != "paypal":
            return super()._prepare_provider_processing_values(processing_values)

        payload = self._paypal_prepare_order_payload()

        idempotency_key = payment_utils.generate_idempotency_key(
            self, scope="payment_request_order"
        )
        try:
            order_data = self._send_api_request(
                "POST",
                "/v2/checkout/orders",
                json=payload,
                idempotency_key=idempotency_key,
            )
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        return {"order_id": order_data["id"]}

    def _paypal_prepare_order_payload(self):
        """Prepare the payload for the Paypal create order request.

        :return: The requested payload to create a Paypal order.
        :rtype: dict
        """
        partner_first_name, partner_last_name = payment_utils.split_partner_name(
            self.partner_name
        )
        if self.partner_id.is_public:
            invoice_address_vals = {
                "address": {"country_code": self.company_id.country_code}
            }
            shipping_address_vals = {}
        else:
            invoice_address_vals = paypal_utils.format_partner_address(self.partner_id)
            shipping_address_vals = paypal_utils.format_shipping_address(self)
        shipping_preference = (
            "SET_PROVIDED_ADDRESS" if shipping_address_vals else "NO_SHIPPING"
        )

        # See https://developer.paypal.com/docs/api/orders/v2/#orders_create!ct=application/json
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": self.reference,
                    "description": f"{self.company_id.name}: {self.reference}",
                    "amount": {
                        "currency_code": self.currency_id.name,
                        "value": self.amount,
                    },
                    "payee": {
                        "display_data": {
                            "brand_name": self.provider_id.company_id.name,
                        },
                        "email_address": self.provider_id.paypal_email_account,
                    },
                    **shipping_address_vals,
                },
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "shipping_preference": shipping_preference,
                    },
                    "name": {
                        "given_name": partner_first_name,
                        "surname": partner_last_name,
                    },
                    **invoice_address_vals,
                },
            },
        }
        # PayPal does not accept None set to fields and to avoid users getting errors when email
        # is not set on company we will add it conditionally since its not a required field.
        if company_email := self.provider_id.company_id.email:
            payload["purchase_units"][0]["payee"]["display_data"]["business_email"] = (
                company_email
            )

        return payload

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "paypal":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("reference_id")

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != "paypal":
            return super()._extract_amount_data(payment_data)

        amount_data = payment_data.get("amount", {})
        amount = amount_data.get("value")
        currency_code = amount_data.get("currency_code")
        return {
            "amount": float(amount),
            "currency_code": currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "paypal":
            return super()._apply_updates(payment_data)

        if not payment_data:
            self._set_canceled(
                state_message=self.env._("The customer left the payment page.")
            )
            return None

        # Update the provider reference.
        txn_id = payment_data.get("id")
        txn_type = payment_data.get("txn_type")
        if not all((txn_id, txn_type)):
            self._set_error(
                self.env._(
                    "Missing value for txn_id (%(txn_id)s) or txn_type (%(txn_type)s).",
                    txn_id=txn_id,
                    txn_type=txn_type,
                )
            )
            return None
        self.provider_reference = txn_id
        self.paypal_type = txn_type

        # Force PayPal as the payment method if it exists.
        self.payment_method_id = (
            self.env["payment.method"].search([("code", "=", "paypal")], limit=1)
            or self.payment_method_id
        )

        # Update the payment state.
        payment_status = payment_data.get("status")

        if payment_status in PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending(state_message=payment_data.get("pending_reason"))
        elif payment_status in PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        else:
            _logger.info(
                "Received data with invalid payment status (%s) for transaction %s.",
                payment_status,
                self.reference,
            )
            self._set_error(
                self.env._(
                    "Received data with invalid payment status: %s", payment_status
                )
            )
        return None
