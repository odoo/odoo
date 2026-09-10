# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_dpo.tests.common import DPOCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(DPOCommon):
    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        expected_values = {
            "api_url": "https://secure.3gdirectpay.com/payv2.php",
            "http_method": "get",
            "url_params": {"ID": "dummy_token"},
        }
        with self._mock_send_api_request(return_value={"TransToken": "dummy_token"}):
            self.assertEqual(tx._get_specific_rendering_values(None), expected_values)

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_dpo.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "http_method": "get"},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        reference = self.env["payment.transaction"]._extract_reference("dpo", self.payment_data)
        self.assertEqual(reference, self.reference)

    def test_search_by_reference_returns_tx(self):
        """Test that the transaction is returned from the payment data."""
        tx = self._create_transaction(flow="redirect")
        tx_found = self.env["payment.transaction"]._search_by_reference("dpo", self.payment_data)
        self.assertEqual(tx, tx_found)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["TransID"])

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are extracted from the payment data."""
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )
