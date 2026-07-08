# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import utils as paypal_utils
from odoo.addons.payment_paypal.const import PAYMENT_STATUS_MAPPING, VAULT_WEBHOOK_EVENTS
from odoo.addons.payment_paypal.controllers.main import PaypalController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    paypal_customer_id = fields.Char(string="PayPal Customer ID")

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to return the Paypal-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        is_card_validation = self.operation == "validation" and self.payment_method_code == "card"
        if (
            self.provider_code != "paypal"
            or (self.operation != "online_direct" and not is_card_validation)
        ):
            return super()._get_specific_processing_values(processing_values)

        try:
            if is_card_validation:
                setup_token_data = self._paypal_create_setup_token()
                self.provider_reference = setup_token_data["id"]
                return {"setup_token_id": setup_token_data["id"]}

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
        is_validation = self.operation == "validation"
        if self.provider_code != "paypal" or (is_validation and self.payment_method_code == "card"):
            return super()._get_specific_rendering_values(processing_values)

        try:
            if is_validation:
                order_data = self._paypal_create_setup_token()
            else:
                payload = (
                    self._paypal_prepare_order_payload()
                    if self.payment_method_code == "paypal"
                    else self._paypal_prepare_apm_order_payload()
                )
                order_data = self._paypal_create_order(payload=payload)
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        self.provider_reference = order_data["id"]
        action_rel = "approve" if is_validation else "payer-action"
        payer_action_url = next(
            link["href"] for link in order_data["links"] if link["rel"] == action_rel
        )
        return {
            "api_url": payer_action_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(payer_action_url),
        }

    def _send_payment_request(self):
        """Override of `payment` to charge a saved PayPal wallet or card by token."""
        if self.provider_code != "paypal":
            return super()._send_payment_request()

        response_content = self._paypal_create_order()
        self._record(
            paypal_utils.normalize_paypal_payment_data(response_content, has_capture_data=True)
        )

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

    def _paypal_create_setup_token(self):
        """Create a PayPal setup token to save a payment method without a payment.

        The setup token is temporary; it must be approved by the customer, then exchanged for a
        payment token in`_paypal_create_payment_token`.

        See https://developer.paypal.com/api/payment-tokens/v3/#setup-tokens_create.
        """
        return_url, cancel_url = self._paypal_get_return_urls(self.reference)
        experience_context = {
            "brand_name": self.provider_id.company_id.name,
            "return_url": return_url,
            "cancel_url": cancel_url,
        }
        if self.payment_method_code == "card":
            payload = {
                "payment_source": {
                    "card": {
                        "verification_method": "SCA_WHEN_REQUIRED",
                        "experience_context": experience_context,
                    }
                }
            }
        else:
            payload = {
                "payment_source": {
                    "paypal": {
                        "permit_multiple_payment_tokens": False,
                        "usage_type": "MERCHANT",
                        "customer_type": "CONSUMER",
                        "experience_context": {
                            **experience_context,
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                            "shipping_preference": "NO_SHIPPING",
                        },
                    }
                }
            }
        if customer_id := self._paypal_get_customer_id():
            payload["customer"] = {"id": customer_id}  # Link the token to the existing customer.
        return self._send_api_request(
            "POST",
            "/v3/vault/setup-tokens",
            json=payload,
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope="setup_token_request"
            ),
        )

    def _paypal_create_payment_token(self):
        """Exchange the approved setup token for a payment token and record it on the transaction.

        See https://developer.paypal.com/api/payment-tokens/v3/#payment-tokens_create.

        :return: None
        """
        vault = self._send_api_request(
            "POST",
            "/v3/vault/payment-tokens",
            json={
                "payment_source": {"token": {"id": self.provider_reference, "type": "SETUP_TOKEN"}}
            },
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope="payment_token_request"
            ),
        )
        self._record({
            "id": vault["id"],
            "status": "COMPLETED",
            "payment_source": paypal_utils.format_vault_payment_source(
                vault, self.payment_method_code
            ),
        })

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
                "card": self._paypal_add_card_data(return_url, cancel_url, invoice_address_vals)
            }
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)

        payment_source = {
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
        if self.token_id:
            payment_source["paypal"]["vault_id"] = self.token_id.provider_ref
            if self.operation == "offline":
                payment_source["paypal"]["stored_credential"] = {
                    "payment_initiator": "MERCHANT",
                    "usage": "SUBSEQUENT",
                }
        elif self.tokenize:
            payment_source["paypal"]["attributes"] = {
                "vault": {
                    "permit_multiple_payment_tokens": False,
                    "store_in_vault": "ON_SUCCESS",
                    "usage_type": "MERCHANT",
                    "customer_type": "CONSUMER",
                 }
            }
            if customer_id := self._paypal_get_customer_id():
                payment_source["paypal"]["attributes"]["customer"] = {"id": customer_id}

        return payment_source

    def _paypal_get_customer_id(self):
        existing_token = (
            self
            .env["payment.token"]
            .sudo()
            .search(
                [
                    ("provider_id", "=", self.provider_id.id),
                    ("partner_id", "=", self.partner_id.id),
                    ("paypal_customer_id", "!=", False),
                ],
                limit=1,
            )
        )
        return existing_token.paypal_customer_id

    def _paypal_add_card_data(self, return_url, cancel_url, invoice_address_vals):
        card_data = {"experience_context": {"return_url": return_url, "cancel_url": cancel_url}}

        if self.token_id:
            card_data["vault_id"] = self.token_id.provider_ref
            card_data["stored_credential"] = {
                "usage": "SUBSEQUENT"
            }
            if self.operation == "offline":
                card_data["stored_credential"].update({
                    "payment_initiator": "MERCHANT",
                    "payment_type": "UNSCHEDULED",
                })
            else:
                card_data["attributes"] = {"verification": {"method": "SCA_WHEN_REQUIRED"}}
                card_data["stored_credential"].update({
                    "payment_initiator": "CUSTOMER",
                    "payment_type": "ONE_TIME",
                })
            return card_data

        card_data["name"] = self.partner_name
        card_data["billing_address"] = invoice_address_vals.get("address", {})
        card_data["attributes"] = {"verification": {"method": "SCA_WHEN_REQUIRED"}}

        if self.tokenize:
            card_data["stored_credential"] = {
                "payment_initiator": "CUSTOMER",
                "payment_type": "ONE_TIME",
                "usage": "FIRST",
            }
            card_data["attributes"]["vault"] = {"store_in_vault": "ON_SUCCESS"}
            if customer_id := self._paypal_get_customer_id():
                card_data["attributes"]["customer"] = {"id": customer_id}

        return card_data

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

        if payment_data.get("event_type") in VAULT_WEBHOOK_EVENTS:
            return  # Vault notifications carry no payment state; only the token is created.

        # Update the provider reference.
        txn_id = payment_data.get("id")
        if not all(txn_id):
            self._set_error(self.env._("Missing value for txn_id (%(txn_id)s).", txn_id=txn_id))
            return

        self.provider_reference = txn_id
        self.payment_method_id = (
            self.payment_method_id or self.provider_id._get_pm_from_code("paypal")
        )

        if self.tokenize and not self.token_id:
            customer_id = self._paypal_get_vault(payment_data).get("customer", {}).get("id")
            if customer_id:
                self.paypal_customer_id = customer_id

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

        if payment_data.get("event_type") in VAULT_WEBHOOK_EVENTS:
            return None  # Vault notifications carry no payment state; only the token is created.

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

    def _paypal_get_vault(self, payment_data):
        """Return the `attributes.vault` section of the payment source in the payment data.

        :param dict payment_data: The payment data sent by the provider.
        :return: The vault data, or an empty dict if absent.
        :rtype: dict
        """
        return (
            payment_data
            .get("payment_source", {})
            .get(self.payment_method_code, {})
            .get("attributes", {})
            .get("vault", {})
        )

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != "paypal":
            return super()._extract_token_values(payment_data)

        vault = self._paypal_get_vault(payment_data)

        if vault.get("status") == "APPROVED":
            _logger.info(
                "Deferred vaulting of the payment source for transaction %s.", self.reference
            )
            return {}

        customer_id = vault.get("customer", {}).get("id")
        vault_id = vault.get("id")
        if not customer_id or not vault_id:
            _logger.warning(
                "Tried to tokenize with missing customer_id (%s) or vault_id (%s)",
                customer_id,
                vault_id,
            )
            return {}

        payment_source = payment_data.get("payment_source", {}).get(self.payment_method_code, {})
        return {
            "provider_ref": vault_id,
            "paypal_customer_id": customer_id,
            "payment_details": (
                payment_source.get("last_digits")
                or payment_source.get("name", {}).get("given_name")
                or payment_source.get("email_address")
            ),
        }
