# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_safaricom.tests.common import SafaricomCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(SafaricomCommon):
    def test_reference_is_recomputed_only_over_account_reference_limit(self):
        """Test that references are recomputed from a truncated 9-char prefix only when they
        exceed the 12-char M-PESA AccountReference limit."""
        for prefix, expected in (
            ("short ref", "short ref"),
            ("this is a long reference of more than 12 chars", "this is a"),
        ):
            reference = self.env["payment.transaction"]._compute_reference(
                self.provider.code, prefix=prefix
            )
            self.assertEqual(reference, expected)

    def test_truncated_reference_collision_suffix_fits_within_limit(self):
        """Test that a collision on the truncated prefix is resolved with a suffix that still
        fits the 12-char M-PESA AccountReference limit."""
        self._create_transaction("direct", reference="this is a")
        reference = self.env["payment.transaction"]._compute_reference(
            self.provider.code, prefix="this is a long reference of more than 12 chars"
        )
        self.assertEqual(reference, "this is a-1")

    def test_no_item_missing_from_stk_push_request_payload(self):
        """Test that the STK Push request payload contains all required M-PESA API fields."""
        tx = self._create_transaction("direct")
        payload = tx._safaricom_prepare_payload(self.phone)
        self.assertListEqual(
            sorted(payload.keys()),
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

    def test_stk_push_amount_is_rounded_down_to_whole_number(self):
        """Test that decimal amounts are rounded down to the whole numbers M-PESA supports in the
        STK Push request payload."""
        tx = self._create_transaction("direct", amount=1111.55)
        payload = tx._safaricom_prepare_payload(self.phone)
        self.assertEqual(payload["Amount"], 1111)

    def test_phone_number_is_normalized_to_mpesa_format(self):
        """Test that customary phone number formats are normalized to the 254XXXXXXXXX format
        required by M-PESA."""
        tx = self._create_transaction("direct")
        for phone in ("254708374149", "0708374149", "708374149"):
            self.assertEqual(tx._safaricom_prepare_payload(phone)["PhoneNumber"], "254708374149")

    def test_invalid_phone_number_raises_validation_error(self):
        """Test that an invalid phone number raises a ValidationError."""
        tx = self._create_transaction("direct")
        with self.assertRaises(ValidationError):
            tx._safaricom_prepare_payload("12345")

    def test_extract_reference_finds_reference(self):
        """Test that the transaction is found based on the verified reference injected in the
        payment data."""
        tx = self._create_transaction("direct")
        payment_data = {**self.webhook_payment_data, "reference": tx.reference}
        tx_found = self.env["payment.transaction"]._search_by_reference("safaricom", payment_data)
        self.assertEqual(tx, tx_found)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set from the STK Push initiation response."""
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "ResponseCode": "0",
            "CheckoutRequestID": self.checkout_id,
        })
        self.assertEqual(tx.provider_reference, self.checkout_id)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount, currency, and whole-number precision are correctly extracted
        from the payment data."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertDictEqual(
            amount_data,
            {"amount": self.amount, "currency_code": self.currency.name, "precision_digits": 0},
        )

    def test_extract_amount_data_returns_zero_amount_for_callback_without_metadata(self):
        """Test that a success callback lacking CallbackMetadata yields a zero amount, so that
        the base amount validation isn't skipped and fails the transaction down the line."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data({
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": self.checkout_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                }
            }
        })
        self.assertEqual(amount_data["amount"], 0.0)
