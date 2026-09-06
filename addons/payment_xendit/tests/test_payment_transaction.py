# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_xendit.controllers.main import XenditController
from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PaymentHttpCommon, XenditCommon):
    def test_no_item_missing_from_processing_values(self):
        """Ensure that for IDR currency, processing_values should contain converted_amount
        which is the amount rounded down to the nearest 0."""
        currency_idr = self.env.ref("base.IDR")
        tx = self._create_transaction("redirect", amount=1000.50, currency_id=currency_idr.id)
        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            processing_values = tx._get_specific_processing_values({})
        self.assertDictEqual(
            processing_values,
            {
                "rounded_amount": 1000,
                "access_token": self._generate_test_access_token(tx.reference),
                "currency": tx.currency_id.name,
            },
        )

    def test_no_item_missing_from_rendering_values(self):
        """Test that when the redirect flow is triggered, rendering_values contains the API_URL
        corresponding to the response of API request."""
        tx = self._create_transaction("redirect")
        url = "https://dummy.com"
        return_value = {"invoice_url": url}
        with (
            self._mock_send_api_request(return_value=return_value),
            patch.object(payment_utils, "generate_access_token", self._generate_test_access_token),
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(rendering_values, {"api_url": url, "http_method": "get"})

    def test_empty_rendering_values_if_direct(self):
        """Test that if it's a card payment (like in direct flow), rendering_values should be empty
        and no API call should be committed in the process."""
        tx = self._create_transaction("direct", payment_method_id=self.payment_method_card.id)
        with (
            self._mock_send_api_request(
                return_value={"data": {"link": "https://dummy.com"}}
            ) as mock,
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            rendering_values = tx._get_specific_rendering_values(None)
            self.assertEqual(mock.call_count, 0)
        self.assertDictEqual(rendering_values, {})

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        with (
            patch(
                "odoo.addons.payment_xendit.models.payment_transaction.PaymentTransaction"
                "._get_specific_rendering_values",
                return_value={"api_url": "https://dummy.com", "http_method": "get"},
            ),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_no_item_missing_from_invoice_request_payload(self):
        """Test that the invoice request values are conform to the transaction fields."""
        self.maxDiff = 10000  # Allow comparing large dicts.
        self.reference = "tx1"
        tx = self._create_transaction(flow="redirect")
        return_url = self._build_url(XenditController._return_url)
        access_token = self._generate_test_access_token(tx.reference, tx.amount)
        success_url_params = url_encode({
            "tx_ref": tx.reference,
            "access_token": access_token,
            "success": "true",
        })

        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            request_payload = tx._xendit_prepare_invoice_request_payload()
        self.assertDictEqual(
            request_payload,
            {
                "external_id": tx.reference,
                "amount": tx.amount,
                "description": tx.reference,
                "customer": {
                    "given_names": tx.partner_name,
                    "email": tx.partner_email,
                    "mobile_number": tx.partner_id.phone,
                    "addresses": [
                        {
                            "city": tx.partner_city,
                            "country": tx.partner_country_id.name,
                            "postal_code": tx.partner_zip,
                            "street_line1": tx.partner_address,
                        }
                    ],
                },
                "success_redirect_url": f"{return_url}?{success_url_params}",
                "failure_redirect_url": return_url,
                "payment_methods": [self.payment_method_code.upper()],
                "currency": tx.currency_id.name,
            },
        )

    def test_charge_request_contains_rounded_amount_idr(self):
        """Ensure that for IDR currency, when creating charge API, the amount in payload should be
        rounded down to the nearest 0."""
        currency_idr = self.env.ref("base.IDR")
        tx = self._create_transaction("redirect", amount=1000.50, currency_id=currency_idr.id)
        with self._mock_send_api_request(
            return_value={**self.charge_payment_data, "amount": 1000}
        ) as mock_req:
            tx._xendit_create_charge("dummytoken")
            payload = mock_req.call_args.kwargs.get("json")
            self.assertEqual(payload["amount"], 1000)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "xendit", self.webhook_payment_data
        )
        self.assertEqual(tx.reference, reference)

    def test_search_by_reference_returns_tx(self):
        """Test that the transaction is found based on the payment data."""
        tx = self._create_transaction("redirect")
        tx_found = self.env["payment.transaction"]._search_by_reference(
            "xendit", self.webhook_payment_data
        )
        self.assertEqual(tx, tx_found)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set when processing the payment data."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.charge_payment_data)
        self.assertEqual(tx.provider_reference, self.charge_payment_data["id"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated according to the payment data."""
        tx = self._create_transaction("direct")
        payment_data = dict(self.webhook_payment_data, payment_method="CREDIT_CARD")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.payment_method_id, self.payment_method_card)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    def test_tokenize_creates_token(self):
        """Test that a successful charge request tokenizes the transaction."""
        tx = self._create_transaction("direct", tokenize=True)
        with self._mock_send_api_request(return_value=self.charge_payment_data):
            tx._xendit_create_charge("dummytoken")
        tx.with_context(payment_safe_write=True)._tokenize(self.charge_payment_data)
        self.assertTrue(tx.token_id, "A token should have been created and linked to the tx.")
        self.assertEqual(tx.token_id.payment_details, "2151")
        self.assertEqual(tx.token_id.provider_ref, "6645aaa2f00da60017cdc669")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are extracted from the payment data."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data,
            {
                "amount": float(self.amount),
                "currency_code": self.currency.name,
                "precision_digits": 0,
            },
        )

    def test_extract_token_values_maps_fields_correctly(self):
        tx = self._create_transaction("direct")
        token_values = tx._extract_token_values(self.charge_payment_data)
        self.assertDictEqual(
            token_values, {"payment_details": "2151", "provider_ref": "6645aaa2f00da60017cdc669"}
        )
