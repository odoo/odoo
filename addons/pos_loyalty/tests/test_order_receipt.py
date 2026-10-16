# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt


@tagged('post_install', '-at_install')
class TestOrderReceiptPosLoyalty(TestPosOrderReceipt):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Coupon_id is skipped because the frontend doesn't have the server id yet.
        self.key_to_skip.update({
            'pos.order.line': ['coupon_id'] + self.key_to_skip['pos.order.line'],
        })

    def test_receipt_data_pos_loyalty(self):
        self.env['loyalty.program'].create({
            'name': 'Buy 4 Take 1 Example Simple Product',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'product_ids': self.example_simple_product.product_variant_id.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.example_simple_product.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 4,
            })],
        })

        data = {
            'frontend_data': None,
            'backend_data': None,
        }

        def get_order_frontend_receipt_data(self, frontend_data):
            backend_data = self.order_receipt_generate_data()
            data['frontend_data'] = frontend_data
            data['backend_data'] = backend_data

        with patch.object(self.env.registry['pos.order'], 'get_order_frontend_receipt_data', get_order_frontend_receipt_data, create=True):
            self.start_pos_tour("test_receipt_data_pos_loyalty")
            loyalty_frontend = data['frontend_data']['extra_data']['loyalties']
            loyalty_backend = data['backend_data']['extra_data']['loyalties']
            for [backend, frontend] in zip(loyalty_backend, loyalty_frontend):
                self.comparator(backend, frontend)

    def test_receipt_next_order_coupon_value(self):
        program = self.env['loyalty.program'].create({
            'name': 'Next Order 0.1/pt',
            'program_type': 'next_order_coupons',
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 0.1,
                'discount_applicability': 'order',
            })],
        })
        self.assertEqual(program._get_per_point_discount(), 0.1)

        coupon = self.env['loyalty.card'].create({
            'program_id': program.id,
            'code': 'TEST_NOC_0001',
            'points': 100,
        })

        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'amount_total': 0, 'amount_paid': 0, 'amount_tax': 0, 'amount_return': 0,
        })
        self.env['loyalty.history'].create({
            'card_id': coupon.id,
            'order_model': 'pos.order',
            'order_id': order.id,
            'issued': 100,
            'description': 'Test next order coupon',
        })

        new_coupons = order.order_receipt_generate_data()['extra_data']['new_coupons']
        self.assertEqual(len(new_coupons), 1)
        self.assertEqual(new_coupons[0]['code'], 'TEST_NOC_0001')
        self.assertEqual(
            new_coupons[0]['discount_value'],
            order._order_receipt_format_currency(100 * 0.1),
        )

        program.reward_ids.discount_mode = 'percent'
        self.assertIsNone(program._get_per_point_discount())
        new_coupons = order.order_receipt_generate_data()['extra_data']['new_coupons']
        self.assertFalse(new_coupons[0]['discount_value'])
