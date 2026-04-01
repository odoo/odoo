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

    def test_synchronisation_of_orders(self):
        """ Test order synchronization with order data using the notify_synchronisation method.
            First, an ongoing order is created on the server, and verify its presence in the POS UI.
            Then, the order is paid from the server, and confirm if the order state is updated correctly.
        """
        self.start_pos_tour("OrderSynchronisationTour")
