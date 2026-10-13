from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user, tagged
from odoo.tools import verify_hash_signed

from odoo.addons.pos_mollie.tests.common import TestMollieCommon


@tagged("post_install", "-at_install")
class TestMolliePaymentMethod(TestMollieCommon):
    # ----- Create Payment -------

    def test_payment(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=self._mollie_payment(),
        ) as mock_request:
            result = self.mollie_payment_method.mollie_create_payment(5.00, "uuid", self.pos_session.id)
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], f"pos_session_id={self.pos_session.id},payment_uuid=uuid")
        self.assertEqual(payload["method"], "pointofsale")
        self.assertEqual(payload["terminalId"], self.mollie_payment_method.mollie_terminal_id)
        self.assertEqual(payload["metadata"], {
            "payment_uuid": "uuid",
            "payment_method_id": self.mollie_payment_method.id,
            "pos_session_id": self.pos_session.id,
        })
        self.assertEqual(result["payment_id"], "tr_test")
        signed_payload = payload["webhookUrl"].split("/pos_mollie/webhook?payload=")[1]
        self.assertEqual(verify_hash_signed(self.env, "pos_mollie", signed_payload), payload["metadata"])

    def test_payment_no_api_key(self):
        self.mollie_payment_method.sudo().mollie_payment_provider_id.mollie_api_key = False
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            with self.assertRaises(ValidationError):
                self.mollie_payment_method.mollie_create_payment(5.00, "uuid", self.pos_session.id)
        mock_request.assert_not_called()

    def test_payment_without_pos_rights(self):
        user = new_test_user(self.env, login="mollie_no_pos", groups="base.group_user")
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            with self.assertRaises(AccessError):
                self.mollie_payment_method.with_user(user).mollie_create_payment(5.00, "uuid", self.pos_session.id)
        mock_request.assert_not_called()

    def test_payment_method_not_in_session(self):
        other_payment_method = self.mollie_payment_method.sudo().copy().with_user(self.pos_user)
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            for payment_method, pos_session_id in [
                (other_payment_method, self.pos_session.id),
                (self.mollie_payment_method, self.pos_session.id + 1000),
            ]:
                with self.subTest(payment_method=payment_method, pos_session_id=pos_session_id), self.assertRaises(ValidationError):
                    payment_method.mollie_create_payment(5.00, "uuid", pos_session_id)
        mock_request.assert_not_called()

    def test_payment_closed_session(self):
        self.pos_session.state = "closed"
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            with self.assertRaises(ValidationError):
                self.mollie_payment_method.mollie_create_payment(5.00, "uuid", self.pos_session.id)
        mock_request.assert_not_called()

    # ----- Refund -------

    def test_refund(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=[
                self._mollie_payment(status="paid"),
                {"id": "re_test", "status": "pending", "metadata": None},
            ],
        ) as mock_request:
            result = self.mollie_payment_method.mollie_create_refund("tr_test", 5.00, "uuid", self.pos_session.id)
            (get_method, get_path), (method, path) = [call.args for call in mock_request.call_args_list]
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(get_method, "GET")
        self.assertEqual(get_path, "/payments/tr_test")
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments/tr_test/refunds")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], f"pos_session_id={self.pos_session.id},payment_uuid=uuid")
        self.assertEqual(result["payment_id"], "re_test")
        self.assertEqual(result["status"], "pending")

    def test_refund_previous_session(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=[
                self._mollie_payment(status="paid", pos_session_id=self.pos_session.id - 1),
                {"id": "re_test", "status": "pending", "metadata": None},
            ],
        ):
            result = self.mollie_payment_method.mollie_create_refund("tr_test", 5.00, "uuid", self.pos_session.id)

        self.assertEqual(result["payment_id"], "re_test")

    def test_refund_foreign_payment(self):
        foreign_payments = [
            {"id": "tr_test", "status": "paid", "metadata": None},
            self._mollie_payment(status="paid", payment_method_id=self.mollie_payment_method.id + 1),
        ]
        for mollie_payment in foreign_payments:
            with self.subTest(mollie_payment=mollie_payment), patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=mollie_payment,
            ) as mock_request:
                with self.assertRaises(ValidationError):
                    self.mollie_payment_method.mollie_create_refund("tr_test", 5.00, "uuid", self.pos_session.id)
                mock_request.assert_called_once_with("GET", "/payments/tr_test")

    # ----- Cancel -------

    def test_cancel(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            side_effect=[self._mollie_payment(), self._mollie_payment(status="canceled")],
        ) as mock_request:
            result = self.mollie_payment_method.mollie_cancel_payment("tr_test", self.pos_session.id)
            (get_method, get_path), (method, path) = [call.args for call in mock_request.call_args_list]

        self.assertEqual(get_method, "GET")
        self.assertEqual(get_path, "/payments/tr_test")
        self.assertEqual(method, "DELETE")
        self.assertEqual(path, "/payments/tr_test")
        self.assertEqual(result["status"], "canceled")

    def test_cancel_closed_session(self):
        self.pos_session.state = "closed"
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            with self.assertRaises(ValidationError):
                self.mollie_payment_method.mollie_cancel_payment("tr_test", self.pos_session.id)
        mock_request.assert_not_called()

    def test_cancel_foreign_payment(self):
        foreign_payments = [
            {"id": "tr_test", "status": "open", "metadata": None},
            self._mollie_payment(payment_method_id=self.mollie_payment_method.id + 1),
            self._mollie_payment(pos_session_id=self.pos_session.id + 1),
        ]
        for mollie_payment in foreign_payments:
            with self.subTest(mollie_payment=mollie_payment), patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=mollie_payment,
            ) as mock_request:
                with self.assertRaises(ValidationError):
                    self.mollie_payment_method.mollie_cancel_payment("tr_test", self.pos_session.id)
                mock_request.assert_called_once_with("GET", "/payments/tr_test")

    # ----- Get Payment -------

    def test_get(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=self._mollie_payment(),
        ) as mock_request:
            result = self.mollie_payment_method.mollie_get_payment("tr_test", self.pos_session.id, "uuid")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "GET")
        self.assertEqual(path, "/payments/tr_test")
        self.assertEqual(result["payment_id"], "tr_test")
        self.assertEqual(result["status"], "open")

    def test_get_paid(self):
        mollie_payment = self._mollie_payment() | {
            "status": "paid",
            "details": {"cardFunding": "debit", "cardNumber": "1234", "cardLabel": "Visa"},
        }
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=mollie_payment,
        ):
            result = self.mollie_payment_method.mollie_get_payment("tr_test", self.pos_session.id)

        self.assertEqual(result["card_type"], "debit")
        self.assertEqual(result["card_no"], "1234")
        self.assertEqual(result["card_brand"], "Visa")

    def test_get_unsuccessful(self):
        status_reason = {"code": "insufficient_funds", "message": "Insufficient funds"}
        for status in ["failed", "expired", "canceled"]:
            mollie_payment = self._mollie_payment(status=status) | {"statusReason": status_reason}
            with self.subTest(status=status), patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=mollie_payment,
            ):
                result = self.mollie_payment_method.mollie_get_payment("tr_test", self.pos_session.id)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["status_reason"], status_reason)
                self.assertNotIn("card_no", result)

    def test_get_foreign_payment(self):
        foreign_payments = [
            {"id": "tr_test", "status": "open", "metadata": None},
            self._mollie_payment(payment_method_id=self.mollie_payment_method.id + 1),
            self._mollie_payment(pos_session_id=self.pos_session.id + 1),
            self._mollie_payment(payment_uuid="other_uuid"),
        ]
        for mollie_payment in foreign_payments:
            with self.subTest(mollie_payment=mollie_payment), patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value=mollie_payment,
            ), self.assertRaises(ValidationError):
                self.mollie_payment_method.mollie_get_payment("tr_test", self.pos_session.id, "uuid")

    # ----- Payment ID Validation -------

    def test_invalid_payment_id(self):
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            for payment_id in ["", "tr_", "test", "re_test"]:
                with self.subTest(payment_id=payment_id):
                    with self.assertRaises(ValidationError):
                        self.mollie_payment_method.mollie_get_payment(payment_id, self.pos_session.id)
                    with self.assertRaises(ValidationError):
                        self.mollie_payment_method.mollie_cancel_payment(payment_id, self.pos_session.id)
                    with self.assertRaises(ValidationError):
                        self.mollie_payment_method.mollie_create_refund(payment_id, 5.00, "uuid", self.pos_session.id)
        mock_request.assert_not_called()
