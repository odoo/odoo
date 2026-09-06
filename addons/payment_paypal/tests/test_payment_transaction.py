# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PaypalCommon):
    def test_no_item_missing_from_processing_values(self):
        tx = self._create_transaction(flow="direct")
        with self._mock_send_api_request(return_value={"id": self.order_id}):
            processing_values = tx._get_processing_values()
        self.assertEqual(processing_values["order_id"], self.order_id)

    def test_no_item_missing_from_order_request_payload(self):
        """Test that the request values are conform to the transaction fields for a standard
        transaction (not the public partner, no shipping address)."""
        tx = self._create_transaction(flow="direct")
        request_payload = tx._paypal_prepare_order_payload()
        self.maxDiff = 10000  # Allow comparing large dicts.

        partner_first_name, partner_last_name = payment_utils.split_partner_name(tx.partner_name)
        expected_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": tx.reference,
                    "description": f"{tx.company_id.name}: {tx.reference}",
                    "amount": {"currency_code": tx.currency_id.name, "value": tx.amount},
                    "payee": {
                        "display_data": {"brand_name": tx.provider_id.company_id.name},
                        "email_address": tx.provider_id.paypal_email_account,
                    },
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {"shipping_preference": "NO_SHIPPING"},
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
        tx = self._create_transaction(flow="direct", partner_id=self.public_user.partner_id.id)
        payload = tx._paypal_prepare_order_payload()
        customer_payload = payload["payment_source"]["paypal"]
        self.assertTrue("email_address" not in customer_payload)
        self.assertEqual(customer_payload["address"]["country_code"], self.company.country_id.code)

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
        """Test the processing of a webhook notification."""
        tx = self._create_transaction("direct")
        normalized_data = PaypalController._normalize_paypal_data(self, self.completed_order)
        tx.with_context(payment_safe_write=True)._apply_updates(normalized_data)
        self.assertEqual(tx.provider_reference, normalized_data["id"])

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is forced to PayPal when processing the payment data."""
        tx = self._create_transaction("direct")
        normalized_data = PaypalController._normalize_paypal_data(self, self.completed_order)
        tx.with_context(payment_safe_write=True)._apply_updates(normalized_data)
        self.assertEqual(tx.payment_method_id, self.env.ref("payment_paypal.payment_method_paypal"))

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        tx = self._create_transaction("direct")
        normalized_data = PaypalController._normalize_paypal_data(self, self.completed_order)
        tx.with_context(payment_safe_write=True)._apply_updates(normalized_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_apply_updates_sets_pending_transaction(self):
        normalized_data = PaypalController._normalize_paypal_data(
            self, self.payment_data.get("resource"), from_webhook=True
        )

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

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are extracted from the payment data."""
        tx = self._create_transaction("direct")
        normalized_data = PaypalController._normalize_paypal_data(
            self, self.payment_data.get("resource"), from_webhook=True
        )
        self.assertDictEqual(
            tx._extract_amount_data(normalized_data),
            {"amount": self.amount, "currency_code": self.currency.name},
        )
