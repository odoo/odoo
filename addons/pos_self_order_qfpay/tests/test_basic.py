from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Command
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestSelfOrderKioskQFPay(TestPointOfSaleHttpCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref("base.HKD")
        cls.main_pos_config.use_pricelist = False
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Test HK POS Config',
            'use_presets': False,
            'default_preset_id': False,
            'available_preset_ids': [(5, 0)],
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [Command.create({
                'name': 'Qfpay',
                "qfpay_pos_key": "my_qfpay_pos_key",
                "qfpay_notification_key": "my_qfpay_notification_key",
                "use_payment_terminal": "qfpay",
                "payment_method_type": "terminal",
                "qfpay_payment_type": "card_payment",
                "journal_id": cls.bank_journal.id,
            })],
        })

        cls.env['pos.payment.method'].create({
            'name': 'Qfpay 2',
            'use_payment_terminal': 'qfpay',
        })

    def test_kiosk_qfpay(self):
        res = self.pos_config.load_self_data()
        pm = res.get('pos.payment.method', [])
        self.assertEqual(len(pm), 1, 'Only one payment method should be loaded')
        self.assertEqual(pm[0]['name'], 'Qfpay', 'The loaded payment method should be Qfpay')

        after_pay_kds = self.env['pos.config']._supported_kiosk_payment_terminal()
        self.assertTrue('qfpay' in after_pay_kds, 'The orders payed with qfpay should be sent to Kitchen Display/Printer only after being paid')

    def test_tour_kiosk_qfpay_order(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        with patch('odoo.addons.pos_qfpay.controllers.main.consteq', lambda a, b: True):
            self.start_tour(self_route, "kiosk_qfpay_order")
