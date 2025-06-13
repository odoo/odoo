from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


class TestFrontend(TestFrontendCommon):
    def test_devices_synchronization(self):
        self.main_pos_config.open_ui()
        self.env['pos.order'].create({
            'pos_reference': 'device_sync',
            'table_id': self.main_floor_table_5.id,
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "Coca-Cola",
                'product_id': self.coca_cola_test.id,
                'price_unit': 2.20,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 2.20,
                'price_subtotal_incl': 2.20,
            })],
            'amount_paid': 2.20,
            'amount_total': 2.20,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        self.start_pos_tour('test_devices_synchronization')

    def test_synchronization_rollback(self):
        self.main_pos_config.open_ui()

        # This first tour should result with an order with 2 cola and 1 water
        self.start_pos_tour('test_synchronization_rollback')
        last_order = self.main_pos_config.current_session_id.order_ids[-1]
        self.assertEqual(last_order.lines.mapped('qty'), [2, 1])
