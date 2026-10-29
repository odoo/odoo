# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paypal import utils as paypal_utils
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PaypalCommon):
    def test_no_item_missing_from_processing_values(self):
        tx = self._create_transaction(flow="direct")
        with (
            self._mock_send_api_request(return_value={"id": self.order_id}),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            processing_values = tx._get_processing_values()
        self.assertEqual(processing_values["order_id"], self.order_id)

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendering values of an alternative payment method redirect the customer
        to the PayPal payer action URL."""
        bancontact_pm = self.env.ref("payment_paypal.payment_method_bancontact").id
        tx = self._create_transaction(flow="redirect", payment_method_id=bancontact_pm)
        with (
            self._mock_send_api_request(return_value=self.apm_order_data),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            rendering_values = tx.with_context(
                payment_safe_write=True
            )._get_specific_rendering_values(None)
        self.assertDictEqual(
            rendering_values,
            {
                "api_url": self.payer_action_url,
                "http_method": "get",
                "url_params": {"token": self.order_id},
            },
        )

    def test_rendering_values_save_order_id_as_provider_reference(self):
        """Test that the id of the created order is saved as the provider reference."""
        bancontact_pm = self.env.ref("payment_paypal.payment_method_bancontact").id
        tx = self._create_transaction(flow="redirect", payment_method_id=bancontact_pm)
        with (
            self._mock_send_api_request(return_value=self.apm_order_data),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            tx.with_context(payment_safe_write=True)._get_specific_rendering_values(None)
        self.assertEqual(tx.provider_reference, self.order_id)

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` and `url_params` keys are not omitted from the rendering
        values."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_paypal.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={
                "api_url": "https://dummy.com",
                "http_method": "get",
                "url_params": {"token": self.order_id},
            },
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {"token": self.order_id})

    def test_send_payment_request_records_capture_data(self):
        """Test that a token payment records the payment data normalized from the capture embedded
        in the created order, as the amount and the final status live on the capture."""
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        token = self._create_token(payment_method_id=paypal_pm, provider_ref="VAULT-TOKEN-1")
        tx = self._create_transaction("token", payment_method_id=paypal_pm, token_id=token.id)
        with (
            self._mock_send_api_request(return_value=self.completed_order),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            tx._send_payment_request()
        payment_data = self.env["payment.data"].search([("transaction_id", "=", tx.id)])
        self.assertEqual(
            payment_data.payload["amount"],
            {"currency_code": self.currency.name, "value": str(self.amount)},
        )

    def test_no_item_missing_from_order_request_payload(self):
        """Test that the request values are conform to the transaction fields for a standard
        transaction (not the public partner, no shipping address)."""
        tx = self._create_transaction(flow="direct")
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            request_payload = tx._paypal_prepare_order_payload()
            return_url, cancel_url = tx._paypal_build_return_urls()
        self.maxDiff = 10000  # Allow comparing large dicts.

        partner_first_name, partner_last_name = payment_utils.split_partner_name(tx.partner_name)
        expected_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": tx.reference,
                    "description": f"{tx.company_id.name}: {tx.reference}",
                    "amount": {"currency_code": tx.currency_id.name, "value": str(tx.amount)},
                    "payee": {
                        "display_data": {"brand_name": tx.provider_id.company_id.name},
                        "email_address": tx.provider_id.paypal_email_account,
                    },
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    },
                    "name": {"given_name": partner_first_name, "surname": partner_last_name},
                    "email_address": tx.partner_id.email,
                    "address": {
                        "address_line_1": tx.partner_id.street,
                        "address_line_2": tx.partner_id.street2,
                        "postal_code": tx.partner_id.zip,
                        "admin_area_2": tx.partner_id.city,
                        "country_code": tx.partner_id.country_code,
                    },
                }
            },
        }
        if company_email := tx.provider_id.company_id.email:
            expected_payload["purchase_units"][0]["payee"]["display_data"]["business_email"] = (
                company_email
            )
        self.assertDictEqual(request_payload, expected_payload)

    def test_order_payload_values_for_public_user(self):
        """If a payment is made with the public user we need to make sure that the email address is
        not sent to PayPal and that we provide the country code of the company instead."""
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        tx = self._create_transaction(
            flow="direct", partner_id=self.public_user.partner_id.id, payment_method_id=paypal_pm
        )
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            payload = tx._paypal_prepare_order_payload()
        customer_payload = payload["payment_source"]["paypal"]
        self.assertTrue("email_address" not in customer_payload)
        self.assertEqual(customer_payload["address"]["country_code"], self.company.country_id.code)

    def test_order_payload_omits_stored_credential_for_token_payments(self):
        """Test that a customer-present token payment doesn't send stored credentials."""
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        token = self._create_token(payment_method_id=paypal_pm, provider_ref="VAULT-TOKEN-1")
        tx = self._create_transaction("token", payment_method_id=paypal_pm, token_id=token.id)
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            payment_source = tx._paypal_prepare_order_payload()["payment_source"]["paypal"]
        self.assertNotIn("stored_credential", payment_source)

    def _create_sale_order_transaction(self):
        if "sale.order" not in self.env:
            self.skipTest("Skipping shipping address test because sale is not installed.")

        product = self.env["product.product"].create(  # noqa: OLS03001
            {"name": "$5", "list_price": 5.0}
        )
        order = self.env["sale.order"].create({  # noqa: OLS03001
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": product.id})],
        })
        return self._create_transaction(flow="direct", sale_order_ids=[Command.set(order.ids)])

    def test_shipping_address_provided_when_complete(self):
        tx = self._create_sale_order_transaction()

        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "SET_PROVIDED_ADDRESS",
            "Address should be provided when possible",
        )
        self.assertDictEqual(
            payload["purchase_units"][0]["shipping"]["address"],
            {
                "address_line_1": tx.partner_id.street,
                "address_line_2": tx.partner_id.street2,
                "postal_code": tx.partner_id.zip,
                "admin_area_2": tx.partner_id.city,
                "country_code": tx.partner_id.country_code,
            },
        )

    def test_shipping_address_omitted_when_incomplete(self):
        tx = self._create_sale_order_transaction()

        # Set country to one where state is required
        self.partner.country_id = self.env.ref("base.us")
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "NO_SHIPPING",
            "No shipping should be set if address values are incomplete",
        )
        self.assertNotIn("shipping", payload["purchase_units"][0])

    def test_shipping_address_prefers_delivery_partner(self):
        tx = self._create_sale_order_transaction()

        # Set country to one where state is required, making the main address incomplete.
        self.partner.country_id = self.env.ref("base.us")
        self.partner.child_ids = [
            Command.create({
                "name": tx.partner_id.name,
                "type": "delivery",
                "street": "40 Wall Street",
                "city": "New York City",
                "zip": "10005",
                "state_id": self.env.ref("base.state_us_27").id,
                "country_id": tx.partner_id.country_id.id,
            })
        ]
        shipping_partner = tx.sale_order_ids.partner_shipping_id = self.partner.child_ids
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload["payment_source"]["paypal"]["experience_context"]["shipping_preference"],
            "SET_PROVIDED_ADDRESS",
            "Address should be provided when partner has a complete delivery address",
        )
        self.assertDictEqual(
            payload["purchase_units"][0]["shipping"]["address"],
            {
                "address_line_1": shipping_partner.street,
                "postal_code": shipping_partner.zip,
                "admin_area_1": shipping_partner.state_id.code,
                "admin_area_2": shipping_partner.city,
                "country_code": shipping_partner.country_code,
            },
        )

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction(flow="direct")
        reference = self.env["payment.transaction"]._extract_reference(
            "paypal", {"reference_id": tx.reference}
        )
        self.assertEqual(tx.reference, reference)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_sets_provider_reference(self):
        tx = self._create_transaction("direct")
        normalized_data = paypal_utils.normalize_payment_data(
            self.completed_order, has_capture_data=True
        )
        tx.with_context(payment_safe_write=True)._apply_updates(normalized_data)
        self.assertEqual(tx.provider_reference, normalized_data["id"])

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_confirms_transaction(self):
        tx = self._create_transaction("direct")
        normalized_data = paypal_utils.normalize_payment_data(
            self.completed_order, has_capture_data=True
        )
        tx.with_context(payment_safe_write=True)._apply_updates(normalized_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_sets_pending_transaction(self):
        normalized_data = paypal_utils.normalize_payment_data(self.payment_data.get("resource"))

        # Pending transaction
        self.reference = "Test Transaction 2"
        tx = self._create_transaction("direct")
        payload = {
            **normalized_data,
            "reference_id": self.reference,
            "status": "PENDING",
            "pending_reason": "multi_currency",
        }
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.state_message, payload["pending_reason"])

    def test_apply_updates_sets_transaction_in_error(self):
        """Test that the transaction is set in error with the state message from the payment data
        when the payment is declined."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "id": self.order_id,
            "status": "DECLINED",
            "state_message": "The provided payment source cannot be used.",
        })
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "The provided payment source cannot be used.")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are extracted from the payment data."""
        tx = self._create_transaction("direct")
        normalized_data = paypal_utils.normalize_payment_data(self.payment_data.get("resource"))
        self.assertDictEqual(
            tx._extract_amount_data(normalized_data),
            {"amount": self.amount, "currency_code": self.currency.name},
        )

    def test_extract_token_values_maps_fields_correctly(self):
        """Test that the token values are extracted from the vaulted payment source."""
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        tx = self._create_transaction("direct", payment_method_id=paypal_pm, tokenize=True)
        payment_data = {
            "payment_source": {
                "paypal": {
                    "email_address": "buyer@example.com",
                    "attributes": {"vault": {"id": "VAULT123", "status": "VAULTED"}},
                }
            }
        }
        self.assertDictEqual(
            tx._extract_token_values(payment_data),
            {"provider_ref": "VAULT123", "payment_details": "buyer@example.com"},
        )
