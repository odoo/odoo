# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_pos_combo_items


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCombo(SelfOrderCommonTest):
    def test_self_order_combo(self):
        setup_pos_combo_items(self)
        desk_organizer_with_attributes_combo_line = self.env["pos.combo.line"].create(
            {
                "product_id": self.desk_organizer.id,
                "combo_price": 0,
            }
        )
        self.desk_accessories_combo.combo_line_ids += desk_organizer_with_attributes_combo_line
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        self.pos_admin.groups_id += self.env.ref('account.group_account_invoice')
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_combo_selector")

    def test_self_order_combo_correct_order(self):
        setup_pos_combo_items(self)
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_self_order_combo_correct_order")

        pos_order = self.env['pos.order'].search([], order="id desc", limit=1)
        order_lines = pos_order._export_for_ui(pos_order)['lines']

        def check_combo_products_order(lines):
            combo_header_id = None
            for line in lines:
                if len(line[2]['combo_line_ids']):
                    combo_header_id = line[2]['id']
                else:
                    if line[2]['combo_parent_id'] != combo_header_id:
                        return False
            return True

        self.assertTrue(check_combo_products_order(order_lines))
