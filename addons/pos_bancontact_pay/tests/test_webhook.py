import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.pos_bancontact_pay.errors.exceptions import (
    BancontactSignatureValidationError,
)
from odoo.addons.pos_bancontact_pay.tests.common import TestBancontactPay


@tagged("post_install", "-at_install")
class TestWebhook(TestBancontactPay):
    # ----- Payment Status ----- #
    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook(self):
        payload = self._make_payload("any_id", "any_status")

        with self.mock_verify_signature():
            response = self._post_bancontact_webhook("string_config_id", payload)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.text, "Invalid POS configuration")

            response = self._post_bancontact_webhook(999, payload)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.text, "Invalid POS configuration")

        with self.mock_verify_signature(raise_error=True):
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.text, "Invalid signature")

        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 204)
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

        for bancontact_status in ("SUCCEEDED", "AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            bancontact_id = f"bancontact_{bancontact_status}"
            self._create_pending_payment(bancontact_id)
            payload = self._make_payload(bancontact_id, bancontact_status)
            with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
                response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
                self.assertEqual(response.status_code, 200)
                self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 1)
                self._assert_notify_bancontact_pay_payments_notification(mock_notify, bancontact_id, bancontact_status)

    # ----- Security: payment_method/config binding & already-finalized guard ----- #
    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_rejects_payment_method_not_configured_on_pos(self):
        """A validly signed callback for a real Bancontact payment method that
        simply isn't one of this config's own must be rejected. Without this, an
        attacker with their own (unrelated) Bancontact account could point its
        callback at a victim's config_id while supplying its own payment_method_id,
        since both are plain attacker-controlled URL parameters."""
        payload = self._make_payload("any_bancontact_id", "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload, payment_method_id=self.payment_method_display_2.id)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.text, "Invalid POS configuration")
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_rejects_invalid_payment_method_id(self):
        """A non-existent or non-numeric payment_method_id must be rejected before
        any signature verification is attempted."""
        payload = self._make_payload("any_bancontact_id", "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            for invalid_payment_method_id in (999999, "not_a_number"):
                response = self._post_bancontact_webhook(self.main_pos_config.id, payload, payment_method_id=invalid_payment_method_id)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.text, "Invalid POS configuration")
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_rejects_non_bancontact_payment_method(self):
        """A payment_method_id pointing at a real, configured payment method that
        isn't a Bancontact one at all must be rejected."""
        payload = self._make_payload("any_bancontact_id", "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload, payment_method_id=self.bank_payment_method.id)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.text, "Invalid POS configuration")
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_accepts_unknown_payment_when_payment_method_valid(self):
        """The order/payment may not have synced to the server yet by the time a
        legitimate callback arrives, so finding a matching pos.payment can never be
        a hard requirement - only the payment_method/config binding is. A callback
        for a paymentId not (yet) known to Odoo, but with a properly configured
        payment_method_id, must still be relayed."""
        payload = self._make_payload("not_yet_synced_bancontact_id", "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 200)
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 1)

    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_ignores_already_finalized_payment(self):
        bancontact_id = "bancontact_already_done"
        payment = self._create_pending_payment(bancontact_id)
        payment.payment_status = "done"
        payload = self._make_payload(bancontact_id, "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 204)
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.webhook")
    def test_bancontact_webhook_ignores_non_draft_order(self):
        bancontact_id = "bancontact_order_not_draft"
        payment = self._create_pending_payment(bancontact_id)
        payment.pos_order_id.state = "paid"
        payload = self._make_payload(bancontact_id, "SUCCEEDED")
        with self.mock_verify_signature(), self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 204)
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

    # ----- Helpers ----- #
    def _make_payload(self, bancontact_id, payment_status):
        return {"transferAmount": 100, "amount": 100, "currency": "EUR", "paymentId": bancontact_id, "status": payment_status}

    def _create_pending_payment(self, bancontact_id, config=None, payment_method=None, amount=10.0):
        config = config or self.main_pos_config
        payment_method = payment_method or self.payment_method_display
        if not config.current_session_id:
            config.open_ui()
        order = self.env["pos.order"].create({
            "company_id": config.company_id.id,
            "session_id": config.current_session_id.id,
            "amount_tax": 0,
            "amount_total": amount,
            "amount_paid": amount,
            "amount_return": 0,
        })
        return self.env["pos.payment"].create({
            "pos_order_id": order.id,
            "payment_method_id": payment_method.id,
            "amount": amount,
            "bancontact_id": bancontact_id,
            "payment_status": "waitingScan",
        })

    def _notify_patcher(self):
        return patch.object(self.env["pos.config"].__class__, "_notify")

    def _assert_notify_count(self, mock_notify, name, expected_count):
        calls = [call for call in mock_notify.mock_calls if call.args and call.args[0] == name]
        self.assertEqual(len(calls), expected_count, f"Expected {expected_count} calls to _notify with name '{name}', but got {len(calls)} calls.")

    def _assert_notify_with(self, mock_notify, name, expected_payload):
        args_list = [call.args for call in mock_notify.mock_calls]
        actual = [args == (name, expected_payload) for args in args_list]
        self.assertTrue(any(actual), f"Notification not found\nExpected: {(name, expected_payload)}\nActual: {args_list}")

    def _assert_notify_bancontact_pay_payments_notification(self, mock_notify, bancontact_id, bancontact_status):
        expected_payload = {
            "bancontact_id": bancontact_id,
            "bancontact_status": bancontact_status,
        }
        self._assert_notify_with(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", expected_payload)

    def _post_bancontact_webhook(self, config_id, payload, payment_method_id=None):
        if payment_method_id is None:
            payment_method_id = self.payment_method_display.id
        return self.url_open(
            f"/bancontact_pay/webhook?config_id={config_id}&payment_method_id={payment_method_id}",
            data=json.dumps(payload),
            headers={"content-type": "application/json"},
            method="POST",
        )

    # ----- Context Manager ----- #
    @contextmanager
    def mock_verify_signature(self, raise_error=False):
        with patch("odoo.addons.pos_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature") as verify_signature_mock:
            if raise_error:
                verify_signature_mock.side_effect = BancontactSignatureValidationError("MOCK: Invalid signature")
            yield
