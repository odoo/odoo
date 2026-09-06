# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController
from odoo.addons.payment_buckaroo.tests.common import BuckarooCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(BuckarooCommon, PaymentHttpCommon):
    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        self.env["ir.config_parameter"].set_str("web.base.url", "http://127.0.0.1:8069")
        self.patch(self, "base_url", lambda: "http://127.0.0.1:8069")

        tx = self._create_transaction(flow="redirect")

        return_url = self._build_url(BuckarooController._return_url)
        expected_values = {
            "api_url": tx.provider_id._buckaroo_get_api_url(),
            "url_params": {
                "Brq_websitekey": tx.provider_id.buckaroo_website_key,
                "Brq_amount": tx.amount,
                "Brq_currency": tx.currency_id.name,
                "Brq_invoicenumber": tx.reference,
                "Brq_return": return_url,
                "Brq_returncancel": return_url,
                "Brq_returnerror": return_url,
                "Brq_returnreject": return_url,
                "Brq_culture": "en-US",
                "Brq_signature": "dacc220c3087edcc1200a38a6db0191c823e7f69",
            },
        }
        result = tx._get_specific_rendering_values(None)
        self.assertEqual(result, expected_values)

    def test_no_input_missing_from_redirect_form(self):
        self.env["ir.config_parameter"].set_str("web.base.url", "http://127.0.0.1:8069")
        self.patch(self, "base_url", lambda: "http://127.0.0.1:8069")

        return_url = self._build_url(BuckarooController._return_url)
        expected_values = {
            "Brq_websitekey": self.buckaroo.buckaroo_website_key,
            "Brq_amount": str(self.amount),
            "Brq_currency": self.currency.name,
            "Brq_invoicenumber": self.reference,
            "Brq_signature": "dacc220c3087edcc1200a38a6db0191c823e7f69",
            "Brq_return": return_url,
            "Brq_returncancel": return_url,
            "Brq_returnerror": return_url,
            "Brq_returnreject": return_url,
            "Brq_culture": "en-US",
        }

        tx_sudo = self._create_transaction(flow="redirect")
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = tx_sudo._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])

        self.assertEqual(form_info["action"], "https://testcheckout.buckaroo.nl/html/")
        self.assertDictEqual(
            expected_values,
            form_info["inputs"],
            "Buckaroo: invalid inputs specified in the redirect form.",
        )

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "buckaroo", self.sync_payment_data
        )
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.sync_payment_data)
        self.assertEqual(
            tx.provider_reference, self.sync_payment_data["brq_transactions"].split(",")[0]
        )

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.sync_payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_buckaroo.payment_method_paypal")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.sync_payment_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_buckaroo.models.payment_transaction")
    def test_apply_updates_sets_transaction_in_error(self):
        tx = self._create_transaction(flow="redirect")
        payment_data = BuckarooController._normalize_data_keys(
            dict(
                self.sync_payment_data,
                brq_invoicenumber=self.reference,
                brq_statuscode="2",
                brq_signature="b8e54e26b2b5a5e697b8ed5085329ea712fd48b2",
            )
        )
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "error")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.sync_payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )
