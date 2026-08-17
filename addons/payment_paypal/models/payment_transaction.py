# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import utils as paypal_utils
from odoo.addons.payment_paypal.const import PAYMENT_STATUS_MAPPING
from odoo.addons.payment_paypal.controllers.main import PaypalController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to return the Paypal-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != "paypal" or self.operation != "online_direct":
            return super()._get_specific_processing_values(processing_values)

        try:
            order_data = self._paypal_create_order()
            self.provider_reference = order_data["id"]
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        return {"order_id": order_data["id"]}

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return the PayPal-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        if self.provider_code != "paypal":
            return super()._get_specific_rendering_values(processing_values)

        payload = (
            self._paypal_prepare_order_payload()
            if self.payment_method_code == "paypal"
            else self._paypal_prepare_apm_order_payload()
        )
        try:
            order_data = self._paypal_create_order(payload=payload)
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        self.provider_reference = order_data["id"]
        payer_action_url = next(
            link["href"] for link in order_data["links"] if link["rel"] == "payer-action"
        )
        return {
            "api_url": payer_action_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(payer_action_url),
        }

    def _paypal_create_order(self, payload=None):
        """Create a PayPal order for the transaction and return the API response."""
        idempotency_key = payment_utils.generate_idempotency_key(
            self, scope="payment_request_order"
        )
        return self._send_api_request(
            "POST",
            "/v2/checkout/orders",
            json=payload if payload else self._paypal_prepare_order_payload(),
            idempotency_key=idempotency_key,
        )

    def _paypal_prepare_order_payload(self):
        """Prepare the payload for the Paypal create order request.

        :return: The requested payload to create a Paypal order.
        :rtype: dict
        """
        if self.partner_id.is_public:
            invoice_address_vals = {"address": {"country_code": self.company_id.country_code}}
            shipping_address_vals = {}
        else:
            invoice_address_vals = paypal_utils.format_partner_address(self.partner_id)
            shipping_address_vals = paypal_utils.format_shipping_address(self)

        # See https://developer.paypal.com/docs/api/orders/v2/#orders_create!ct=application/json
        return {
            "intent": "CAPTURE",
            "purchase_units": [self._paypal_get_purchase_unit(shipping_address_vals)],
            "payment_source": self._paypal_get_payment_source(
                invoice_address_vals, has_shipping=bool(shipping_address_vals)
            ),
        }

    def _paypal_get_purchase_unit(self, shipping_address_vals):
        payee_data = {
            "display_data": {"brand_name": self.provider_id.company_id.name},
            "email_address": self.provider_id.paypal_email_account,
        }

        if company_email := self.provider_id.company_id.email:
            payee_data["display_data"]["business_email"] = company_email

        return {
            "reference_id": self.reference,
            "description": f"{self.company_id.name}: {self.reference}",
            "amount": {"currency_code": self.currency_id.name, "value": str(self.amount)},
            "payee": payee_data,
            **shipping_address_vals,
        }

    def _paypal_get_payment_source(self, invoice_address_vals, has_shipping):
        return_url, cancel_url = self._paypal_get_return_urls(self.reference)
        if self.payment_method_code == "card":
            return {
                "card": {
                    "name": self.partner_name,
                    "billing_address": invoice_address_vals.get("address", {}),
                    "attributes": {"verification": {"method": "SCA_WHEN_REQUIRED"}},
                    "experience_context": {"return_url": return_url, "cancel_url": cancel_url},
                }
            }
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        return {
            "paypal": {
                "experience_context": {
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "landing_page": "LOGIN",
                    "shipping_preference": (
                        "SET_PROVIDED_ADDRESS" if has_shipping else "NO_SHIPPING"
                    ),
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                },
                "name": {"given_name": partner_first_name, "surname": partner_last_name},
                **invoice_address_vals,
            }
        }

    def _paypal_prepare_apm_order_payload(self):
        """Prepare the payload of the create order request for an alternative payment method.

        :return: The payload of the create order request for the alternative payment method.
        :rtype: dict
        """
        return_url, cancel_url = self._paypal_get_return_urls(self.reference)
        locale = (self.partner_id.lang or self.env.user.lang or "en_US").replace("_", "-")
        return {
            "intent": "CAPTURE",
            "processing_instruction": "ORDER_COMPLETE_ON_PAYMENT_APPROVAL",
            "purchase_units": [
                {
                    "reference_id": self.reference,
                    "custom_id": self.reference,
                    "description": f"{self.company_id.name}: {self.reference}",
                    "amount": {"currency_code": self.currency_id.name, "value": str(self.amount)},
                }
            ],
            "payment_source": {
                self.payment_method_code: {
                    "country_code": self.partner_id.country_code or self.company_id.country_code,
                    "name": self.partner_name,
                    "email": self.partner_email,
                }
            },
            "application_context": {
                "locale": locale,
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "paypal":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("reference_id")

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "paypal":
            super()._apply_updates(payment_data)
            return

        if not payment_data:
            self._set_canceled(state_message=self.env._("The customer left the payment page."))
            return

        # Update the provider reference.
        txn_id = payment_data.get("id")
        if not all(txn_id):
            self._set_error(self.env._("Missing value for txn_id (%(txn_id)s).", txn_id=txn_id))
            return

        self.provider_reference = txn_id

        # Force PayPal as the payment method if it exists.
        self.payment_method_id = (
            self.payment_method_id or self.provider_id._get_pm_from_code("paypal")
        )

        # Update the payment state.
        payment_status = payment_data.get("status")

        if payment_status in PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending(state_message=payment_data.get("pending_reason"))
        elif payment_status in PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        elif payment_status in PAYMENT_STATUS_MAPPING["error"]:
            self._set_error(
                payment_data.get("state_message")
                or self.env._("The payment was declined by PayPal.")
            )
        else:
            _logger.info(
                "Received data with invalid payment status (%s) for transaction %s.",
                payment_status,
                self.reference,
            )
            self._set_error(
                self.env._("Received data with invalid payment status: %s", payment_status)
            )

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != "paypal":
            return super()._extract_amount_data(payment_data)

        amount_data = payment_data.get("amount", {})
        amount = amount_data.get("value")
        currency_code = amount_data.get("currency_code")
        return {"amount": float(amount), "currency_code": currency_code}

    def _paypal_get_return_urls(self, ref):
        base_url = self.provider_id._paypal_get_base_url()
        params = urlencode({"reference": ref})
        return_url = f"{urls.urljoin(base_url, PaypalController._return_url)}?{params}"
        cancel_url = f"{urls.urljoin(base_url, PaypalController._cancel_url)}?{params}"
        return return_url, cancel_url
