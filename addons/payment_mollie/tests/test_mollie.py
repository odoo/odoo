# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mollie.controllers.main import MollieController
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged("post_install", "-at_install")
class MollieTest(MollieCommon, PaymentHttpCommon):
    def test_payment_request_payload_values(self):
        tx = self._create_transaction(flow="redirect")

        payload = tx._mollie_prepare_payment_request_payload()
        expected_billing_address = {
            "givenName": "Norbert",
            "familyName": "Buyer",
            "streetAndNumber": "Huge Street 2/543",
            "postalCode": "1000",
            "city": "Sin City",
            "country": "BE",
            "email": "norbert.buyer@example.com",
        }

        self.assertDictEqual(payload["amount"], {"currency": "EUR", "value": "1111.11"})
        self.assertDictEqual(payload["billingAddress"], expected_billing_address)
        self.assertDictEqual(
            payload["lines"][0]["totalAmount"], {"currency": "EUR", "value": "1111.11"}
        )
        self.assertEqual(payload["description"], tx.reference)

    def test_payload_preparation_in_payment_with_tokenize(self):
        """Test that tokenization requests create a customer and set a 'first' sequence without a
        mandate ID."""
        tx = self._create_transaction("redirect", tokenize=True)
        with patch.object(
            self.env.registry["payment.transaction"],
            "_mollie_create_customer",
            return_value="cst_test987",
        ):
            payload = tx._mollie_prepare_payment_request_payload()

        expected_payload = {"sequenceType": "first", "customerId": "cst_test987"}
        for key, value in expected_payload.items():
            self.assertEqual(payload.get(key), value)
        self.assertNotIn("mandateId", payload)

    def test_payload_preparation_in_payment_with_token(self):
        """Test that using a saved token produces a recurring payload with customer and mandate IDs
        and no method."""
        token = self._create_token(mollie_customer_id="cst_test987")
        tx = self._create_transaction("redirect", token_id=token.id)

        payload = tx._mollie_prepare_payment_request_payload()

        expected_payload = {
            "sequenceType": "recurring",
            "customerId": "cst_test987",
            "mandateId": "provider Ref (TEST)",
        }
        for key, value in expected_payload.items():
            self.assertEqual(payload.get(key), value)
        self.assertNotIn("method", payload)

    def test_payload_preparation_in_oneoff_payment(self):
        """Test that a payment without tokenization or token is configured as a one-off sequence."""
        tx = self._create_transaction("redirect")
        payload = tx._mollie_prepare_payment_request_payload()
        self.assertEqual(payload.get("sequenceType"), "oneoff")

    def test_extract_token_values_maps_fields_correctly(self):
        """Test that the token values are extracted correctly from the payment data."""
        tx = self._create_transaction("direct")
        payment_data = {
            "customerId": "cst_test987",
            "details": {"cardNumber": "4242"},
            "mandateId": "provider Ref (TEST)",
        }
        token_values = tx._extract_token_values(payment_data)
        self.assertDictEqual(
            token_values,
            {
                "payment_details": "4242",
                "provider_ref": "provider Ref (TEST)",
                "mollie_customer_id": "cst_test987",
            },
        )

    def test_incomplete_billing_address_not_sent(self):
        self.default_partner.zip = ""
        tx = self._create_transaction(flow="redirect")

        payload = tx._mollie_prepare_payment_request_payload()
        expected_billing_address = {
            "givenName": "Norbert",
            "familyName": "Buyer",
            "email": "norbert.buyer@example.com",
        }

        self.assertDictEqual(payload["billingAddress"], expected_billing_address)

    @mute_logger(
        "odoo.addons.payment_mollie.controllers.main",
        "odoo.addons.payment_mollie.models.payment_transaction",
    )
    def test_webhook_notification_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        self._disable_process_patcher()
        tx = self._create_transaction("redirect")
        url = self._build_url(MollieController._webhook_url)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={
                "status": "paid",
                "amount": {"value": str(self.amount), "currency": self.currency.name},
                "id": "provider Ref (TEST)",
            },
        ):
            self._make_http_post_request(url, data=self.payment_data)
        self._run_processing()
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_return_from_checkout_redirects_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._return_url)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_http_get_request(url, params=self.payment_data)
        self.assertTrue(response.url.endswith('/payment/status'))

    @mute_logger("odoo.addons.payment_mollie.controllers.main")
    def test_webhook_notification_is_rejected_when_payment_data_unavailable(self):
        self._create_transaction("redirect")
        url = self._build_url(MollieController._webhook_url)
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=ValidationError("Service Unavailable"),
        ):
            response = self._make_http_post_request(url, data=self.payment_data)
        self.assertEqual(response.status_code, 503)

    def test_lines_payload_with_taxes_included_unit_prices(self):
        """Test that the lines are sent with their taxes included unit prices."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=23.0)
        line_items = {
            "line": {
                "name": "Chair",
                "description": "",
                "sku": "CHAIR",
                "quantity": 2,
                "total": 23.0,
                "url": "https://example.com/shop/chair",
                "image_url": "https://example.com/chair.png",
            }
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            lines = tx._mollie_prepare_lines_payload(2)
        self.assertListEqual(
            lines,
            [
                {
                    "description": "Chair",
                    "quantity": 2,
                    "unitPrice": {"currency": "EUR", "value": "11.50"},
                    "totalAmount": {"currency": "EUR", "value": "23.00"},
                    "sku": "CHAIR",
                    "productUrl": "https://example.com/shop/chair",
                    "imageUrl": "https://example.com/chair.png",
                }
            ],
        )

    def test_lines_payload_falls_back_to_single_quantity(self):
        """Test that a line with a fractional quantity is sent with a quantity of 1."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=10.0)
        line_items = {"line": {"name": "Desk", "description": "", "quantity": 1.5, "total": 10.0}}
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            line = tx._mollie_prepare_lines_payload(2)[0]
        self.assertEqual((line["quantity"], line["unitPrice"]["value"]), (1, "10.00"))

    def test_lines_payload_skips_too_long_sku(self):
        """Test that the SKU is only sent if Mollie accepts its length."""
        PaymentTransaction = self.env.registry["payment.transaction"]
        tx = self._create_transaction(flow="redirect", amount=10.0)
        line_items = {
            "line": {
                "name": "Desk",
                "description": "",
                "sku": "A" * 65,
                "quantity": 1,
                "total": 10.0,
            }
        }
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            line = tx._mollie_prepare_lines_payload(2)[0]
        self.assertNotIn("sku", line)

    def _assert_default_lines(self, tx, line_items):
        PaymentTransaction = self.env.registry["payment.transaction"]
        with patch.object(PaymentTransaction, "_get_line_items", return_value=line_items):
            lines = tx._mollie_prepare_lines_payload(2)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["description"], "Odoo purchase")
        self.assertEqual(lines[0]["totalAmount"]["value"], f"{tx.amount:.2f}")

    def test_default_lines_with_negative_line(self):
        """Test that a single line is sent for the whole amount when a line item is negative."""
        tx = self._create_transaction(flow="redirect", amount=15.0)
        self._assert_default_lines(
            tx,
            {
                "line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0},
                "discount": {"name": "Promo", "description": "", "quantity": 1, "total": -5.0},
            },
        )

    def test_default_lines_with_nameless_line(self):
        """Test that a single line is sent for the whole amount when a line item has no name."""
        tx = self._create_transaction(flow="redirect", amount=10.0)
        self._assert_default_lines(
            tx, {"line": {"name": "", "description": "", "quantity": 1, "total": 10.0}}
        )

    def test_default_lines_for_partial_payment(self):
        """Test that a single line is sent for the whole amount when the line items do not add up
        to the transaction amount."""
        tx = self._create_transaction(flow="redirect", amount=10.0)
        self._assert_default_lines(
            tx, {"line": {"name": "Desk", "description": "", "quantity": 1, "total": 20.0}}
        )

    def test_default_lines_without_line_items(self):
        """Test that a single line is sent for the whole amount when there are no line items."""
        tx = self._create_transaction(flow="redirect", amount=10.0)
        self._assert_default_lines(tx, {})
