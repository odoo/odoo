# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug import urls

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal import const
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged("post_install", "-at_install")
class TestProcessingFlows(PaypalCommon, PaymentHttpCommon):
    def _build_return_url(self, tx):
        url_params = urls.url_encode({
            "reference": tx.reference,
            "access_token": self._generate_test_access_token(tx.reference),
        })
        return self._build_url(f"{const.PAYMENT_RETURN_ROUTE}?{url_params}")

    def _create_apm_transaction(self):
        bancontact_pm = self.env.ref("payment_paypal.payment_method_bancontact").id
        tx = self._create_transaction("redirect", payment_method_id=bancontact_pm)
        self._update_transaction(tx, provider_reference=self.order_id)
        return tx

    def test_returning_from_payment_triggers_processing(self):
        """Test that returning from PayPal with a valid access token triggers the processing of
        the payment data."""
        tx = self._create_apm_transaction()
        with (
            patch(
                "odoo.addons.payment.utils.generate_access_token",
                new=self._generate_test_access_token,
            ),
            self._mock_send_api_request(return_value=self.payment_data["resource"]),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_http_get_request(self._build_return_url(tx))
        self.assertEqual(record_mock.call_count, 1)

    def test_returning_from_payment_triggers_signature_check(self):
        """Test that returning from PayPal triggers an access token check."""
        tx = self._create_apm_transaction()
        with (
            patch("odoo.addons.payment.utils.check_access_token") as signature_check_mock,
            self._mock_send_api_request(return_value=self.payment_data["resource"]),
            patch("odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"),
        ):
            self._make_http_get_request(self._build_return_url(tx))
        self.assertEqual(
            signature_check_mock.call_args[0][0], self._generate_test_access_token(tx.reference)
        )

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
        url = self._build_url(const.WEBHOOK_ROUTE)
        with (
            self._mock_send_api_request(side_effect=ValidationError("Test error")),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(record_mock.call_count, 0)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("direct")
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            "odoo.addons.payment_paypal.controllers.main.PaypalController"
            "._verify_notification_origin"
        ) as signature_check_mock:
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_order_declined_webhook_records_declined_payment_data(self):
        """Test that a `CHECKOUT.ORDER.DECLINED` webhook notification records payment data with a
        declined status and the error description as state message."""
        self._create_transaction("redirect")
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
            self._make_json_request(url, data=self.declined_notification)
        payment_data = record_mock.call_args.args[0]
        self.assertEqual(payment_data["status"], "DECLINED")
        self.assertEqual(
            payment_data["state_message"], "The provided payment source cannot be used."
        )

    @mute_logger("odoo.addons.payment_paypal.controllers.main")
    def test_capture_denied_webhook_records_payment_data_on_order_tx(self):
        """Test that a `PAYMENT.CAPTURE.DENIED` webhook notification records the payment data on
        the transaction matched through the order id (`provider_reference`), as the denied capture
        resource does not echo back the shared reference_id."""
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
        with (
            patch(
                "odoo.addons.payment_paypal.controllers.main.PaypalController"
                "._verify_notification_origin"
            ),
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            self._make_json_request(url, data=denied_notification)
        self.assertDictEqual(
            record_mock.call_args.args[0],
            {
                "reference_id": tx.reference,
                "id": "8SS60826HT082593F",
                "status": "DECLINED",
                "amount": {"currency_code": self.currency.name, "value": str(self.amount)},
            },
        )

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
