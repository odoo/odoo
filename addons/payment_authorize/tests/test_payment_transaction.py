# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AuthorizeCommon):
    def test_no_item_missing_from_processing_values(self):
        """Test custom 'access_token' processing_values for authorize provider."""
        tx = self._create_transaction(flow="direct")
        with (
            mute_logger("odoo.addons.payment.models.payment_transaction"),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            processing_values = tx._get_processing_values()

        with patch(
            "odoo.addons.payment.utils.generate_access_token", new=self._generate_test_access_token
        ):
            self.assertTrue(
                payment_utils.check_access_token(
                    processing_values["access_token"], self.reference, self.partner.id
                )
            )

    def test_refunding_voided_tx_cancels_it(self):
        """Test that refunding a transaction that has been voided from Authorize.net side cancels
        it on Odoo."""
        source_tx = self._create_transaction("direct", state="done")
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".get_transaction_details",
            return_value={"transaction": {"transactionStatus": "voided"}},
        ):
            child_tx = source_tx._refund(amount_to_refund=source_tx.amount)
        self.assertEqual(child_tx.state, "cancel")

    def test_refund_creates_refund_tx(self):
        """Test that refunding a transaction that has been refunded from Authorize.net side creates
        a refund transaction on Odoo."""
        source_tx = self._create_transaction("direct", state="done")
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".get_transaction_details",
            return_value={"transaction": {"transactionStatus": "refundSettledSuccessfully"}},
        ):
            source_tx._refund(amount_to_refund=source_tx.amount)
        refund_tx = self.env["payment.transaction"].search([
            ("source_transaction_id", "=", source_tx.id)
        ])
        self.assertTrue(refund_tx)

    @mute_logger("odoo.addons.payment_authorize.models.payment_transaction")
    def test_refunding_authorized_tx_voids_it(self):
        """Test that refunding a transaction that is still authorized on Authorize.net side voids
        it on Authorize.net instead of refunding it."""
        source_tx = self._create_transaction("direct", state="done")
        with (
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
                ".get_transaction_details",
                return_value={"transaction": {"transactionStatus": "authorizedPendingCapture"}},
            ),
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.void",
                return_value={"dummy": True},
            ) as void_mock,
        ):
            source_tx._refund(amount_to_refund=source_tx.amount)
        self.assertEqual(void_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_authorize.models.payment_transaction")
    def test_refunding_captured_tx_refunds_it_and_creates_refund_tx(self):
        """Test that refunding a transaction that is captured on Authorize.net side captures it and
        create a refund transaction on Odoo."""
        source_tx = self._create_transaction("direct", state="done")
        with (
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
                ".get_transaction_details",
                return_value={"transaction": {"transactionStatus": "settledSuccessfully"}},
            ),
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.refund",
                return_value={"dummy": True},
            ) as refund_mock,
        ):
            source_tx._refund(amount_to_refund=source_tx.amount)
        self.assertEqual(refund_mock.call_count, 1)
        refund_tx = self.env["payment.transaction"].search([
            ("source_transaction_id", "=", source_tx.id)
        ])
        self.assertTrue(refund_tx)

    def test_voided_refund_tx_is_done(self):
        """Test that a refund transaction voided due to the payment not being settled yet is
        marked as done."""
        source_tx = self._create_transaction("direct", state="done")
        with (
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
                ".get_transaction_details",
                return_value={"transaction": {"transactionStatus": "authorizedPendingCapture"}},
            ),
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.void",
                return_value={"x_response_code": "1", "x_type": "void"},
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            refund_tx = source_tx._refund(amount_to_refund=source_tx.amount)
        payload = record_mock.call_args.args[0]
        refund_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(refund_tx.state, "done")

    def test_capture_confirms_tx(self):
        """Test that confirming a capture request sets the capture tx to 'done'."""
        tx = self._create_transaction("direct", state="authorized")
        with (
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.capture",
                return_value={
                    "x_response_code": "1",
                    "x_trans_id": self.trans_id,
                    "x_type": "prior_auth_capture",
                    "payment_method_code": "Visa",
                },
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            captured_tx = tx._capture()
        payload = record_mock.call_args.args[0]
        captured_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(captured_tx.state, "done")

    def test_void_cancels_tx(self):
        """Test that confirming a void request sets the void tx to 'cancel'."""
        tx = self._create_transaction("direct", state="authorized")
        with (
            patch(
                "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI.void",
                return_value={
                    "x_response_code": "1",
                    "x_trans_id": self.trans_id,
                    "x_type": "void",
                    "payment_method_code": "Visa",
                },
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            void_tx = tx._void()
        payload = record_mock.call_args.args[0]
        void_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(void_tx.state, "cancel")

    def test_search_by_reference_finds_transaction_from_webhook_data(self):
        """Test that a transaction is correctly found from webhook data using invoiceNumber."""
        tx = self._create_transaction("direct")
        found_tx = self.env["payment.transaction"]._search_by_reference(
            "authorize", self.webhook_authcapture_data
        )
        self.assertEqual(tx, found_tx)

    def test_apply_updates_voiding_confirmed_tx_cancels_it(self):
        """Test that voiding a transaction cancels it even if it's already confirmed."""
        source_tx = self._create_transaction("direct", state="done")
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".get_transaction_details",
            return_value={"transaction": {"authAmount": self.amount}},
        ):
            source_tx.with_context(payment_safe_write=True)._apply_updates({
                "response": {"x_response_code": "1", "x_type": "void"}
            })
        self.assertEqual(source_tx.state, "cancel")

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["response"]["x_trans_id"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_authorize.payment_method_ach_direct_debit")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_validation_tx_is_tokenized_before_being_voided(self):
        """Test that the tokenization request is sent before the void request.
        The customer profile can only be created from a transaction that has not been voided yet,
        so the tokenization must happen before the validation transaction is voided.
        """
        tx = self._create_transaction("direct", operation="validation", tokenize=True)
        call_order = []

        def tokenize(*_args, **_kwargs):
            call_order.append("tokenize")
            tx.with_context(payment_safe_write=True).tokenize = False

        def void(*_args, **_kwargs):
            call_order.append("void")

        with (
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._tokenize",
                side_effect=tokenize,
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._void",
                side_effect=void,
            ),
        ):
            tx.with_context(payment_safe_write=True)._apply_updates({
                "response": {
                    "x_response_code": "1",
                    "x_type": "auth_only",
                    "x_trans_id": "test_trans_id",
                }
            })

        self.assertEqual(call_order, ["tokenize", "void"])

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".get_transaction_details",
            return_value={"transaction": {"authAmount": tx.amount}},
        ):
            amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )

    def test_amount_validation_is_skipped_when_transaction_details_are_missing(self):
        """Test that the amount validation is skipped when the API returns with an error."""
        tx = self._create_transaction("direct")
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".get_transaction_details",
            return_value={"err_code": "E00040", "err_msg": "The record cannot be found."},
        ):
            amount_data = tx._extract_amount_data({
                "response": {
                    "x_response_code": "E00040",
                    "x_response_reason_text": "The record cannot be found.",
                }
            })
        self.assertEqual(amount_data, None)  # Amount validation is skipped.

    @mute_logger("odoo.addons.payment_authorize.models.payment_transaction")
    def test_extract_token_values_maps_fields_correctly(self):
        tx = self._create_transaction("direct")
        payment_data = {
            "payment_details": "1234",
            "payment_profile_id": "123456789",
            "profile_id": "987654321",
        }
        with patch(
            "odoo.addons.payment_authorize.models.authorize_request.AuthorizeAPI"
            ".create_customer_profile",
            return_value=payment_data,
        ):
            token_values = tx._extract_token_values({})
        self.assertDictEqual(
            token_values,
            {
                "payment_details": "1234",
                "provider_ref": "123456789",
                "authorize_profile": "987654321",
            },
        )
