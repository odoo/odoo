# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.addons.payment_stripe.tests.common import StripeCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(StripeCommon):
    def test_no_item_missing_from_processing_values(self):
        dummy_client_secret = "pi_123456789_secret_dummy_123456789"
        tx = self._create_transaction(flow="direct")  # We don't really care what the flow is here.

        with (
            patch(
                "odoo.addons.payment_stripe.models.payment_transaction.PaymentTransaction"
                "._stripe_create_intent",
                return_value={"client_secret": dummy_client_secret},
            ),
            mute_logger("odoo.addons.payment.models.payment_transaction"),
        ):
            processing_values = tx._get_specific_processing_values(None)

        base_url = self.provider.get_base_url()
        return_url = url_join(
            base_url, f"{StripeController._return_url}?{url_encode({'reference': tx.reference})}"
        )
        self.assertDictEqual(
            processing_values, {"client_secret": dummy_client_secret, "return_url": return_url}
        )

    def test_no_item_missing_from_payment_intent_request_payload(self):
        """Test that the payment intent request values are conform to the transaction fields."""
        tx = self._create_transaction(flow="direct")
        self.maxDiff = 10000  # Allow comparing large dicts.
        with patch(
            "odoo.addons.payment_stripe.models.payment_transaction.PaymentTransaction"
            "._stripe_create_customer",
            return_value={"id": "cus_1234567890ABCDE"},
        ):
            request_payload = tx._stripe_prepare_payment_intent_payload()
        converted_amount = payment_utils.to_minor_currency_units(
            tx.amount,
            tx.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(tx.currency_id.name),
        )
        self.assertDictEqual(
            request_payload,
            {
                "amount": converted_amount,
                "currency": tx.currency_id.name.lower(),
                "description": tx.reference,
                "capture_method": "automatic",
                "payment_method_types[]": tx.payment_method_code,
                "expand[]": "payment_method",
                "customer": "cus_1234567890ABCDE",
            },
        )

    @mute_logger("odoo.addons.payment_stripe.models.payment_transaction")
    def test_refund_creates_refund_tx(self):
        """Test that refunding a transaction creates a refund transaction."""
        tx = self._create_transaction("redirect", state="done")
        with self._mock_send_api_request(return_value=self.refund_object):
            tx._refund()
        refund_tx = self.env["payment.transaction"].search([("source_transaction_id", "=", tx.id)])
        self.assertTrue(refund_tx)
        self.assertEqual(refund_tx.operation, "refund")
        self.assertEqual(refund_tx.amount, -tx.amount)

    @mute_logger("odoo.addons.payment_stripe.models.payment_transaction")
    def test_refund_id_is_set_as_provider_reference(self):
        """Test that the id of the refund object is set as the provider reference of the refund
        transaction."""
        source_tx = self._create_transaction("redirect", state="done")
        with (
            self._mock_send_api_request(return_value=self.refund_object),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            source_tx._refund()
        payload = record_mock.call_args.args[0]
        self.assertEqual(payload["refund"]["id"], self.refund_object["id"])

    @mute_logger("odoo.addons.payment_stripe.models.payment_transaction")
    def test_capture_confirms_tx(self):
        """Test that capturing an authorized transaction sets the capture tx to 'done'."""
        self.provider.capture_manually = True
        tx = self._create_transaction("direct", state="authorized")

        with (
            self._mock_send_api_request(
                return_value={
                    "id": "pi_3KTk9zAlCFm536g81Wy7RCPH",
                    "status": "succeeded",
                    **self.notification_amount_and_currency,
                }
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            captured_tx = tx._capture()
        payload = record_mock.call_args.args[0]
        captured_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(captured_tx.state, "done")

    @mute_logger("odoo.addons.payment_stripe.models.payment_transaction")
    def test_void_cancels_tx(self):
        """Test that voiding an authorized transaction sets the void tx to 'cancel'."""
        self.provider.capture_manually = True
        tx = self._create_transaction("redirect", state="authorized")

        with (
            self._mock_send_api_request(
                return_value={
                    "id": "pi_3KTk9zAlCFm536g81Wy7RCPH",
                    "status": "canceled",
                    **self.notification_amount_and_currency,
                }
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            void_tx = tx._void()
        payload = record_mock.call_args.args[0]
        void_tx.with_context(payment_safe_write=True)._apply_updates(payload)
        self.assertEqual(void_tx.state, "cancel")

    def test_extract_reference_finds_reference(self):
        """Test that the transaction is found from the reference included in the payment data."""
        tx = self._create_transaction("redirect")
        found_tx = self.env["payment.transaction"]._search_by_reference(
            "stripe", {"reference": tx.reference}
        )
        self.assertEqual(tx, found_tx)

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.online_payment_data)
        self.assertEqual(tx.provider_reference, self.payment_intent_data["id"])

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated from the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.online_payment_data)
        self.assertEqual(
            tx.payment_method_id, self.env.ref("payment_stripe.payment_method_ach_direct_debit")
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.online_payment_data)
        self.assertEqual(tx.state, "done")

    def test_validate_amount_succeeds_for_special_currencies(self):
        for currency_code in const.CURRENCY_DECIMALS:
            currency = self._enable_currency(currency_code)
            tx = self._create_transaction(
                "dummy",
                operation="online_direct",
                amount=15,
                currency_id=currency.id,
                reference=f"test_{currency_code}",
            )
            data = self.payment_data["data"]
            with patch(
                "odoo.addons.payment_stripe.models.payment_transaction.PaymentTransaction"
                "._stripe_create_customer",
                return_value={"id": "cus_1234567890ABCDE"},
            ):
                data["payment_intent"] = tx._stripe_prepare_payment_intent_payload()
            tx._validate_amount(data)
            self.assertNotEqual(tx.state, "error")

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.online_payment_data)
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
            "payment_intent": {"charges": {"data": [{}]}, "customer": "test_customer"},
            "payment_method": {
                "card": {"brand": "visa", "last4": "1111"},
                "id": "pm_test",
                "object": "payment_method",
                "type": "card",
            },
        }
        token_values = tx._extract_token_values(payment_data)
        self.assertDictEqual(
            token_values,
            {
                "payment_details": "1111",
                "provider_ref": "test_customer",
                "stripe_mandate": None,
                "stripe_payment_method": "pm_test",
            },
        )
