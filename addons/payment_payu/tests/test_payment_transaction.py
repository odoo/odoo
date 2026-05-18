# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_payu.tests.common import PayUCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PayUCommon):
    def test_no_item_missing_from_txn_payload(self):
        """ Test that the transaction payload contains all required fields with correct values. """
        tx = self._create_transaction("direct")
        payload = tx._payu_prepare_txn_payload()
        self.maxDiff = 10000  # Allow comparing large dicts.
        return_url = f"{self.provider.get_base_url()}/payment/payu/return"
        webhook_url = f"{self.provider.get_base_url()}/payment/payu/webhook"
        expected_payload = {
            "key": self.payu_merchant_key,
            "txnid": self.reference,
            "amount": str(self.amount),
            "productinfo": "Odoo-Product",
            "firstname": self.partner.name,
            "phone": self.partner.phone,
            "email": self.partner.email,
            "surl": return_url,
            "furl": return_url,
            "udf1": "payment",
            "enforce_paymethod": "creditcard|debitcard",
            "partner_webhook_success": webhook_url,
            "partner_webhook_failure": webhook_url,
            "hash": payload.get("hash"),
        }
        self.assertDictEqual(payload, expected_payload)


    def test_processing_values_require_partner_contact_info(self):
        for field in ('partner_email', 'partner_phone'):
            with self.subTest(field=field):
                tx = self._create_transaction(
                    "direct",
                    reference=f"Test Transaction {field}",
                )
                setattr(tx, field, False)
                with self.assertRaises(UserError):
                    tx._get_specific_processing_values({})

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("direct")
        tx._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_payu.models.payment_transaction")
    def test_apply_updates_sets_error_for_unknown_status(self):
        """Test that an unknown payment status results in an error state."""
        tx = self._create_transaction("direct")
        data = dict(self.webhook_payment_data, status="unknown_status")
        tx._apply_updates(data)
        self.assertEqual(tx.state, "error")

    def test_apply_updates_raises_on_missing_status(self):
        """Test that _apply_updates raises ValidationError when status is missing."""
        tx = self._create_transaction("direct")
        data = dict(self.webhook_payment_data, status="")
        with self.assertRaises(ValidationError):
            tx._apply_updates(data)

    def test_apply_updates_sets_provider_reference(self):
        """Test that provider_reference is set from mihpayid in webhook data."""
        tx = self._create_transaction("direct")
        tx._apply_updates(self.webhook_payment_data)
        self.assertEqual(tx.provider_reference, self.mihpayid)

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    @mute_logger("odoo.addons.payment_payu.models.payment_transaction")
    def test_apply_updates_does_not_update_reference_if_confirmed(self):
        """Test that the provider reference is not changed when the transaction is already
        confirmed (done)."""
        original_mihpayid = "original_12345"
        tx = self._create_transaction(
            "direct", state="done", provider_reference=original_mihpayid
        )
        tx._apply_updates(self.webhook_payment_fail_data)
        self.assertEqual(
            tx.provider_reference,
            original_mihpayid,
            msg="The provider reference should not be updated if the transaction is already"
            " confirmed.",
        )

    def test_search_by_reference_returns_payment_tx(self):
        """Test that _search_by_reference returns the correct transaction for payment data."""
        tx = self._create_transaction("direct")
        returned_tx = self.env["payment.transaction"]._search_by_reference(
            "payu",
            self.webhook_payment_data,
        )
        self.assertEqual(returned_tx, tx)

    def test_search_by_reference_returns_refund_tx(self):
        """Test that _search_by_reference returns the correct transaction for refund data
        using the 'token' field as the reference."""
        tx = self._create_transaction("direct")
        returned_tx = self.env["payment.transaction"]._search_by_reference(
            "payu",
            self.webhook_refund_data,
        )
        self.assertEqual(returned_tx, tx)

    def test_extract_amount_data_for_payment(self):
        """Test that _extract_amount_data correctly extracts amount and currency for payment."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_payment_data)
        self.assertEqual(amount_data["amount"], self.amount)
        self.assertEqual(amount_data["currency_code"], "INR")

    def test_extract_amount_data_for_refund(self):
        """Test that _extract_amount_data correctly extracts amount from refund data
        using the 'amt' key."""
        tx = self._create_transaction("direct")
        amount_data = tx._extract_amount_data(self.webhook_refund_data)
        self.assertEqual(amount_data["amount"], self.amount)
        self.assertEqual(amount_data["currency_code"], "INR")

    def test_apply_updates_triggers_refund_post_processing(self):
        """Test that processing a refund webhook triggers the post-processing cron."""
        tx = self._create_transaction("direct")
        with patch.object(
            type(self.env.ref("payment.cron_post_process_payment_tx")), "_trigger"
        ) as trigger_mock:
            tx._apply_updates(self.webhook_refund_data)
        self.assertEqual(trigger_mock.call_count, 1)

    def test_send_refund_request_payload(self):
        """Test that the refund request is sent with the correct payload structure."""
        source_tx = self._create_transaction(
            "direct", state="done", provider_reference=self.mihpayid
        )
        refund_tx = source_tx._create_child_transaction(
            self.amount,
            is_refund=True,
        )
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
        ) as mock_request:
            refund_tx._send_refund_request()
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            self.assertEqual(call_args[0][0], "POST")
            self.assertIn("/merchant/postservice", call_args[0][1])
            payload = call_args[1].get("data", {})
            self.assertEqual(payload["key"], self.payu_merchant_key)
            self.assertEqual(payload["command"], "cancel_refund_transaction")
            self.assertEqual(payload["var1"], self.mihpayid)
            self.assertIn("hash", payload)
