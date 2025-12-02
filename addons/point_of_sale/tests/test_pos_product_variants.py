# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(ProductVariantsCommon, TestPointOfSaleHttpCommon):

    def test_integration_dynamic_variant_price(self):
        """Tests the price of products with dynamic variant when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 10,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dynamic product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        })

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids.id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, [ptav_dyn2.id])],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_variant_price', login="pos_user")

    def test_integration_always_variant_price(self):
        """Tests the price of products with always variant when added to cart"""
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A always product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_variant_price', login="pos_user")

    def test_integration_never_variant_price(self):
        """Tests the price of products with no variant(never) variant when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A never product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_variant_price(self):
        """Tests the price of products with dynamic and always variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_variant_price', login="pos_user")

    def test_integration_dynamic_never_variant_price(self):
        """Tests the price of products with dynamic and never variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_never_variant_price', login="pos_user")

    def test_integration_always_never_variant_price(self):
        """Tests the price of products with always and never variants when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5
        self.size_attribute_m.default_extra_price = 10

        product_template = self.env['product.template'].create({
            'name': 'A alw/nev product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_never_variant_price(self):
        """Tests the price of products with all types of variants when added to cart"""
        (dyn1, dyn2) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5
        self.no_variant_attribute_second.default_extra_price = 0.5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_never_variant_price', login="pos_user")

    def test_image_variants_displayed(self):
        """
        Tests that the user can correctly chose variants in the product_configurator_popup
        if the variant was set as Image
        """
        image_attribute = self.env['product.attribute'].create({
            'name': 'Images',
            'display_type': 'image',
            'create_variant': 'always',
        })
        images = self.env['product.attribute.value'].create([{
            'name': 'First Image',
            'attribute_id': image_attribute.id,
        }, {
            'name': 'Second Image',
            'attribute_id': image_attribute.id,
            'default_extra_price': 20,
        }])
        product_template = self.env['product.template'].create({
            'name': 'Image Product',
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': image_attribute.id,
            'value_ids': [Command.set([images[0].id, images[1].id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_image_variants_displayed', login="pos_user")
