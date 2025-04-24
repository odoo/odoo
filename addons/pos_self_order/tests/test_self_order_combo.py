# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.fields import Command


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCombo(SelfOrderCommonTest):
    def test_self_order_combo(self):
        # merged test_self_order_kiosk_combo_sides
        # Add configurable product to the combo
        self.desk_accessories_combo.write({
            'combo_item_ids': [Command.create({'product_id': self.configurable_chair.product_variant_id.id})]
        })
        self.pos_admin.group_ids += self.env.ref('account.group_account_invoice')
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.start_pos_self_tour('self_combo_selector')

        order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(len(order.lines), 4, "There should be 4 order lines - 1 combo parent and 3 combo lines")
        # check that the combo lines are correctly linked to each other
        parent_line_id = self.env['pos.order.line'].search([('product_id.name', '=', 'Office Combo'), ('order_id', '=', order.id)])
        combo_line_ids = self.env['pos.order.line'].search([('product_id.name', '!=', 'Office Combo'), ('order_id', '=', order.id)])
        self.assertEqual(parent_line_id.combo_line_ids, combo_line_ids, "The combo parent should have 3 combo lines")
        self.assertEqual(parent_line_id.qty, 2, "There should be 2 combo products")
        self.assertEqual(parent_line_id.qty, combo_line_ids[0].qty, "The quantities should match with the parent")

    def test_self_order_combo_categories(self):
        self.pos_config.write({
            'iface_available_categ_ids': self.pos_cat_chair_test.ids,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.start_pos_self_tour('self_combo_selector_category')
