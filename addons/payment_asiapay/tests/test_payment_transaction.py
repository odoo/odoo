# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_asiapay import const
from odoo.addons.payment_asiapay.tests.common import AsiaPayCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AsiaPayCommon, PaymentHttpCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test the singularization of reference prefixes."""
        reference = self.env["payment.transaction"]._compute_reference(self.asiapay.code)
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
            self.asiapay.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, "MISC/2011/11/0001-20111102120021")

    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_stripped_at_max_length(self):
        """Test that reference prefixes are stripped to have a length of at most 35 chars."""
        reference = self.env["payment.transaction"]._compute_reference(
            self.asiapay.code, prefix="this is a long reference of more than 35 characters"
        )
        self.assertEqual(reference, "this is a long refer-20111102120021")
        self.assertEqual(len(reference), 35)

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_asiapay.models.payment_provider.PaymentProvider"
            "._asiapay_calculate_signature",
            return_value="dummy_signature",
        ):
            rendering_values = tx._get_specific_rendering_values(None)
            return_url = self._build_url("/payment/asiapay/return")
            self.assertDictEqual(
                rendering_values,
                {
                    "api_url": tx.provider_id._asiapay_get_api_url(),
                    "url_params": {
                        "amount": tx.amount,
                        "currCode": const.CURRENCY_MAPPING[tx.currency_id.name],
                        "lang": const.LANGUAGE_CODES_MAPPING["en"],
                        "merchantId": tx.provider_id.asiapay_merchant_id,
                        "mpsMode": "SCP",
                        "payMethod": "ALL",
                        "payType": "N",
                        "orderRef": tx.reference,
                        "successUrl": return_url,
                        "failUrl": return_url,
                        "cancelUrl": return_url,
                        "secureHash": "dummy_signature",
                    },
                },
            )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that no key is omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        expected_input_keys = [
            "merchantId",
            "amount",
            "orderRef",
            "currCode",
            "mpsMode",
            "successUrl",
            "failUrl",
            "cancelUrl",
            "payType",
            "lang",
            "payMethod",
            "secureHash",
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], tx.provider_id._asiapay_get_api_url())
        self.assertEqual(form_info["method"], "post")
        self.assertListEqual(list(form_info["inputs"].keys()), expected_input_keys)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction(flow="redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "asiapay", self.redirect_payment_data
        )
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.provider_reference, self.webhook_payment_data["PayRef"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_asiapay.payment_method_alipay")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )
