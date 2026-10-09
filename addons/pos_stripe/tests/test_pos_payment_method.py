from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

SEND_API_REQUEST = (
    "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"
)


@tagged("post_install", "-at_install")
class TestStripePaymentMethod(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["payment.provider"].create(
            {
                "name": "Stripe Test",
                "code": "stripe",
                "company_id": cls.env.company.id,
            },
        )
        cls.stripe_payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Stripe",
                "use_payment_terminal": "stripe",
                "stripe_serial_number": "WSC513105011295",
                "payment_method_type": "terminal",
                "journal_id": cls.bank_journal.id,
            },
        )

    def test_capture_payment(self):
        PaymentMethod = self.env["pos.payment.method"]
        with patch(SEND_API_REQUEST, return_value={"id": "pi_1"}) as mock_request:
            PaymentMethod.stripe_capture_payment("pi_1")
            self.assertEqual(
                mock_request.call_args.args,
                ("POST", "payment_intents/pi_1/capture"),
            )
            self.assertIsNone(mock_request.call_args.kwargs["data"])

            PaymentMethod.with_context(
                stripe_currency_rounding=0.01,
            ).stripe_capture_payment("pi_1", amount=12.5)
            self.assertEqual(
                mock_request.call_args.kwargs["data"],
                {"amount_to_capture": 1250},
            )

            PaymentMethod.with_context(
                stripe_currency_rounding=1,
            ).stripe_capture_payment("pi_1", amount=1250)
            self.assertEqual(
                mock_request.call_args.kwargs["data"],
                {"amount_to_capture": 1250},
            )

    def test_payment_intent(self):
        with patch(
            SEND_API_REQUEST,
            return_value={"client_secret": "secret"},
        ) as mock_request:
            self.stripe_payment_method.stripe_payment_intent(12.5)
        self.assertEqual(mock_request.call_args.args, ("POST", "payment_intents"))
        self.assertEqual(
            mock_request.call_args.kwargs["data"],
            [
                ("currency", self.stripe_payment_method.company_id.currency_id.name),
                ("amount", 1250),
                ("payment_method_types[]", "card_present"),
                ("capture_method", "manual"),
            ],
        )

    def test_refund(self):
        with patch(SEND_API_REQUEST, return_value={"id": "re_1"}) as mock_request:
            self.stripe_payment_method.stripe_refund("pi_1", -12.5)
            self.assertEqual(
                mock_request.call_args.kwargs["data"],
                [("payment_intent", "pi_1"), ("amount", 1250)],
            )
            self.stripe_payment_method.stripe_refund("ch_1", -12.5)
            self.assertEqual(
                mock_request.call_args.kwargs["data"],
                [("charge", "ch_1"), ("amount", 1250)],
            )

        error = ValidationError("Refund failed")
        with patch(SEND_API_REQUEST, side_effect=error):
            self.assertEqual(
                self.stripe_payment_method.stripe_refund("pi_1", 12.5),
                {"error": error},
            )

    def test_access_requires_pos_user(self):
        user = new_test_user(self.env, login="no_pos_user", groups="base.group_user")
        with patch(SEND_API_REQUEST) as mock_request, self.assertRaises(AccessError):
            self.stripe_payment_method.with_user(user).stripe_capture_payment("pi_1")
        mock_request.assert_not_called()

    def test_serial_number_unique(self):
        with self.assertRaises(ValidationError):
            self.stripe_payment_method.copy(
                {
                    "stripe_serial_number": self.stripe_payment_method.stripe_serial_number,
                },
            )
