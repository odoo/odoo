from unittest.mock import patch

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
                    "use_payment_terminal": "mollie",
                    "mollie_terminal_id": "MOLLIE123",
                    "mollie_payment_provider_id": payment_provider.id,
                    "payment_method_type": "terminal",
                    "journal_id": cls.bank_journal.id,
                }),
            ],
        })
        cls.mollie_payment_method = cls.main_pos_config.payment_method_ids.filtered(lambda pm: pm.use_payment_terminal == "mollie")

    def test_payment(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            self.mollie_payment_method.mollie_create_payment(5.00, "uuid", 1)
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], "pos_session_id=1,payment_uuid=uuid")
        self.assertEqual(payload["method"], "pointofsale")
        self.assertEqual(payload["terminalId"], self.mollie_payment_method.mollie_terminal_id)

    def test_refund(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            self.mollie_payment_method.mollie_create_refund("test", 5.00, "uuid", 1)
            method, path = mock_request.call_args.args
            payload = mock_request.call_args.kwargs.get("json")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/payments/test/refunds")
        self.assertEqual(payload["amount"]["value"], "5.00")
        self.assertEqual(payload["description"], "pos_session_id=1,payment_uuid=uuid")

    def test_cancel(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            self.mollie_payment_method.mollie_cancel_payment("test")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "DELETE")
        self.assertEqual(path, "/payments/test")

    def test_get(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "open"},
        ) as mock_request:
            self.mollie_payment_method.mollie_get_payment("test")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "GET")
        self.assertEqual(path, "/payments/test")
