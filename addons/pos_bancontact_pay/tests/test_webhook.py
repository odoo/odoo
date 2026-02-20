import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_bancontact_pay.errors.exceptions import BancontactSignatureValidationError


@tagged("post_install", "-at_install")
class TestWebhook(CommonPosTest, TestPointOfSaleHttpCommon):

    def setUp(self):
        super().setUp()
        self.test_ppid = "test_bancontact_ppid"
        self.web_hook_payload_base = {"transferAmount": 100, "amount": 100, "currency": "EUR"}

        self.bancontact_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bancontact Pay',
            'bancontact_ppid': self.test_ppid,
            'journal_id': self.company_data['default_journal_bank'].id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
        })

        self.pos_config_usd.write({
            'payment_method_ids': [(4, self.bancontact_payment_method.id, 0)],
        })

    # ----- Payment Status ----- #
    def test_bancontact_webhook_payment_status_done(self):
        pos_payment, payload = self._make_payment_and_payload("succeeded_id", "waitingScan", "succeeded_qr_code")

        with self._notify_patcher(pos_payment) as mock_notify:
            self._post_status(payload, "SUCCEEDED")
            self.assertEqual(pos_payment.payment_status, "done")
            self.assertFalse(pos_payment.qr_code)
            self.assertEqual(pos_payment.bancontact_id, "succeeded_id")
            self._assert_notify_called_once(mock_notify, pos_payment, "SUCCEEDED")

    def test_bancontact_webhook_payment_status_done_ignore(self):
        pos_payment, payload = self._make_payment_and_payload("not_updated", "done", "not_updated_qr_code")

        with self._notify_patcher(pos_payment) as mock_notify:
            for status in ("SUCCEEDED", "CANCELLED"):
                self._post_status(payload, status)
                self.assertEqual(pos_payment.payment_status, "done")
                self.assertEqual(pos_payment.qr_code, "not_updated_qr_code")
                self.assertEqual(pos_payment.bancontact_id, "not_updated")

            mock_notify.assert_not_called()

    def test_bancontact_webhook_payment_status_error(self):
        for bancontact_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
            pos_payment, payload = self._make_payment_and_payload("error_id", "waitingScan", "error_qr_code")

            with self._notify_patcher(pos_payment) as mock_notify:
                self._post_status(payload, bancontact_status)
                self.assertEqual(pos_payment.payment_status, "retry")
                self.assertFalse(pos_payment.qr_code)
                self.assertFalse(pos_payment.bancontact_id)
                self._assert_notify_called_once(mock_notify, pos_payment, bancontact_status)

    def test_bancontact_webhook_payment_status_error_ignore(self):
        pos_payment, payload = self._make_payment_and_payload("not_updated", "retry", "not_updated_qr_code")

        with self._notify_patcher(pos_payment) as mock_notify:
            for status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"):
                self._post_status(payload, status)
                self.assertEqual(pos_payment.payment_status, "retry")
                self.assertEqual(pos_payment.qr_code, "not_updated_qr_code")
                self.assertEqual(pos_payment.bancontact_id, "not_updated")

            mock_notify.assert_not_called()

    # ----- Errors ----- #
    def test_bancontact_webhook_payment_not_found(self):
        response = self._post_bancontact_webhook({"paymentId": "not_found_id"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, "Payment not found.")

    def test_bancontact_webhook_invalid_signature(self):
        with self.mock_bancontact_signature_validation_error(verify_signature=True):
            response = self._post_bancontact_webhook({"paymentId": "any_id"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.text, "MOCK: Invalid signature")

    def test_bancontact_webhook_subject_mismatch(self):
        _pos_payment, payload = self._make_payment_and_payload("subject_mismatch_id", "waitingScan", "subject_mismatch_qr_code")

        with self.mock_bancontact_signature_validation_error(verify_subject=True):
            response = self._post_bancontact_webhook(payload)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.text, "MOCK: Subject mismatch")

    # ----- Helpers ----- #
    def _make_payment_and_payload(self, bancontact_id, payment_status, qr_code):
        pos_payment = self._init_bancontact_pos_payment(bancontact_id, payment_status, qr_code)
        payload = dict(self.web_hook_payload_base, paymentId=bancontact_id)
        return pos_payment, payload

    def _notify_patcher(self, pos_payment):
        return patch.object(pos_payment.pos_order_id.config_id.__class__, "_notify")

    def _assert_notify_called_once(self, mock_notify, pos_payment, bancontact_status):
        mock_notify.assert_called_once_with(
            "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
            {
                "order_id": pos_payment.pos_order_id.id,
                "payment_id": pos_payment.id,
                "bancontact_status": bancontact_status,
            },
        )

    def _init_bancontact_pos_payment(self, bancontact_id, payment_status, qr_code):
        order, _ = self.create_backend_pos_order(
            {
                "line_data": [
                    {"product_id": self.ten_dollars_no_tax.product_variant_id.id},
                ],
            },
        )
        return self.env["pos.payment"].create(
            {
                "amount": 100,
                "payment_status": payment_status,
                "bancontact_id": bancontact_id,
                "payment_method_id": self.bancontact_payment_method.id,
                "pos_order_id": order.id,
                "qr_code": qr_code,
            },
        )

    def _post_bancontact_webhook(self, payload):
        return self.url_open(
            "/bancontact_pay/webhook?mode=test",
            data=json.dumps(payload),
            headers={"content-type": "application/json"},
            method="POST",
        )

    def _post_status(self, payload, status):
        payload["status"] = status
        response = self._post_bancontact_webhook(payload)
        self.assertEqual(response.status_code, 200)
        return response

    # ----- Context Manager ----- #
    @contextmanager
    def mock_bancontact_signature_validation_error(self, verify_signature=None, verify_subject=None):
        with patch("odoo.addons.pos_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_signature") as verify_signature_mock, \
             patch("odoo.addons.pos_bancontact_pay.controllers.signature.BancontactSignatureValidation.verify_subject") as verify_subject_mock:
            if verify_signature:
                verify_signature_mock.side_effect = BancontactSignatureValidationError("MOCK: Invalid signature")
            if verify_subject:
                verify_subject_mock.side_effect = BancontactSignatureValidationError("MOCK: Subject mismatch")
            yield
