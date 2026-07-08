# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal import utils as paypal_utils

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    paypal_setup_token_ref = fields.Char(string="PayPal Setup Token ID")

    # See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNandPDTVariables/
    # this field has no use in Odoo except for debugging
    paypal_type = fields.Char(string="PayPal Transaction Type")

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to return the Paypal-specific processing values.

        This is used by the Card, Venmo, and PayPal Pay Later payment methods.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        is_card_validation = self.operation == "validation" and self.payment_method_code == "card"
        if self.provider_code != "paypal" or (
            self.operation != "online_direct" and not is_card_validation
        ):
            return super()._get_specific_processing_values(processing_values)

        try:
            if is_card_validation:
                setup_token_data = self._paypal_create_setup_token()
                self.paypal_setup_token_ref = setup_token_data["id"]
                return {"setup_token_id": self.paypal_setup_token_ref}

            order_data = self._paypal_create_order()
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        self.provider_reference = order_data["id"]
        return {"order_id": order_data["id"]}

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return the PayPal-specific rendering values.

        This is used by the PayPal payment method and alternative payment methods.

        Note: self.ensure_one() from `_get_processing_values`.

        :param dict processing_values: The generic and specific processing values of the
                                       transaction
        :return: The dict of provider-specific rendering values
        :rtype: dict
        """
        is_validation = self.operation == "validation"
        if self.provider_code != "paypal" or (is_validation and self.payment_method_code == "card"):
            return super()._get_specific_rendering_values(processing_values)

        try:
            if is_validation:
                setup_token_data = self._paypal_create_setup_token()
                self.paypal_setup_token_ref = setup_token_data["id"]
                candidate_api_url_data = setup_token_data["links"]
            else:
                if self.payment_method_code == "paypal":
                    payload = self._paypal_prepare_order_payload()
                else:
                    payload = self._paypal_prepare_apm_order_payload()
                order_data = self._paypal_create_order(payload=payload)
                self.provider_reference = order_data["id"]
                candidate_api_url_data = order_data["links"]
        except ValidationError as e:
            self._set_error(str(e))
            return {}

        action_rel = "approve" if is_validation else "payer-action"
        payer_action_url = next(
            link["href"] for link in candidate_api_url_data if link["rel"] == action_rel
        )
        return {
            "api_url": payer_action_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(payer_action_url),
        }

    def _paypal_create_setup_token(self):
        """Create a PayPal setup token to save a payment method without a payment.

        The setup token is temporary; it must be approved by the customer, then exchanged for a
        payment token in`_paypal_exchange_setup_token`.

        See https://developer.paypal.com/api/payment-tokens/v3/#setup-tokens_create.

        :return: The API response of the setup token creation
        :rtype: dict
        """
        return_url, cancel_url = self._paypal_build_return_urls()
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
        return self._send_api_request(
            "POST",
            "/v3/vault/setup-tokens",
            json=payload,
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope="setup_token_request"
            ),
        )

    def _send_payment_request(self):
        """Override of `payment` to charge a saved PayPal wallet or card by token."""
        if self.provider_code != "paypal":
            return super()._send_payment_request()

        response_content = self._paypal_create_order()
        self._record(paypal_utils.normalize_payment_data(response_content, has_capture_data=True))

    def _paypal_create_order(self, payload=None):
        """Create a PayPal order for the transaction and return the API response.

        :param dict payload: The payload to use for the order creation. If not provided, the
                             `_paypal_prepare_order_payload` method will be used.
        :return: The API response of the order creation
        :rtype: dict
        """
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
            "purchase_units": [self._paypal_prepare_purchase_units_payload(shipping_address_vals)],
            "payment_source": self._paypal_prepare_payment_source_payload(
                invoice_address_vals, has_shipping=bool(shipping_address_vals)
            ),
        }

    def _paypal_prepare_purchase_units_payload(self, shipping_address_vals):
        """Prepare the purchase unit of the create order request payload.

        :param dict shipping_address_vals: The formatted shipping address, if any
        :return: The purchase unit payload
        :rtype: dict
        """
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

    def _paypal_prepare_payment_source_payload(self, invoice_address_vals, has_shipping):
        """Prepare the payment source of the create order request payload.

        Card payments send the billing address and the verification requirements, while wallet
        payments configure the checkout experience on PayPal.

        :param dict invoice_address_vals: The formatted invoice address
        :param bool has_shipping: Whether a shipping address is sent with the order
        :return: The payment source payload
        :rtype: dict
        """
        return_url, cancel_url = self._paypal_build_return_urls()
        if self.payment_method_code == "card":
            return {
                "card": self._paypal_prepare_card_payment_source_payload(
                    return_url, cancel_url, invoice_address_vals
                )
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
                    "store_in_vault": "ON_SUCCESS",
                    "usage_type": "MERCHANT",
                    "customer_type": "CONSUMER",
                }
            }

        return payment_source

    def _paypal_prepare_card_payment_source_payload(
        self, return_url, cancel_url, invoice_address_vals
    ):
        """Prepare the card payment source of the create order request payload.

        :param str return_url: The URL to redirect the customer to after the payment
        :param str cancel_url: The URL to redirect the customer to after canceling the payment
        :param dict invoice_address_vals: The formatted invoice address
        :return: The card payment source payload
        :rtype: dict
        """
        card_data = {"experience_context": {"return_url": return_url, "cancel_url": cancel_url}}

        if self.token_id:
            card_data["vault_id"] = self.token_id.provider_ref
            card_data["stored_credential"] = {"usage": "SUBSEQUENT"}
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

        return card_data

    def _paypal_prepare_apm_order_payload(self):
        """Prepare the payload of the create order request for an alternative payment method.

        :return: The create order request payload
        :rtype: dict
        """
        return_url, cancel_url = self._paypal_build_return_urls()
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

    def _paypal_build_return_urls(self):
        base_url = self.get_base_url()
        params = urlencode({
            "reference": self.reference,
            "access_token": payment_utils.generate_access_token(self.reference),
        })
        return_url = f"{urls.urljoin(base_url, const.PAYMENT_RETURN_ROUTE)}?{params}"
        cancel_url = f"{urls.urljoin(base_url, const.PAYMENT_CANCEL_ROUTE)}?{params}"
        return return_url, cancel_url

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

        if payment_data.get("event_type") in const.VAULT_WEBHOOK_EVENTS:
            return  # Vault notifications carry no payment state; only the token is created

        # Update the provider reference.
        txn_id = payment_data.get("id")
        txn_type = payment_data.get("txn_type")

        self.provider_reference = txn_id
        self.paypal_type = txn_type

        # Update the payment method
        # TODO

        # Update the payment state.
        payment_status = payment_data.get("status")

        if payment_status in const.PAYMENT_STATUS_MAPPING["pending"]:
            self._set_pending(state_message=payment_data.get("pending_reason"))
        elif payment_status in const.PAYMENT_STATUS_MAPPING["done"]:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING["cancel"]:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING["error"]:
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

        if payment_data.get("event_type") in const.VAULT_WEBHOOK_EVENTS:
            return None  # Vault notifications carry no payment state; only the token is created

        amount_data = payment_data.get("amount", {})
        amount = amount_data.get("value")
        currency_code = amount_data.get("currency_code")
        return {"amount": float(amount), "currency_code": currency_code}

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != "paypal":
            return super()._extract_token_values(payment_data)

        vault_data = (
            payment_data
            .get("payment_source", {})
            .get(self.payment_method_code, {})
            .get("attributes", {})
            .get("vault", {})
        )
        if vault_data.get("status") == "APPROVED":
            _logger.info(
                "Deferred vaulting of the payment source for transaction %s.", self.reference
            )
            return {}

        vault_id = vault_data.get("id")
        if not vault_id:
            _logger.warning("Tried to tokenize with missing vault_id: %s", vault_id)
            return {}

        payment_source = payment_data.get("payment_source", {}).get(self.payment_method_code, {})
        return {
            "provider_ref": vault_id,
            "payment_details": (
                payment_source.get("last_digits")
                or payment_source.get("name", {}).get("given_name")
                or payment_source.get("email_address")
            ),
        }
