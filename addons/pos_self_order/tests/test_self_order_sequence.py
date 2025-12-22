# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderSequence(SelfOrderCommonTest):
    browser_size = "1920,1080"

    def test_self_order_order_number_conflict_with_normal_orders(self):
        main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.env['restaurant.table'].create({
            'table_number': 1,
            'floor_id': main_floor.id,
            'seats': 4,
            'position_h': 150,
            'position_v': 100,
        })
        self.env['restaurant.table'].create({
            'table_number': 3,
            'floor_id': main_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 100,
        })
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_service_mode': 'table',
        })

        self.pos_config.open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'SelfOrderOrderNumberTour', login="pos_admin")
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'OrderNumberConflictTour', login="pos_admin")
