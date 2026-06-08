import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_bancontact_pay.errors.exceptions import BancontactSignatureValidationError


@tagged("post_install", "-at_install")
class TestWebhook(CommonPosTest, TestPointOfSaleHttpCommon):
    # ----- Payment Status ----- #
    def test_bancontact_webhook(self):
        payload = self._make_payload("any_id", "any_status")

        response = self._post_bancontact_webhook("string_config_id", payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Invalid or missing config_id parameter")

        response = self._post_bancontact_webhook(999, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Invalid POS configuration ID")

        with self.mock_bancontact_signature_validation_error(verify_signature=True):
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.text, "MOCK: Invalid signature")

        with self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
            self.assertEqual(response.status_code, 204)
            self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 0)

        for bancontact_status in ("SUCCEEDED", "AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            payload["status"] = bancontact_status
            with self._notify_patcher() as mock_notify:
                response = self._post_bancontact_webhook(self.main_pos_config.id, payload)
                self.assertEqual(response.status_code, 200)
                self._assert_notify_count(mock_notify, "BANCONTACT_PAY_PAYMENTS_NOTIFICATION", 1)
                self._assert_notify_bancontact_pay_payments_notification(mock_notify, "any_id", bancontact_status)

    # ----- Helpers ----- #
    def _make_payload(self, bancontact_id, payment_status):
        return {"transferAmount": 100, "amount": 100, "currency": "EUR", "paymentId": bancontact_id, "status": payment_status}

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

    def _post_bancontact_webhook(self, config_id, payload):
        return self.url_open(
            f"/bancontact_pay/webhook?config_id={config_id}&mode=test",
            data=json.dumps(payload),
            headers={"content-type": "application/json"},
            method="POST",
        )

    # ----- Context Manager ----- #
    @contextmanager
    def mock_bancontact_signature_validation_error(self, verify_signature=None):
        with patch("odoo.addons.pos_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature") as verify_signature_mock:
            if verify_signature:
                verify_signature_mock.side_effect = BancontactSignatureValidationError("MOCK: Invalid signature")
            yield
