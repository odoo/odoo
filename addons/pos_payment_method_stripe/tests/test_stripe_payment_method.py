from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestStripePaymentMethod(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        payment_provider = cls.env["payment.provider"].create({"name": "Stripe Test", "code": "stripe", "stripe_secret_key": "mockApiKey"})
        cls.stripe_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Stripe",
            "payment_provider": "stripe",
            "stripe_serial_number": "STRIPE123",
            "stripe_payment_provider_id": payment_provider.id,
            "stripe_ask_customer_for_tip": True,
            "integration_type": "terminal",
        })
        cls.currency = cls.env.company.currency_id

    def test_payment(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            result = self.stripe_payment_method.start_payment(5.00, self.currency.id)
            method, path = mock_request.call_args.args
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "payment_intents")
        self.assertEqual(args[0], ("currency", self.currency.name))
        self.assertEqual(args[1], ("amount", 500))
        self.assertEqual(args[2], ("payment_method_types[]", "card_present"))
        self.assertEqual(args[3], ("capture_method", "automatic_async"))
        self.assertEqual(args[4], ("metadata[allow_tips]", ""))
        self.assertEqual(result["transaction_id"], "test")
        self.assertEqual(result["client_secret"], "SECRET")
        self.assertEqual(result["terminal_serial_number"], "STRIPE123")
        self.assertEqual(result["allow_tips"], False)

    def test_payment_allowing_tips(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            result = self.stripe_payment_method.start_payment(5.00, self.currency.id, {"allow_tips": True})
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(args[4], ("metadata[allow_tips]", "true"))
        self.assertEqual(result["allow_tips"], True)

    def test_payment_allowing_adjustment(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            self.stripe_payment_method.start_payment(5.00, self.currency.id, {"allow_adjustments": True})
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(args[3], ("capture_method", "manual"))

    def test_payment_australia(self):
        self.env.company.country_code = "AU"
        self.currency.name = "AUD"
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            self.stripe_payment_method.start_payment(5.00, self.currency.id, {"allow_adjustments": True})
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(args[5], ("payment_method_options[card_present][capture_method]", "manual_preferred"))

    def test_payment_canada(self):
        self.env.company.country_code = "CA"
        self.currency.name = "CAD"
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            self.stripe_payment_method.start_payment(5.00, self.currency.id)
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(args[5], ("payment_method_types[]", "interac_present"))

    def test_reversal(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test_refund", "status": "pending", "client_secret": "SECRET"},
        ) as mock_request:
            result = self.stripe_payment_method.start_reversal(5.00, self.currency.id, "test")
            method, path = mock_request.call_args.args
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "refunds")
        self.assertEqual(args[0], ("payment_intent", "test"))
        self.assertEqual(args[1], ("amount", 500))
        self.assertEqual(result["transaction_id"], "test_refund")

    def test_capture(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "succeeded", "client_secret": "SECRET"},
        ) as mock_request:
            result = self.stripe_payment_method.capture_payment(5.00, self.currency.id, "test")
            method, path = mock_request.call_args.args
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "payment_intents/test/capture")
        self.assertEqual(args["amount_to_capture"], 500)
        self.assertEqual(result["transaction_id"], "test")

    def test_adjust(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"id": "test", "status": "succeeded", "client_secret": "SECRET"},
        ) as mock_request:
            result = self.stripe_payment_method.adjust_payment(5.00, self.currency.id, "test")
            method, path = mock_request.call_args.args
            args = mock_request.call_args.kwargs.get("data")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "payment_intents/test/capture")
        self.assertEqual(args["amount_to_capture"], 500)
        self.assertEqual(result["transaction_id"], "test")
        self.assertEqual(result["metadata"]["can_be_adjusted"], False)

    def test_get_requires_capture(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={
                "id": "test",
                "status": "requires_capture",
                "currency": self.currency.name,
                "latest_charge": "charge",
                "charges": {
                    "data": [{
                        "id": "charge",
                        "payment_method_details": {
                            "type": "card_present",
                            "card_present": {"brand": "Visa", "overcapture_supported": True},
                        },
                    }],
                },
                "amount_details": {
                    "tip": {"amount": 100},
                },
                "metadata": {},
            },
        ) as mock_request:
            result = self.stripe_payment_method.get_transaction_status("test")
            method, path = mock_request.call_args.args

        self.assertEqual(method, "GET")
        self.assertEqual(path, "payment_intents/test")
        self.assertEqual(result["status"], "paid")
        self.assertEqual(result["transaction_id"], "test")
        self.assertEqual(result["card_type"], "Visa")
        self.assertEqual(result["metadata"]["requires_capture"], True)
        self.assertEqual(result["metadata"]["can_be_adjusted"], True)
        self.assertEqual(result["tip_amount"], 1.00)

    def test_get_captured(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={
                "id": "test",
                "status": "succeeded",
                "currency": self.currency.name,
                "latest_charge": "charge",
                "charges": {
                    "data": [{
                        "id": "charge",
                        "payment_method_details": {
                            "type": "card_present",
                            "card_present": {"brand": "Visa", "overcapture_supported": True},
                        },
                    }],
                },
                "amount_details": {},
                "metadata": {},
            },
        ):
            result = self.stripe_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "paid")
        self.assertEqual(result["metadata"]["requires_capture"], False)
        self.assertEqual(result["metadata"]["can_be_adjusted"], False)

    def test_get_requires_payment_method(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={
                "id": "test",
                "client_secret": "SECRET",
                "status": "requires_payment_method",
                "amount_details": {},
                "metadata": {"allow_tips": "true"},
            },
        ):
            result = self.stripe_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["stripe_status"], "requires_payment_method")
        self.assertEqual(result["client_secret"], "SECRET")
        self.assertEqual(result["terminal_serial_number"], "STRIPE123")
        self.assertEqual(result["allow_tips"], True)

    def test_get_cancelled(self):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={
                "id": "test",
                "status": "canceled",
            },
        ):
            result = self.stripe_payment_method.get_transaction_status("test")

        self.assertEqual(result["status"], "failed")
