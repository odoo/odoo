from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.pos_payment_method.models.pos_electronic_payment import (
    PosElectronicPayment,
)


class TestElectronicPayment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dummy_payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Test",
            "payment_provider": "test",
            "integration_type": "terminal",
        })
        cls.currency_id = cls.env.company.currency_id.id
        cls.payment_method_user = new_test_user(
            cls.env, login="test_payment_method_user", groups="pos_payment_method.group_payment_method_user,base.group_user",
        )
        cls.other_user = new_test_user(
            cls.env, login="test_other_user", groups="base.group_user",
        )
        cls.payment_method_with_user = cls.dummy_payment_method.with_user(cls.payment_method_user)

    def test_start_payment_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).start_payment(5.00, self.currency_id)
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).start_payment(5.00, self.currency_id)
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_payment(-5.00, self.currency_id)
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_payment(5.00, -123)

    def test_start_refund_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).start_refund(5.00, self.currency_id)
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).start_refund(5.00, self.currency_id)
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_refund(-5.00, self.currency_id)
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_refund(5.00, -123)

    def test_start_reversal_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).start_reversal(5.00, self.currency_id, "test")
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).start_reversal(5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_reversal(-5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.start_reversal(5.00, -123, "test")

    def test_capture_payment_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).capture_payment(5.00, self.currency_id, "test")
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).capture_payment(5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.capture_payment(-5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.capture_payment(5.00, -123, "test")

    def test_adjust_payment_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).adjust_payment(5.00, self.currency_id, "test")
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).adjust_payment(5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.adjust_payment(-5.00, self.currency_id, "test")
        with self.assertRaises(ValueError):
            self.payment_method_with_user.adjust_payment(5.00, -123, "test")

    def test_cancel_transaction_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).cancel_transaction("test")
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).cancel_transaction("test")

    def test_get_transaction_status_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).get_transaction_status("test")
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).get_transaction_status("test")

    def test_init_payment_method_validation(self):
        with self.assertRaises(ValueError):
            self.payment_method_with_user.browse([]).init_payment_method()
        with self.assertRaises(AccessError):
            self.dummy_payment_method.with_user(self.other_user).init_payment_method()

    def test_get_payment_providers(self):
        provider_data = self.payment_method_with_user._get_payment_providers()
        provider_selection = self.dummy_payment_method._fields["payment_provider"].get_values(self.env)

        for provider in provider_selection:
            if provider not in provider_data:
                msg = f"'{provider}' electronic payment provider is installed but is not listed in `_get_payment_providers`"
                self.fail(msg)

    def test_onchange_payment_provider(self):
        pm = self.env["pos.electronic.payment"].create({"name": "Test PM", "integration_type": "terminal", "payment_provider": "terminal_1"})
        with patch.object(PosElectronicPayment, "_get_terminal_provider_selection", return_value=[("terminal_1", "Terminal 1"), ("terminal_2", "Terminal 2")]), \
             patch.object(PosElectronicPayment, "_get_qr_provider_selection", return_value=[("qr_1", "QR Code 1"), ("qr_2", "QR Code 2")]), \
             patch.object(PosElectronicPayment, "_get_cash_machine_selection", return_value=[("cash_1", "Cash Machine 1"), ("cash_2", "Cash Machine 2")]):
            # terminal_1 --> terminal_2 = terminal
            pm.payment_provider = "terminal_2"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "terminal")

            # terminal_2 --> qr_1 = qr
            pm.payment_provider = "qr_1"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "qr")

            # qr_1 --> qr_2 = qr
            pm.payment_provider = "qr_2"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "qr")

            # qr_2 --> False = qr
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "qr")

            # False --> qr_1 = qr
            pm.payment_provider = "qr_1"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "qr")

            # qr_1 --> cash_1 = cash_machine
            pm.payment_provider = "cash_1"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "cash_machine")

            # cash_1 --> terminal_1 = terminal
            pm.payment_provider = "terminal_1"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "terminal")

            # terminal_1 --> False = terminal
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "terminal")

            # False --> cash_1 = cash_machine
            pm.payment_provider = "cash_1"
            pm._onchange_payment_provider()
            self.assertEqual(pm.integration_type, "cash_machine")

    def test_onchange_integration_type(self):
        pm = self.env["pos.electronic.payment"].create({"name": "Test PM", "integration_type": "terminal", "payment_provider": "terminal_1"})
        with patch.object(PosElectronicPayment, "_get_terminal_provider_selection", return_value=[("terminal_1", "Terminal 1"), ("terminal_2", "Terminal 2")]), \
             patch.object(PosElectronicPayment, "_get_qr_provider_selection", return_value=[("qr_1", "QR Code 1"), ("qr_2", "QR Code 2")]), \
             patch.object(PosElectronicPayment, "_get_cash_machine_selection", return_value=[("cash_1", "Cash Machine 1"), ("cash_2", "Cash Machine 2")]):
            # (terminal_1) terminal --> qr = False
            pm.payment_provider = "terminal_1"
            pm.integration_type = "qr"
            pm._onchange_integration_type()
            self.assertFalse(pm.payment_provider)

            # (qr_1) external_qr --> terminal = False
            pm.payment_provider = "qr_1"
            pm.integration_type = "terminal"
            pm._onchange_integration_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> cash_machine = False
            pm.payment_provider = "terminal_1"
            pm.integration_type = "cash_machine"
            pm._onchange_integration_type()
            self.assertFalse(pm.payment_provider)
