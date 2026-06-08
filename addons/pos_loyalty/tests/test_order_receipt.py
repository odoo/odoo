# Part of Odoo. See LICENSE file for full copyright and licensing details.
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

        # Add function to model
        order_model = self.env.registry.models['pos.order']
        order_model.get_order_frontend_receipt_data = get_order_frontend_receipt_data
        self.start_pos_tour("test_receipt_data_pos_loyalty")
        loyalty_frontend = data['frontend_data']['extra_data']['loyalties']
        loyalty_backend = data['backend_data']['extra_data']['loyalties']
        for [backend, frontend] in zip(loyalty_backend, loyalty_frontend):
            self.comparator(backend, frontend)
