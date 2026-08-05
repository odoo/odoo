# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderAttribute(SelfOrderCommonTest):
    def test_self_order_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)]
        })

        product = self.env['product.template'].search([('name', '=', 'Desk Organizer')])[0]
        product.attribute_line_ids[0].product_template_value_ids[0].price_extra = 0.0
        product.attribute_line_ids[0].product_template_value_ids[1].price_extra = 1.0
        product.attribute_line_ids[0].product_template_value_ids[2].price_extra = 2.0

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        size_m = product.attribute_line_ids[0].product_template_value_ids[1]
        size_l = product.attribute_line_ids[0].product_template_value_ids[2]
        fabric_leather = product.attribute_line_ids[1].product_template_value_ids[0]

        order = self.process_self_order([
            {
                'product': self.desk_organizer,
                'qty': 1,
                'price_unit': product.list_price,
                'attribute_value_ids': [size_m.id, fabric_leather.id],
            },
            {
                'product': self.desk_organizer,
                'qty': 1,
                'price_unit': product.list_price,
                'attribute_value_ids': [size_l.id, fabric_leather.id],
            },
        ])
        self.assertEqual(order.lines[0].price_extra, 1.0)
        self.assertEqual(order.lines[1].price_extra, 2.0)

    def test_self_order_always_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)]
        })
        pos_categ_chairs = self.env['pos.category'].create({
            'name': 'Chairs',
        })
        self.pos_config.write({
            'iface_available_categ_ids': [(4, pos_categ_chairs.id)]
        })

        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'always',
            'value_ids': [(0, 0, {'name': 'White'}), (0, 0, {'name': 'Red', 'default_extra_price': 5})],
        })
        chair_product_tmpl = self.env['product.template'].create({
            'name': 'Chair',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_chairs.id)],
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, color_attribute.value_ids.ids)]
            })],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        white_variant = chair_product_tmpl.product_variant_ids[0]
        red_variant = chair_product_tmpl.product_variant_ids[1]

        order = self.process_self_order([
            {
                'product': white_variant,
                'qty': 1,
                'price_unit': 10.0,
                'attribute_value_ids': white_variant.product_template_attribute_value_ids.ids,
            },
            {
                'product': red_variant,
                'qty': 1,
                'price_unit': 15.0,
                'attribute_value_ids': red_variant.product_template_attribute_value_ids.ids,
            },
        ])

        self.assertEqual(order.lines[0].product_id.id, white_variant.id)
        self.assertEqual(order.lines[0].attribute_value_ids.ids, white_variant.product_template_attribute_value_ids.ids)
        self.assertEqual(order.lines[0].price_unit, 10.0)
        self.assertEqual(order.lines[1].product_id.id, red_variant.id)
        self.assertEqual(order.lines[1].attribute_value_ids.ids, red_variant.product_template_attribute_value_ids.ids)
        self.assertEqual(order.lines[1].price_unit, 15.0)

    def test_self_order_multi_check_attribute_with_extra_price(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': "mobile",
            'self_ordering_pay_after': "each",
            'self_ordering_service_mode': "counter",
            'available_preset_ids': [Command.clear()],
        })
        attributes = self.env['product.attribute'].create([
            {
                'name': "Colour",
                'display_type': "radio",
                'create_variant': "always",
                'value_ids': [
                    Command.create({'name': "No Colour", 'default_extra_price': 0}),
                    Command.create({'name': "Blue", 'default_extra_price': 2}),
                ],
            },
            {
                'name': "Add-ons",
                'display_type': "multi",
                'create_variant': "no_variant",
                'value_ids': [
                    Command.create({'name': "Pen Holder", 'default_extra_price': 1.0}),
                    Command.create({'name': "Mini Drawer", 'default_extra_price': 2.0}),
                ],
            },
        ])

        desk_tmpl = self.desk_organizer.product_tmpl_id
        self.env['product.template.attribute.line'].create([
            {
                'product_tmpl_id': desk_tmpl.id,
                'attribute_id': attr.id,
                'value_ids': [Command.link(val.id) for val in attr.value_ids],
            }
            for attr in attributes
        ])
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        colour_line = desk_tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Colour')
        addons_line = desk_tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Add-ons')
        size_line = desk_tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Size')
        fabric_line = desk_tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Fabric')

        colour_blue = colour_line.product_template_value_ids.filtered(lambda v: v.name == 'Blue')
        addon_pen_holder = addons_line.product_template_value_ids.filtered(lambda v: v.name == 'Pen Holder')
        addon_mini_drawer = addons_line.product_template_value_ids.filtered(lambda v: v.name == 'Mini Drawer')
        size_m = size_line.product_template_value_ids.filtered(lambda v: v.name == 'M')
        fabric_leather = fabric_line.product_template_value_ids.filtered(lambda v: v.name == 'Leather')

        blue_variant = desk_tmpl.product_variant_ids.filtered(
            lambda v: any(ptav.name == 'Blue' for ptav in v.product_template_attribute_value_ids)
        )[:1]

        order = self.process_self_order([
            {
                'product': blue_variant,
                'qty': 1,
                'price_unit': blue_variant.lst_price,
                'attribute_value_ids': [
                    size_m.id, fabric_leather.id, colour_blue.id,
                    addon_pen_holder.id, addon_mini_drawer.id,
                ],
            },
        ])
        self.assertEqual(order.amount_total, 11.62)  # 5.10 (price) + 2.0 + 1.0 + 2.0 + 1.52 (tax)
