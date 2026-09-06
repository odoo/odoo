# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_flutterwave.tests.common import FlutterwaveCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(FlutterwaveCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test that transaction references are unique at the provider level."""
        reference = self.env["payment.transaction"]._compute_reference(self.flutterwave.code)
        self.assertEqual(reference, "tx-20111102120021")

    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_computed_based_on_document_name(self):
        """Test the computation of reference prefixes based on the provided invoice."""
        self._skip_if_account_payment_is_not_installed()
        company = self.env.company
        Account = self.env["account.account"]  # noqa: OLS03001
        default_account_revenue = Account.with_company(company).search(
            [
                *Account._check_company_domain(company),
                ("account_type", "=", "income"),
                ("id", "!=", company.account_journal_early_pay_discount_gain_account_id.id),
            ],
            limit=1,
        )

        invoice = self.env["account.move"].create({  # noqa: OLS03001
            "move_type": "entry",
            "date": "2011-11-02",
            "line_ids": [
                Command.create({"name": "line", "account_id": default_account_revenue.id})
            ],
        })
        invoice.action_post()
        reference = self.env["payment.transaction"]._compute_reference(
            self.flutterwave.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, "MISC/2011/11/0001-20111102120021")

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        with self._mock_send_api_request(return_value={"link": "https://dummy.com"}):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(
            rendering_values, {"api_url": "https://dummy.com", "http_method": "get"}
        )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_flutterwave.models.payment_transaction.PaymentTransaction"
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
        reference = self.env["payment.transaction"]._extract_reference(
            "flutterwave", self.redirect_payment_data
        )
        self.assertEqual(reference, self.reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.verification_data["data"])
        self.assertEqual(tx.provider_reference, self.verification_data["data"]["id"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction(flow="redirect")
        payment_data = dict(self.verification_data["data"], payment_type="banktransfer")
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_flutterwave.payment_method_bank_transfer")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.verification_data["data"])
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.verification_data["data"])
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )

    def test_extract_token_values_maps_fields_correctly(self):
        tx = self._create_transaction(flow="redirect")
        token_values = tx._extract_token_values(self.verification_data["data"])
        self.assertDictEqual(
            token_values,
            {
                "payment_details": "2950",
                "provider_ref": "flw-t1nf-f9b3bf384cd30d6fca42b6df9d27bd2f-m03k",
                "flutterwave_customer_email": "user@example.com",
            },
        )
