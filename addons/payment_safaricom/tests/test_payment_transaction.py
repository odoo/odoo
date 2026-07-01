# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import verify_hash_signed

from odoo.addons.payment_safaricom.tests.common import SafaricomCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(SafaricomCommon):
    def test_short_reference_is_kept_unchanged(self):
        """Test that references within the 12-char M-PESA AccountReference limit are not
        recomputed."""
        reference = self.env["payment.transaction"]._compute_reference(
            self.provider.code, prefix="short ref"
        )
        self.assertEqual(reference, "short ref")

    def test_long_reference_is_recomputed_from_truncated_prefix(self):
        """Test that references over the 12-char M-PESA AccountReference limit are recomputed
        from a 9-char prefix."""
        reference = self.env["payment.transaction"]._compute_reference(
            self.provider.code, prefix="this is a long reference of more than 12 chars"
        )
        self.assertEqual(reference, "this is a")

    def test_truncated_reference_collision_suffix_fits_within_limit(self):
        """Test that a collision on the truncated prefix is resolved with a suffix that still
        fits the 12-char M-PESA AccountReference limit."""
        self._create_transaction("direct", reference="this is a")
        reference = self.env["payment.transaction"]._compute_reference(
            self.provider.code, prefix="this is a long reference of more than 12 chars"
        )
        self.assertEqual(reference, "this is a-1")

    def test_reference_is_singularized(self):
        """Test that a duplicate reference is resolved by appending a counter."""
        tx = self._create_transaction("direct")
        new_reference = self.env["payment.transaction"]._compute_reference(
            self.provider.code, prefix=tx.reference
        )
        self.assertNotEqual(new_reference, tx.reference)

    def test_no_item_missing_from_stk_push_request_payload(self):
        """Test that the STK Push request payload contains all required M-PESA API fields."""
        tx = self._create_transaction("direct")
        with self._mock_send_api_request({
            "ResponseCode": "0",
            "CheckoutRequestID": self.checkout_id,
        }) as mock_request:
            tx._safaricom_send_stk_push(self.phone)
        self.assertListEqual(
            sorted(mock_request.call_args.kwargs["json"].keys()),
            sorted([
                "AccountReference",
                "Amount",
                "BusinessShortCode",
                "CallBackURL",
                "PartyA",
                "PartyB",
                "Password",
                "PhoneNumber",
                "Timestamp",
                "TransactionDesc",
                "TransactionType",
            ]),
        )

    def test_send_stk_push_records_initiation_response(self):
        """Test that the STK Push initiation response is recorded for deferred processing."""
        tx = self._create_transaction("direct")
        with (
            self._mock_send_api_request({
                "ResponseCode": "0",
                "CheckoutRequestID": self.checkout_id,
            }),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            tx._safaricom_send_stk_push(self.phone)
        self.assertEqual(record_mock.call_count, 1)

    def test_failed_stk_push_request_propagates_error(self):
        """Test that a failed STK Push request propagates the error to the caller instead of
        swallowing it, so the controller can surface it on the inline form."""
        tx = self._create_transaction("direct")
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                side_effect=ValidationError("Connection failed"),
            ),
            self.assertRaises(ValidationError),
        ):
            tx._safaricom_send_stk_push(self.phone)

    def test_callback_url_carries_verifiable_reference(self):
        """Test that the reference signed into the callback URL can be verified with the scope
        used by the webhook."""
        tx = self._create_transaction("direct")
        callback_url = tx._safaricom_get_callback_url()
        signed_reference = parse_qs(urlsplit(callback_url).query)["reference"][0]
        verified = verify_hash_signed(self.env(su=True), "payment_safaricom", signed_reference)
        self.assertEqual(verified, {"reference": tx.reference})

    def test_phone_number_with_country_code_prefix_is_unchanged(self):
        """Test that a phone number already in 254XXXXXXXXX format is returned unchanged."""
        tx = self._create_transaction("direct")
        self.assertEqual(tx._safaricom_format_phone_number("254708374149"), "254708374149")

    def test_phone_number_with_leading_zero_is_normalized(self):
        """Test that a phone number with a leading zero is converted to 254XXXXXXXXX format."""
        tx = self._create_transaction("direct")
        self.assertEqual(tx._safaricom_format_phone_number("0708374149"), "254708374149")

    def test_phone_number_without_prefix_is_normalized(self):
        """Test that a 9-digit phone number without a prefix is converted to 254XXXXXXXXX format."""
        tx = self._create_transaction("direct")
        self.assertEqual(tx._safaricom_format_phone_number("708374149"), "254708374149")

    def test_invalid_phone_number_raises_validation_error(self):
        """Test that an invalid phone number raises a ValidationError."""
        tx = self._create_transaction("direct")
        with self.assertRaises(ValidationError):
            tx._safaricom_format_phone_number("12345")

    def test_extract_reference_finds_reference(self):
        """Test that the transaction is found based on the verified reference injected in the
        payment data."""
        tx = self._create_transaction("direct")
        payment_data = {**self.webhook_payment_data, "reference": tx.reference}
        tx_found = self.env["payment.transaction"]._search_by_reference("safaricom", payment_data)
        self.assertEqual(tx, tx_found)

    def test_apply_updates_cancels_transaction_on_customer_cancellation(self):
        """Test that the transaction state is set to 'cancel' when the customer cancels the
        payment from the status page."""
        tx = self._create_transaction("direct", state="pending")
        tx.with_context(payment_safe_write=True)._apply_updates({"canceled_by_customer": True})
        self.assertEqual(tx.state, "cancel")

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_cancels_transaction_when_user_cancels_prompt(self):
        """Test that the transaction state is set to 'cancel' when the user cancels the STK prompt
        on their phone (ResultCode 1032)."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": self.checkout_id,
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user.",
                }
            }
        })
        self.assertEqual(tx.state, "cancel")

    def test_apply_updates_sets_error_when_user_unreachable(self):
        """Test that the transaction state is set to 'error' when the STK prompt expires unanswered
        (ResultCode 1037)."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": self.checkout_id,
                    "ResultCode": 1037,
                    "ResultDesc": "DS timeout user cannot be reached.",
                }
            }
        })
        self.assertEqual(tx.state, "error")

    def test_apply_updates_sets_error_when_payment_fails(self):
        """Test that the transaction state is set to 'error' when the payment data indicate a
        failed payment."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": self.checkout_id,
                    "ResultCode": 1,
                    "ResultDesc": "The balance is insufficient for the transaction.",
                }
            }
        })
        self.assertEqual(tx.state, "error")

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set from the STK Push initiation response."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "ResponseCode": "0",
            "CheckoutRequestID": self.checkout_id,
        })
        self.assertEqual(tx.provider_reference, self.checkout_id)

    def test_apply_updates_sets_pending_state(self):
        """Test that the transaction state is set to 'pending' from the STK Push initiation
        response."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "ResponseCode": "0",
            "CheckoutRequestID": self.checkout_id,
        })
        self.assertEqual(tx.state, "pending")

    def test_apply_updates_sets_error_when_stk_push_is_rejected(self):
        """Test that the transaction state is set to 'error' when the STK Push is rejected."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "ResponseCode": "1",
            "errorMessage": "Invalid Access Token",
        })
        self.assertEqual(tx.state, "error")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are correctly extracted from the payment data."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data, {"amount": self.amount, "currency_code": self.currency.name}
        )

    def test_success_callback_without_amount_sets_transaction_in_error(self):
        """Test that a success callback lacking CallbackMetadata fails the amount validation
        instead of confirming the transaction."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._process({
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": self.checkout_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                }
            }
        })
        self.assertEqual(tx.state, "error")
