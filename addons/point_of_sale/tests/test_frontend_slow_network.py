from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestFrontendSlowNetwork(TestPointOfSaleHttpCommon):
    def start_slow_network_tour(self, tour_name, login="pos_admin", **kwargs):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, tour_name, login=login, **kwargs)

    def test_order_slow_network(self):
        self.start_slow_network_tour('test_order_slow_network')

        active_session_id = self.main_pos_config.current_session_id.id
        orders = self.env['pos.order'].search([('session_id', '=', active_session_id)])
        prices = orders.mapped('amount_total')

        self.assertEqual(len(orders), 2, "There should be two orders created in the session.")
        self.assertEqual(prices, [3.96, 1.98], "The total amounts of the orders should be 1.98 and 3.96 respectively.")
