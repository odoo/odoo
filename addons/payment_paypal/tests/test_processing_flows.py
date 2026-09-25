# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaypalCommon, PaymentHttpCommon):
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch(
                "odoo.addons.payment_paypal.controllers.main.PaypalController"
                "._verify_notification_origin"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paypal.controllers.main", "odoo.http")
    def test_webhook_notification_skips_processing_for_errored_txs(self):
        self._create_transaction("direct")
        PaymentTransaction = self.env.registry["payment.transaction"]
        PaymentProvider = self.env.registry["payment.provider"]
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            patch.object(
                PaymentProvider, "_send_api_request", side_effect=ValidationError("Test error")
            ),
            patch.object(PaymentTransaction, "_record") as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_triggers_origin_check(self):
        """Test that receiving a webhook notification triggers an origin check."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ) as origin_check_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(origin_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_order_declined_webhook_errors_transaction(self):
        """Test that a `CHECKOUT.ORDER.DECLINED` webhook notification errors the transaction."""
        self._disable_process_patcher()
        tx = self._create_transaction("redirect")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=self.declined_notification)
        self._run_processing()
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.state_message, "The provided payment source cannot be used.")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_capture_denied_webhook_updates_tx_error_status(self):
        """Test that a `PAYMENT.CAPTURE.DENIED` webhook notification cancels the transaction.

        The transaction is matched through the order id (`provider_reference`) as the denied capture
        resource does not echo back the shared reference_id.
        """
        self._disable_process_patcher()
        tx = self._create_transaction("redirect")
        self._update_transaction(tx, provider_reference=self.order_id)
        denied_notification = {
            "event_type": "PAYMENT.CAPTURE.DENIED",
            "resource": {
                "id": "8SS60826HT082593F",
                "status": "DECLINED",
                "amount": {"currency_code": self.currency.name, "value": str(self.amount)},
                "supplementary_data": {"related_ids": {"order_id": self.order_id}},
            },
        }
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=denied_notification)
        self._run_processing()
        self.assertEqual(tx.state, "error")

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_deferred_vaulting_creates_token_from_webhook(self):
        """A wallet vaulted asynchronously (vault.status APPROVED, no vault id) is tokenized from
        the VAULT.PAYMENT-TOKEN.CREATED webhook, correlated through the order id."""
        self._disable_process_patcher()
        paypal_pm = self.env.ref("payment_paypal.payment_method_paypal").id
        tx = self._create_transaction("direct", payment_method_id=paypal_pm, tokenize=True)
        vault_id = "VAULT456"
        approved_capture = {
            "status": "COMPLETED",
            "id": self.order_id,
            "txn_type": "CAPTURE",
            "reference_id": self.reference,
            "amount": {"currency_code": self.currency.name, "value": str(self.amount)},
            "payment_source": {"paypal": {"attributes": {"vault": {"status": "APPROVED"}}}},
        }
        tx.with_context(payment_safe_write=True)._process(approved_capture)
        self.assertEqual(tx.state, "done")
        self.assertFalse(tx.token_id, "No token should be created before the vault webhook.")

        notification = {
            "event_type": "VAULT.PAYMENT-TOKEN.CREATED",
            "resource": {
                "id": vault_id,
                "metadata": {"order_id": self.order_id},
                "payment_source": {"paypal": {"email_address": "buyer@example.com"}},
            },
        }
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ):
            self._make_json_request(url, data=notification)
        self._run_processing()
        tx.invalidate_recordset()
        self.assertTrue(tx.token_id, "The vault webhook should create the token.")
        self.assertEqual(tx.token_id.provider_ref, vault_id)
        self.assertEqual(tx.token_id.payment_details, "buyer@example.com")
        self.assertFalse(tx.tokenize)
