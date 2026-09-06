# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PaymobCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test the singularization of reference prefixes."""
        reference = self.env["payment.transaction"]._compute_reference(self.paymob.code)
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
            self.paymob.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, "MISC/2011/11/0001-20111102120021")

    def test_no_item_missing_from_rendering_values(self):
        """Test that when the redirect flow is triggered, rendering_values contains the API_URL and
        URL_PARAMS corresponding to the response of API request."""
        tx = self._create_transaction("redirect")
        with self._mock_send_api_request(
            return_value={"intention_order_id": self.order_id, "client_secret": "dummy_secret"}
        ):
            rendering_values = tx.with_context(
                payment_safe_write=True
            )._get_specific_rendering_values(None)
        paymob_url = self.paymob._paymob_get_api_url()
        paymob_pk = self.paymob.paymob_public_key
        self.assertEqual(rendering_values["api_url"], f"{paymob_url}/unifiedcheckout/")
        self.assertEqual(rendering_values["url_params"]["publicKey"], paymob_pk)
        self.assertEqual(rendering_values["url_params"]["clientSecret"], "dummy_secret")

    def test_rendering_values_sets_provider_reference(self):
        """Test that the provider reference is set as soon as the payment intention is created,
        while the transaction remains in a draft state until the customer completes payment."""
        tx = self._create_transaction("redirect")
        with self._mock_send_api_request(return_value={"intention_order_id": self.order_id}):
            tx.with_context(payment_safe_write=True)._get_specific_rendering_values(None)
        self.assertEqual(tx.provider_reference, self.order_id)

    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        with patch(
            "odoo.addons.payment_paymob.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com", "http_method": "get", "url_params": {}},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "get")
        self.assertDictEqual(form_info["inputs"], {})

    def test_no_item_missing_from_payment_request_payload(self):
        """Test that the request values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        request_payload = tx._paymob_prepare_payment_request_payload()

        partner_first_name, partner_last_name = payment_utils.split_partner_name(tx.partner_name)
        base_url = tx.get_base_url()
        redirect_url = urls.urljoin(base_url, PaymobController._return_url)
        webhook_url = urls.urljoin(base_url, PaymobController._webhook_url)
        expected_payload = {
            "special_reference": tx.reference,
            "amount": payment_utils.to_minor_currency_units(tx.amount, tx.currency_id),
            "currency": tx.currency_id.name,
            "payment_methods": ["dummytest"],
            "notification_url": webhook_url,
            "redirection_url": redirect_url,
            "billing_data": {
                "first_name": partner_first_name or partner_last_name or "",
                "last_name": partner_last_name or "",
                "email": tx.partner_email or "",
                "street": tx.partner_address or "",
                "state": tx.partner_state_id.name or "",
                "phone_number": (tx.partner_phone or "").replace(" ", ""),
                "country": tx.partner_country_id.code or "",
            },
        }
        self.assertDictEqual(request_payload, expected_payload)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction(flow="redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "paymob", self.redirection_data
        )
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.redirection_data)
        self.assertEqual(tx.state, "done")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.redirection_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )
