from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend_slow_network import TestFrontendSlowNetwork
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@tagged('post_install', '-at_install')
class TestFrontendSlowNetworkRestaurant(TestFrontendSlowNetwork, TestFrontendCommon):
    def test_table_merge_slow_network(self):
        self.start_slow_network_tour('test_table_merge_slow_network')

        active_session_id = self.main_pos_config.current_session_id.id
        orders = self.env['pos.order'].search([('session_id', '=', active_session_id)])
        cancelled_orders = orders.filtered(lambda o: o.state == 'cancel')

        self.assertEqual(len(orders), 3, "There should be three orders created in the session.")
        self.assertEqual(len(cancelled_orders), 1, "There should be one cancelled order in the session.")
