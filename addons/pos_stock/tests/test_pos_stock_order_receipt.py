# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_stock.tests.test_frontend import TestPosStockHttpCommon
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt


class TestPosStockOrderReceipt(TestPosStockHttpCommon, TestPosOrderReceipt):
    def test_receipt_with_ship_later(self):
        self.main_pos_config.write({
            'receipt_header': 'This is a test header for receipt',
            'receipt_footer': 'This is a test footer for receipt',
            'ship_later': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
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
        self.start_pos_tour("test_receipt_with_ship_later")
        self.compare_data(data['frontend_data'], data['backend_data'])
