from odoo.tests.common import tagged

from odoo.addons.pos_bancontact_pay.tests.test_webhook import TestWebhook


@tagged("post_install", "-at_install")
class TestSelfOrderWebhook(TestWebhook):
    def setUp(self):
        super().setUp()
        self.kiosk = self.env["pos.config"].create(
            {
                "name": "Kiosk Test",
                "self_ordering_default_user_id": self.pos_user.id,
                "self_ordering_mode": "kiosk",
                "self_ordering_pay_after": "each",
                "payment_method_ids": [(4, self.bank_payment_method.id)],
            },
        )

    def test_bancontact_webhook_success(self):
        payload = self._make_payload("any_id", "SUCCEEDED")

        with self._notify_patcher() as mock_notify:
            response = self._post_bancontact_webhook(self.kiosk.id, payload)
            self.assertEqual(response.status_code, 200)
            self._assert_notify_count(mock_notify, "FINALIZE_KIOSK_PAYMENT", 1)
            self._assert_notify_finalize_kiosk_payment(mock_notify, "any_id", "SUCCEEDED")

    def test_bancontact_webhook_error(self):
        for bancontact_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            payload = self._make_payload("any_id", bancontact_status)

            with self._notify_patcher() as mock_notify:
                response = self._post_bancontact_webhook(self.kiosk.id, payload)
                self.assertEqual(response.status_code, 200)
                self._assert_notify_count(mock_notify, "FINALIZE_KIOSK_PAYMENT", 1)
                self._assert_notify_finalize_kiosk_payment(mock_notify, "any_id", bancontact_status)

    def _assert_notify_finalize_kiosk_payment(self, mock_notify, bancontact_id, bancontact_status):
        error = None
        if bancontact_status == "CANCELLED":
            error = "Payment cancelled"
        elif bancontact_status == "EXPIRED":
            error = "Payment expired"

        expected_payload = {
            "status": "success" if bancontact_status == "SUCCEEDED" else "fail",
            "error": error,
            "bancontact_id": bancontact_id,
        }
        self._assert_notify_with(mock_notify, "FINALIZE_KIOSK_PAYMENT", expected_payload)
