# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
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
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)]
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
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'available_preset_ids': [(5, 0)]
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
        self.pos_config.limit_categories = True
        self.pos_config.iface_available_categ_ids = [(4, pos_categ_misc.id)]
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_order_product_info")

    def test_archive_variants_attributes(self):
        """Test archiving of variants when an attribute is removed, and verify
        the behavior in the POS UI product configurator.

        The test validates two main scenarios:
        1. Variants used in orders remain in DB when their attribute is removed
        2. In the UI configurator (see PosProductWithRemovedAttribute tour):
           - Selecting active variants shows no warning
           - Selecting archived variants shows a warning banner
        """

        # Create 3 attributes with 2 values each
        attributes = self.env['product.attribute'].create([{
            'name': f'Attribute {i}',
            'create_variant': 'always',
            'value_ids': [
                (0, 0, {'name': f'Value {i}-A'}),
                (0, 0, {'name': f'Value {i}-B'})
            ],
        } for i in range(1, 4)])

        # Create product template with these attributes
        # This will create 8 variants (2^3 combinations)
        template = self.env['product.template'].create({
            'name': 'One Attribute Removed Product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)]
            }) for attribute in attributes],
            'available_in_pos': True,
        })

        # Get two variants that differ in the first attribute's value
        # These will be used to test proper archiving after attribute removal
        variants = template.product_variant_ids
        variant1 = variants.filtered(lambda v: any(
            ptav.attribute_id == attributes[0] and ptav.product_attribute_value_id == attributes[0].value_ids[0]
            for ptav in v.product_template_attribute_value_ids
        ))[0]
        variant2 = variants.filtered(lambda v: any(
            ptav.attribute_id == attributes[0] and ptav.product_attribute_value_id == attributes[0].value_ids[1]
            for ptav in v.product_template_attribute_value_ids
        ))[0]

        # Create a POS order using both variants to ensure they can't be deleted
        self.pos_config.with_user(self.pos_user).open_ui()
        self.env['pos.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'session_id': self.pos_config.current_session_id.id,
            'amount_tax': 0,
            'amount_total': 1,
            'amount_paid': 1,
            "amount_return": 0,
            'lines': [
                (0, 0, {
                    'product_id': variant1.id,
                    'price_unit': variant1.lst_price,
                    'qty': 1,
                    'discount': 0.0,
                    'tax_ids': False,
                    'price_subtotal': variant1.lst_price,
                    'price_subtotal_incl': variant1.lst_price,
                }),
                (0, 0, {
                    'product_id': variant2.id,
                    'price_unit': variant2.lst_price,
                    'qty': 1,
                    'discount': 0.0,
                    'tax_ids': False,
                    'price_subtotal': variant1.lst_price,
                    'price_subtotal_incl': variant1.lst_price,
                })
            ]
        })

        # Store variant ids for later checking
        variant_ids = [variant1.id, variant2.id]

        # Remove first attribute - this should archive variants that differ only by this attribute
        template.attribute_line_ids.filtered(lambda l: l.attribute_id == attributes[0]).unlink()

        # Archive a specific variant to test UI warning in the product configurator
        # This variant has Value 2-B and Value 3-B (see tour steps)
        variant_to_archive = template.product_variant_ids.filtered(
            lambda v: any(ptav.product_attribute_value_id == attributes[1].value_ids[1] for ptav in v.product_template_attribute_value_ids)
                      and any(ptav.product_attribute_value_id == attributes[2].value_ids[1] for ptav in v.product_template_attribute_value_ids)
        )
        variant_to_archive.write({'active': False})

        # Verify variants from order still exist but are archived
        archived_variants = self.env['product.product'].with_context(active_test=False).browse(variant_ids)
        self.assertTrue(archived_variants.exists(), "Variants used in sale order should still exist")
        self.assertTrue(all(not active for active in archived_variants.mapped('active')), "Variants used in sale order should be archived")

        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_archived_attribute")
