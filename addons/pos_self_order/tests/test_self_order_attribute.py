# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderAttribute(SelfOrderCommonTest):
    def test_self_order_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        product = self.env['product.product'].search([('name', '=', 'Desk Organizer')])[0]
        product.attribute_line_ids[0].product_template_value_ids[0].price_extra = 0.25
        product.attribute_line_ids[0].product_template_value_ids[1].price_extra = 1.0
        product.attribute_line_ids[0].product_template_value_ids[2].price_extra = 2.0

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_attribute_selector")
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].price_extra, 1.0)
        self.assertEqual(order.lines[1].price_extra, 2.0)

    def test_self_order_multi_check_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        pos_categ_misc = self.env['pos.category'].create({
            'name': 'Miscellaneous',
        })

        product = self.env['product.product'].create({
            'name': 'Multi Check Attribute Product',
            'available_in_pos': True,
            'list_price': 1,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        attribute = self.env['product.attribute'].create({
            'name': 'Attribute 1',
            'display_type': 'multi',
            'create_variant': 'no_variant',
        })
        attribute_val_1 = self.env['product.attribute.value'].create({
            'name': 'Attribute Val 1',
            'attribute_id': attribute.id,
        })
        attribute_val_2 = self.env['product.attribute.value'].create({
            'name': 'Attribute Val 2',
            'attribute_id': attribute.id,
        })

        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, [attribute_val_1.id, attribute_val_2.id])]
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_multi_attribute_selector")

    def test_self_order_always_attribute(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        pos_categ_chairs = self.env['pos.category'].create({
            'name': 'Chairs',
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
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "selfAlwaysAttributeVariants")

        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.lines[0].product_id.id, chair_product_tmpl.product_variant_ids[0].id)
        self.assertEqual(order.lines[0].price_unit, 10.0)
        self.assertEqual(order.lines[1].product_id.id, chair_product_tmpl.product_variant_ids[1].id)
        self.assertEqual(order.lines[1].price_unit, 15.0)

    def test_self_order_product_info(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        pos_categ_misc = self.env['pos.category'].create({
            'name': 'Miscellaneous',
        })

        self.env['product.product'].create({
            'name': 'Product Info Test',
            'available_in_pos': True,
            'list_price': 1,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
            'public_description': 'Nice Product'
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_order_product_info")
