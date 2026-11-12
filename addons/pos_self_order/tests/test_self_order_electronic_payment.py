from unittest.mock import patch

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


class TestSelfOrderElectronicPayment(SelfOrderCommonTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.electronic_payment = cls.env["pos.electronic.payment"].create({
            "name": "Test",
            "integration_type": "terminal",
            "payment_provider": "test",
        })
        cls.currency = cls.env.company.currency_id

    def setUp(self):
        super().setUp()
        self.bank_payment_method.electronic_payment_id = self.electronic_payment
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        self.order = self.process_self_order([{
            'product': self.cola,
            'qty': 1,
            'price_unit': self.cola.lst_price,
        }])

    def test_start_payment_adds_pending_payment(self):
        with patch(
            "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._start_payment",
            return_value={"transaction_id": "test", "status": "pending"},
        ):
            self.electronic_payment.start_payment(self.order.amount_total, self.currency.id, {"kiosk_order_id": self.order.id, "kiosk_payment_method_id": self.bank_payment_method.id})

        self.assertEqual(len(self.order.payment_ids), 1)
        self.assertEqual(self.order.payment_ids[0].amount, self.order.amount_total)
        self.assertEqual(self.order.payment_ids[0].payment_status, "pending")

    def test_start_payment_adds_completed_payment_and_validates(self):
        with patch(
            "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._start_payment",
            return_value={"transaction_id": "test", "status": "paid"},
        ):
            self.electronic_payment.start_payment(self.order.amount_total, self.currency.id, {"kiosk_order_id": self.order.id, "kiosk_payment_method_id": self.bank_payment_method.id})

        self.assertEqual(len(self.order.payment_ids), 1)
        self.assertEqual(self.order.payment_ids[0].amount, self.order.amount_total)
        self.assertEqual(self.order.payment_ids[0].payment_status, "done")
        self.assertEqual(self.order.state, "paid")

    def test_get_transaction_status_deletes_pending_payment(self):
        self.env["pos.payment"].create({
            "pos_order_id": self.order.id,
            "amount": self.order.amount_total,
            "payment_method_id": self.bank_payment_method.id,
            "payment_status": "pending",
            "transaction_id": "test",
        })
        self.assertEqual(len(self.order.payment_ids), 1)

        with patch(
            "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._get_transaction_status",
            return_value={"transaction_id": "test", "status": "failed"},
        ):
            self.electronic_payment.get_transaction_status("test")

        self.assertEqual(len(self.order.payment_ids), 0)

    def test_get_transaction_status_confirms_pending_payment_and_validates(self):
        self.env["pos.payment"].create({
            "pos_order_id": self.order.id,
            "amount": self.order.amount_total,
            "payment_method_id": self.bank_payment_method.id,
            "payment_status": "pending",
            "transaction_id": "test",
        })

        with patch(
            "odoo.addons.pos_payment_method.models.pos_electronic_payment.PosElectronicPayment._get_transaction_status",
            return_value={"transaction_id": "test", "status": "paid"},
        ):
            self.electronic_payment.get_transaction_status("test")

        self.assertEqual(self.order.payment_ids[0].payment_status, "done")
        self.assertEqual(self.order.state, "paid")

    def test_notify_deletes_pending_payment(self):
        self.env["pos.payment"].create({
            "pos_order_id": self.order.id,
            "amount": self.order.amount_total,
            "payment_method_id": self.bank_payment_method.id,
            "payment_status": "pending",
            "transaction_id": "test",
        })
        self.assertEqual(len(self.order.payment_ids), 1)

        self.electronic_payment._notify("test", {"transaction_id": "test", "status": "failed"})

        self.assertEqual(len(self.order.payment_ids), 0)

    def test_notify_confirms_pending_payment_and_validates(self):
        self.env["pos.payment"].create({
            "pos_order_id": self.order.id,
            "amount": self.order.amount_total,
            "payment_method_id": self.bank_payment_method.id,
            "payment_status": "pending",
            "transaction_id": "test",
        })

        self.electronic_payment._notify("test", {"transaction_id": "test", "status": "paid"})

        self.assertEqual(self.order.payment_ids[0].payment_status, "done")
        self.assertEqual(self.order.state, "paid")
