from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.tools import hash_sign

from odoo.addons.pos_mollie.tests.common import TestMollieCommon


@tagged("post_install", "-at_install")
class TestMollieWebhook(TestMollieCommon):
    # ----- Helpers -------

    def _signed_payload(self, scope="pos_mollie", **metadata):
        return hash_sign(self.env, scope, {
            "payment_uuid": "uuid",
            "payment_method_id": self.mollie_payment_method.id,
            "pos_session_id": self.pos_session.id,
            **metadata,
        }, expiration_hours=1)

    def _mollie_webhook(self, payment_id, mollie_payment=None, payload=None, side_effect=None):
        if payload is None:
            payload = self._signed_payload()
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=mollie_payment,
                side_effect=side_effect,
            ) as mock_request,
            patch("odoo.addons.point_of_sale.models.pos_bus_mixin.PosBusMixin._notify") as mock_notify,
        ):
            response = self.url_open(f"/pos_mollie/webhook?payload={payload}", data={"id": payment_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "OK")
        return mock_request, mock_notify

    # ----- Valid Webhook -------

    def test_webhook_notifies_the_bus(self):
        mock_request, mock_notify = self._mollie_webhook("tr_test", self._mollie_payment(status="paid"))

        mock_request.assert_called_once_with("GET", "/payments/tr_test")
        mock_notify.assert_called_once()
        notification, payment = mock_notify.call_args.args
        self.assertEqual(notification, "MOLLIE_PAYMENT_STATUS")
        self.assertEqual(payment["payment_id"], "tr_test")
        self.assertEqual(payment["status"], "paid")

    # ----- Invalid Payload -------

    def test_webhook_invalid_signature(self):
        invalid_payloads = {
            "wrong_scope": self._signed_payload(scope="other_scope"),
            "malformed": "not_a_token",
        }
        for case, payload in invalid_payloads.items():
            with self.subTest(case=case), self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
                mock_request, mock_notify = self._mollie_webhook("tr_test", payload=payload)
                mock_request.assert_not_called()
                mock_notify.assert_not_called()

    def test_webhook_expired_signature(self):
        with freeze_time(datetime.now() - timedelta(hours=2)):
            payload = self._signed_payload()
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("tr_test", payload=payload)

        mock_request.assert_not_called()
        mock_notify.assert_not_called()

    # ----- Rejected Payment -------

    def test_webhook_unknown_payment_method(self):
        payload = self._signed_payload(payment_method_id=self.mollie_payment_method.id + 1000)
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("tr_test", payload=payload)

        mock_request.assert_not_called()
        mock_notify.assert_not_called()

    def test_webhook_invalid_payment_id(self):
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("re_test")

        mock_request.assert_not_called()
        mock_notify.assert_not_called()

    def test_webhook_closed_session(self):
        self.pos_session.state = "closed"
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("tr_test", self._mollie_payment(status="paid"))

        mock_request.assert_not_called()
        mock_notify.assert_not_called()

    def test_webhook_foreign_payment(self):
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("tr_other", self._mollie_payment(payment_uuid="other_uuid"))

        mock_request.assert_called_once_with("GET", "/payments/tr_other")
        mock_notify.assert_not_called()

    def test_webhook_mollie_api_error(self):
        with self.assertLogs("odoo.addons.pos_mollie.controllers.webhook", level="WARNING"):
            mock_request, mock_notify = self._mollie_webhook("tr_test", side_effect=ValidationError("Mollie is down"))

        mock_request.assert_called_once_with("GET", "/payments/tr_test")
        mock_notify.assert_not_called()
