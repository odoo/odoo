# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_mollie.tests.common import MollieCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(MollieCommon):
    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendering values contain all the expected keys."""
        tx = self._create_transaction("redirect")
        test_url = "https://www.mollie.com/checkout"
        expected_values = {
            "api_url": test_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(test_url),
        }
        with self._mock_send_api_request(
            return_value={"_links": {"checkout": {"href": test_url}}, "id": "provider Ref (TEST)"}
        ):
            values = tx.with_context(payment_safe_write=True)._get_specific_rendering_values(None)
        self.assertDictEqual(values, expected_values)

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_mollie.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "http_method": "get"},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_no_item_missing_from_mollie_request_payload(self):
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

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        reference = self.env["payment.transaction"]._extract_reference("mollie", self.payment_data)
        self.assertEqual(reference, self.reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, "tr_ABCxyz0123")

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_mollie.payment_method_apple_pay")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount data is extracted correctly from the payment data."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": self.amount, "currency_code": self.currency.name}
        )

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
