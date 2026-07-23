# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import release
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_adyen import const
from odoo.addons.payment_adyen.tests.common import AdyenCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AdyenCommon):
    def test_no_item_missing_from_processing_values(self):
        tx = self._create_transaction(flow="direct")
        with (
            mute_logger("odoo.addons.payment.models.payment_transaction"),
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
        ):
            processing_values = tx._get_specific_processing_values({
                "reference": tx.reference,
                "partner_id": tx.partner_id.id,
            })

        converted_amount = 111111
        self.assertDictEqual(
            processing_values,
            {
                "converted_amount": converted_amount,
                "access_token": self._generate_test_access_token(
                    tx.reference, converted_amount, tx.currency_id.id, tx.partner_id.id
                ),
            },
        )

    def test_application_info_passed_in_token_payment_request(self):
        """Ensure applicationInfo is added correctly to the token payment request payload."""
        tx = self._create_transaction("token", token_id=self._create_token().id)
        with self._mock_send_api_request(return_value={"dummy": "dummy"}) as mock_make_request:
            tx._send_payment_request()
        application_info = mock_make_request.call_args.kwargs["json"].get("applicationInfo")
        self.assertDictEqual(
            application_info,
            {
                "externalPlatform": {
                    "name": "Odoo",
                    "version": release.version,
                    "integrator": "Odoo SA",
                }
            },
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_capture_request_leaves_transaction_authorized(self):
        """Test that sending a capture request only records Adyen's 'received' acknowledgment and
        does not itself confirm the transaction; confirmation only happens later, when a CAPTURE
        webhook notification reports the actual outcome."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", state="authorized")

        with self._mock_send_api_request(return_value={"status": "received"}):
            tx._capture()
        self.assertEqual(
            tx.state,
            "authorized",
            msg="A capture request as been made, but the state of the transaction stays as"
            " 'authorized' until a success notification is sent",
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_partial_capture_request_leaves_transactions_authorized(self):
        """Test that sending a partial capture request only records Adyen's 'received'
        acknowledgment and does not itself confirm the source or child transaction."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", state="authorized")

        with self._mock_send_api_request(return_value={"status": "received"}):
            tx._capture(amount_to_capture=10)
        self.assertEqual(
            tx.state,
            "authorized",
            msg="A partial capture request as been made, but the state of the source transaction"
            " stays as 'authorized' until the full amount is either done or canceled.",
        )
        self.assertEqual(
            tx.child_transaction_ids[0].state,
            "draft",
            msg="A partial capture request as been made, but the state of the child transaction"
            " stays as 'draft' until a success notification is sent.",
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_void_request_leaves_transaction_authorized(self):
        """Test that sending a void request only records Adyen's 'received' acknowledgment and
        does not itself cancel the transaction; cancellation only happens later, when a
        CANCELLATION webhook notification reports the actual outcome."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", state="authorized")

        with self._mock_send_api_request(return_value={"status": "received"}):
            tx._void()
        self.assertEqual(
            tx.state,
            "authorized",
            msg="A void request as been made, but the state of the transaction stays as"
            " 'authorized' until a success notification is sent",
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_refund_creates_refund_tx(self):
        self.provider.support_refund = "full_only"  # Should simply not be False
        tx = self._create_transaction(
            "redirect", state="done", provider_reference="source_reference"
        )

        # Send the refund request
        with self._mock_send_api_request(
            return_value={"pspReference": "refund_reference", "status": "received"}
        ):
            tx._refund()

        refund_tx = self.env["payment.transaction"].search([("source_transaction_id", "=", tx.id)])
        self.assertTrue(refund_tx)
        self.assertEqual(refund_tx.operation, "refund")
        self.assertEqual(refund_tx.amount, -tx.amount)

    def test_search_by_reference_returns_refund_tx(self):
        source_tx = self._create_transaction(
            "direct", state="done", provider_reference=self.original_reference
        )
        refund_tx = self._create_transaction(
            "direct",
            reference="RefundTx",
            provider_reference=self.psp_reference,
            amount=-source_tx.amount,
            operation="refund",
            source_transaction_id=source_tx.id,
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(
                    source_tx.amount, refund_tx.currency_id
                ),
            },
            eventCode="REFUND",
        )
        returned_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertEqual(returned_tx, refund_tx, msg="The existing refund tx is the one returned")

    def test_search_by_reference_creates_refund_tx_when_missing(self):
        source_tx = self._create_transaction(
            "direct", state="done", provider_reference=self.original_reference
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(self.amount, source_tx.currency_id),
            },
            eventCode="REFUND",
        )
        refund_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertTrue(
            refund_tx,
            msg="If no refund tx is found with received refund data, a refund tx should be created",
        )
        self.assertNotEqual(refund_tx, source_tx)
        self.assertEqual(refund_tx.source_transaction_id, source_tx)

    def test_search_by_reference_returns_partial_capture_child_tx(self):
        self.provider.capture_manually = True
        source_tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference
        )
        capture_tx = self._create_transaction(
            "direct",
            reference="CaptureTx",
            provider_reference=self.psp_reference,
            amount=source_tx.amount - 10,
            operation=source_tx.operation,
            source_transaction_id=source_tx.id,
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(
                    source_tx.amount - 10, capture_tx.currency_id
                ),
            },
            eventCode="CAPTURE",
        )
        returned_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertEqual(returned_tx, capture_tx, msg="The existing capture tx is the one returned")

    def test_search_by_reference_creates_capture_tx_when_missing(self):
        self.provider.capture_manually = True
        source_tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(
                    self.amount - 10, source_tx.currency_id
                ),
            },
            eventCode="CAPTURE",
        )
        capture_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertTrue(
            capture_tx,
            msg="If no child tx is found with received capture data, a child tx should be created.",
        )
        self.assertNotEqual(capture_tx, source_tx)
        self.assertEqual(capture_tx.source_transaction_id, source_tx)

    def test_search_by_reference_returns_void_tx(self):
        self.provider.capture_manually = True
        source_tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference
        )
        cancel_tx = self._create_transaction(
            "direct",
            reference="CancelTx",
            provider_reference=self.psp_reference,
            amount=source_tx.amount - 10,
            operation=source_tx.operation,
            source_transaction_id=source_tx.id,
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(
                    source_tx.amount - 10, cancel_tx.currency_id
                ),
            },
            eventCode="CANCELLATION",
        )
        returned_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertEqual(returned_tx, cancel_tx, msg="The existing void tx is the one returned")

    def test_search_by_reference_creates_void_tx_when_missing(self):
        self.provider.capture_manually = True
        source_tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference
        )
        data = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(
                    self.amount - 10, source_tx.currency_id
                ),
            },
            eventCode="CANCELLATION",
        )
        void_tx = self.env["payment.transaction"]._search_by_reference("adyen", data)
        self.assertTrue(
            void_tx,
            msg="If no child tx is found with received void data, a child tx should be created.",
        )
        self.assertNotEqual(void_tx, source_tx)
        self.assertEqual(void_tx.source_transaction_id, source_tx)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_notification_payload)
        self.assertEqual(tx.provider_reference, self.webhook_notification_payload["pspReference"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_notification_payload)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_adyen.payment_method_ach_direct_debit")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_notification_payload)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_authorizes_transaction(self):
        self.provider.capture_manually = True
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates(self.webhook_notification_payload)
        self.assertEqual(
            tx.state,
            "authorized",
            msg="The authorization succeeded, the manual capture is enabled, the tx state should be"
            " 'authorized'.",
        )

    def test_apply_updates_confirms_captured_transaction(self):
        self.provider.capture_manually = True
        tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference, amount=9.99
        )
        payload = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(9.99, tx.currency_id),
            },
            eventCode="CAPTURE",
        )
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(
            tx.state, "done", msg="The capture succeeded, the tx state should be 'done'."
        )

    def test_apply_updates_cancels_authorized_transaction(self):
        tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference, amount=9.99
        )
        payload = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(9.99, tx.currency_id),
            },
            eventCode="CANCELLATION",
            resultCode="Cancelled",
        )
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(
            tx.state, "cancel", msg="The cancellation succeeded, the tx state should be 'cancel'."
        )

    def test_apply_updates_confirms_refund(self):
        source_tx = self._create_transaction(
            "direct", state="done", provider_reference=self.original_reference
        )
        refund_tx = self._create_transaction(
            "direct",
            reference="RefundTx",
            provider_reference=self.psp_reference,
            amount=-source_tx.amount,
            operation="refund",
            source_transaction_id=source_tx.id,
        )
        payload = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(self.amount, source_tx.currency_id),
            },
            eventCode="REFUND",
        )
        refund_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(refund_tx.state, "done")

    def test_apply_updates_leaves_transaction_in_draft_on_failed_authorization(self):
        tx = self._create_transaction("direct")
        payload = dict(self.webhook_notification_payload, success="false", resultCode=None)
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(tx.state, "draft")

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_apply_updates_leaves_transaction_authorized_on_failed_capture(self):
        tx = self._create_transaction(
            "direct", state="authorized", provider_reference=self.original_reference
        )
        payload = dict(
            self.webhook_notification_payload,
            eventCode="CAPTURE",
            success="false",
            resultCode="Error",
        )
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(
            tx.state,
            "authorized",
            msg="The capture failed, the tx state should still be 'authorized'.",
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_apply_updates_leaves_transaction_authorized_on_failed_cancellation(self):
        tx = self._create_transaction("direct", state="authorized")
        payload = dict(
            self.webhook_notification_payload,
            eventCode="CANCELLATION",
            success="false",
            resultCode="Error",
        )
        tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(
            tx.state,
            "authorized",
            msg="The cancellation failed, the tx state should still be 'authorized'.",
        )

    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_apply_updates_sets_refund_transaction_in_error(self):
        source_tx = self._create_transaction(
            "direct", state="done", provider_reference=self.original_reference
        )
        refund_tx = self._create_transaction(
            "direct",
            reference="RefundTx",
            provider_reference=self.psp_reference,
            amount=-source_tx.amount,
            operation="refund",
            source_transaction_id=source_tx.id,
        )
        payload = dict(
            self.webhook_notification_payload,
            amount={
                "currency": self.currency.name,
                "value": payment_utils.to_minor_currency_units(self.amount, source_tx.currency_id),
            },
            eventCode="REFUND",
            success="false",
            resultCode="Error",
        )
        refund_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(
            refund_tx.state,
            "error",
            msg="After a failed refund notification, the refund state should be in 'error'.",
        )

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.webhook_notification_payload)
        self.assertDictEqual(
            amount_data,
            {
                "amount": tx.amount,
                "currency_code": tx.currency_id.name,
                "precision_digits": const.CURRENCY_DECIMALS.get(tx.currency_id.name),
            },
        )

    def test_extract_token_values_maps_fields_correctly(self):
        tx = self._create_transaction("direct")
        payment_data = {
            "additionalData": {
                "recurring.recurringDetailReference": "token_reference",
                "cardSummary": "4242",
                "recurring.shopperReference": "partner_reference",
            }
        }
        token_values = tx._extract_token_values(payment_data)
        self.assertDictEqual(
            token_values,
            {
                "provider_ref": "token_reference",
                "payment_details": "4242",
                "adyen_shopper_reference": "partner_reference",
            },
        )
