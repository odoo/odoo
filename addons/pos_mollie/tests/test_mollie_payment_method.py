from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestMolliePaymentMethod(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        payment_provider = cls.env["payment.provider"].create({"name": "Mollie Test", "code": "mollie", "mollie_api_key": "mockApiKey"})
        cls.main_pos_config.write({
            "payment_method_ids": [
                (0, 0, {
                    "name": "Mollie",
                    "type": "bank",
                    "payment_provider": "mollie",
                    "mollie_terminal_id": "MOLLIE123",
                    "mollie_payment_provider_id": payment_provider.id,
                    "payment_method_type": "terminal",
                    "journal_id": cls.bank_journal.id,
                }),
            ],
        })
        cls.mollie_payment_method = cls.main_pos_config.payment_method_ids.filtered(lambda pm: pm.payment_provider == "mollie")

    def setUp(self):
        super().setUp()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.pos_session = self.main_pos_config.current_session_id
        self.mollie_payment_method = self.mollie_payment_method.with_user(self.pos_user)

    def _mollie_payment(self, **metadata):
        return {
            "id": "tr_test",
            "status": "open",
            "metadata": {
                "payment_uuid": "uuid",
                "payment_method_id": self.mollie_payment_method.id,
                "pos_session_id": self.pos_session.id,
                **metadata,
            },
        }

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

    def test_payment_closed_session(self):
        self.pos_session.state = "closed"
        with patch("odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request") as mock_request:
            with self.assertRaises(ValidationError):
                self.mollie_payment_method.mollie_create_payment(5.00, "uuid", self.pos_session.id)
        mock_request.assert_not_called()

    def test_refund(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "re_test", "status": "pending", "metadata": None},
        ) as mock_request:
            result = self.mollie_payment_method.mollie_create_refund("tr_test", 5.00, "uuid", self.pos_session.id)
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments/tr_test/refunds")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], f"pos_session_id={self.pos_session.id},payment_uuid=uuid")
        self.assertEqual(result["payment_id"], "re_test")
        self.assertEqual(result["status"], "pending")

    def test_cancel(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=self._mollie_payment(status="canceled"),
        ) as mock_request:
            self.mollie_payment_method.mollie_cancel_payment("tr_test", self.pos_session.id)
            method, path = mock_request.call_args.args

        self.assertEqual(method, "DELETE")
        self.assertEqual(path, "/payments/tr_test")

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
