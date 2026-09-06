# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time
from werkzeug.urls import url_encode

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_worldline.controllers.main import WorldlineController
from odoo.addons.payment_worldline.tests.common import WorldlineCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(WorldlineCommon, PaymentHttpCommon):
    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """Test that the reference is recomputed with a singularized 'WL' prefix when the natural
        reference exceeds Worldline's 30-character limit."""
        reference = self.env["payment.transaction"]._compute_reference(
            self.worldline.code, prefix="a" * 31
        )
        self.assertEqual(reference, "WL-20111102120021")

    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_computed_based_on_document_name(self):
        """Test that the reference is computed based on the invoice name when it doesn't exceed
        Worldline's 30-character limit."""
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
            self.worldline.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, invoice.name)

    @freeze_time("2011-11-02 12:00:21")  # Freeze time for consistent singularization behavior.
    def test_reference_is_stripped_at_max_length(self):
        """Test that the recomputed reference does not exceed Worldline's 30-character limit."""
        reference = self.env["payment.transaction"]._compute_reference(
            self.worldline.code, prefix="a" * 50
        )
        self.assertLessEqual(len(reference), 30)

    def test_no_item_missing_from_processing_values(self):
        """Test that the token-flow transaction is switched to the redirect flow when Worldline
        requires 3-D Secure authentication."""
        tx = self._create_transaction(
            "token", state="error", state_message="AUTHORIZATION_REQUESTED"
        )
        processing_values = tx.with_context(
            payment_safe_write=True
        )._get_specific_processing_values(None)
        self.assertDictEqual(processing_values, {"force_flow": "redirect"})

    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction("redirect")
        with self._mock_send_api_request(return_value={"redirectUrl": "https://dummy.com"}):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(rendering_values, {"api_url": "https://dummy.com"})

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_worldline.models.payment_transaction.PaymentTransaction"
            "._get_specific_rendering_values",
            return_value={"api_url": "https://dummy.com"},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], "https://dummy.com")
        self.assertEqual(form_info["method"], "post")
        self.assertDictEqual(form_info["inputs"], {})

    def test_no_item_missing_from_checkout_session_request_payload(self):
        """Test that the request values are conform to the transaction fields."""
        tx = self._create_transaction(
            "redirect", payment_method_id=self.provider._get_pm_from_code("card").id
        )
        with self._mock_send_api_request(
            return_value={"redirectUrl": "https://dummy.com"}
        ) as send_request_mock:
            tx._get_specific_rendering_values(None)
        request_payload = send_request_mock.call_args.kwargs["json"]

        return_url_params = url_encode({"provider_id": str(tx.provider_id.id)})
        return_url = f"{self._build_url(WorldlineController._return_url)}?{return_url_params}"
        self.assertDictEqual(
            request_payload,
            {
                "hostedCheckoutSpecificInput": {
                    "locale": tx.partner_lang or "",
                    "returnUrl": return_url,
                    "showResultPage": False,
                    "paymentProductFilters": {"restrictTo": {"groups": ["cards"]}},
                },
                "order": {
                    "amountOfMoney": {
                        "amount": payment_utils.to_minor_currency_units(tx.amount, tx.currency_id),
                        "currencyCode": tx.currency_id.name,
                    },
                    "customer": {
                        "billingAddress": {
                            "city": tx.partner_city or "",
                            "countryCode": tx.partner_country_id.code or "",
                            "state": tx.partner_state_id.name or "",
                            "street": tx.partner_address or "",
                            "zip": tx.partner_zip or "",
                        },
                        "contactDetails": {
                            "emailAddress": tx.partner_email or "",
                            "phoneNumber": tx.partner_phone or "",
                        },
                        "personalInformation": {
                            "name": {"firstName": "Norbert", "surname": "Buyer"}
                        },
                    },
                    "references": {"descriptor": tx.reference, "merchantReference": tx.reference},
                },
                "cardPaymentMethodSpecificInput": {
                    "authorizationMode": "SALE",
                    "tokenize": tx.tokenize,
                },
            },
        )

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        reference = self.env["payment.transaction"]._extract_reference(
            "worldline", self.payment_data
        )
        self.assertEqual(reference, self.reference)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set when processing the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, "1234567890")

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated based on the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id.code, "visa")

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_cancels_transaction(self):
        """Test that the transaction state is set to 'cancel' when the payment data indicate a
        cancelled payment."""
        tx = self._create_transaction("redirect")
        payment_data = {
            "payment": {
                "paymentOutput": self.payment_data["payment"]["paymentOutput"],
                "hostedCheckoutSpecificOutput": {"hostedCheckoutId": "123456789"},
                "status": "CANCELLED",
                "statusOutput": {"errors": [{"errorCode": "30171001"}]},
            }
        }
        tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(tx.state, "cancel")
        self.assertEqual(tx.state_message, "Transaction cancelled with error code 30171001.")

    def test_apply_updates_sets_transaction_in_error_on_insufficient_funds(self):
        """Test that the transaction state is set to 'error' when the payment data indicate the
        payment was declined for insufficient funds."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(
            self.payment_data_insufficient_funds
        )
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "Transaction declined with error code 30511001.")

    def test_apply_updates_sets_transaction_in_error_on_expired_card(self):
        """Test that the transaction state is set to 'error' when the payment data indicate the
        payment was declined for an expired card."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data_expired_card)
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "Transaction declined with error code 30331001.")

    def test_tokenize_creates_token(self):
        """Test that tokenizing a successful transaction creates and links a token."""
        tx = self._create_transaction("redirect", tokenize=True)
        tx.with_context(payment_safe_write=True)._tokenize(self.payment_data)
        self.assertTrue(tx.token_id, "A token should have been created and linked to the tx.")
        self.assertEqual(tx.token_id.provider_ref, "whateverToken")
        self.assertEqual(tx.token_id.payment_details, "4242")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are extracted from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )

    def test_extract_token_values_maps_fields_correctly(self):
        """Test that the token values are extracted from the payment data."""
        tx = self._create_transaction("redirect", tokenize=True)
        token_values = tx._extract_token_values(self.payment_data)
        self.assertDictEqual(
            token_values, {"payment_details": "4242", "provider_ref": "whateverToken"}
        )
