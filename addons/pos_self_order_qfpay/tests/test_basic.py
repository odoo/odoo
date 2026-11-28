from unittest.mock import patch
from uuid import uuid4

from odoo import fields
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Command, JsonRpcException
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

    def test_kiosk_qfpay_sign_trade(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        payment_method = self.pos_config.payment_method_ids

        def create_order(amount):
            order = self.env['pos.order'].create({
                'uuid': uuid4(),
                'session_id': self.pos_config.current_session_id.id,
                'date_order': fields.Datetime.now(),
                'amount_total': amount,
                'amount_tax': 0,
                'amount_paid': 0,
                'amount_return': 0,
                'lines': [Command.create({
                    'product_id': self.whiteboard_pen.product_variant_id.id,
                    'qty': 1,
                    'price_unit': amount,
                    'price_subtotal': amount,
                    'price_subtotal_incl': amount,
                })],
            })
            order._ensure_access_token()
            return order

        def sign_trade(order, order_access_token=None, payment_method_id=payment_method.id):
            # Not logged in, like a kiosk
            return self.make_jsonrpc_request('/pos-self-order/qfpay-sign-trade', {
                'access_token': self.pos_config.access_token,
                'order_id': order.id,
                'order_access_token': order_access_token or order.access_token,
                'payment_method_id': payment_method_id,
            })

        for amount in [100, 12.5]:
            order = create_order(amount)
            self.assertEqual(sign_trade(order), payment_method.qfpay_sign_request({
                'func_type': 1001,
                'amt': amount,
                'channel': 'card_payment',
                'out_trade_no': f'{order.uuid}--{order.session_id.id}--{payment_method.id}',
                'wait_card_timeout': 30,
                'camera_id': 1,
            }))

        with self.assertRaises(JsonRpcException, msg='werkzeug.exceptions.NotFound'):
            sign_trade(order, order_access_token='wrong_token')
        other_payment_method = self.env['pos.payment.method'].search([('name', '=', 'Qfpay 2')])
        with self.assertRaises(JsonRpcException, msg='werkzeug.exceptions.NotFound'):
            sign_trade(order, payment_method_id=other_payment_method.id)
        order.state = 'paid'
        with self.assertRaises(JsonRpcException, msg='werkzeug.exceptions.NotFound'):
            sign_trade(order)
