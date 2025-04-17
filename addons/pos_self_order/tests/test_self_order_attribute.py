# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderAttribute(SelfOrderCommonTest):

    def test_self_order_attribute(self):
        # product = self.env['product.template'].search([('name', '=', 'Desk Organizer')])[0]
        self.configurable_chair.attribute_line_ids.product_template_value_ids.price_extra = 0.0
        self.configurable_chair.attribute_line_ids[1].product_template_value_ids[1].price_extra = 10.0  # Wood
        self.configurable_chair.attribute_line_ids[2].product_template_value_ids[1].price_extra = 20.0  # Wool

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.start_pos_self_tour("self_attribute_selector")
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].price_extra, 10.0)
        self.assertEqual(order.lines[1].price_extra, 20.0)

    def test_self_order_multi_check_attribute(self):
        multi_attribute = self.env['product.attribute'].create({
            'name': 'Multi',
            'display_type': 'multi',
            'create_variant': 'no_variant',
            'value_ids': [
                (0, 0, {'name': 'Value 1'}),
                (0, 0, {'name': 'Value 2'}),
            ]
        })
        self.desk_organizer.write({
            'list_price': 10,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': multi_attribute.id,
                'value_ids': [(6, 0, multi_attribute.value_ids.ids)]
            })],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_self_tour("self_multi_attribute_selector")

    def test_self_order_always_attribute(self):
        self.always_color_attribute.value_ids[1].default_extra_price = 5
        self.desk_organizer.write({
            'list_price': 10,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.always_color_attribute.id,
                'value_ids': [(6, 0, self.always_color_attribute.value_ids.ids)]
            })],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("selfAlwaysAttributeVariants")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].product_id.id, self.desk_organizer.product_variant_ids[0].id)
        self.assertEqual(order.lines[0].price_unit, 10.0)
        self.assertEqual(order.lines[1].product_id.id, self.desk_organizer.product_variant_ids[1].id)
        self.assertEqual(order.lines[1].price_unit, 15.0)

    def test_self_order_product_info(self):
        self.desk_organizer.write({
            'public_description': 'Nice Product'
        })
        self.pos_config.with_user(self.pos_user).open_ui()

        self.start_pos_self_tour("self_order_product_info")
