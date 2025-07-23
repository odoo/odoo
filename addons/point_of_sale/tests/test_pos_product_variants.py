# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(ProductVariantsCommon, TestPointOfSaleHttpCommon):

    def get_ptav(self, template, pav):
        return template.valid_product_template_attribute_line_ids.filtered(
            lambda ptal: ptal.attribute_id == pav.attribute_id
        ).product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == pav
        )

    def test_product_exclusions(self):
        sofa = self.product_template_sofa
        sofa.attribute_line_ids = [Command.create({
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([
                self.size_attribute_s.id,
                self.size_attribute_l.id,
            ])],
        })]

        red_ptav = self.get_ptav(sofa, self.color_attribute_red)
        blue_ptav = self.get_ptav(sofa, self.color_attribute_blue)
        small_ptav = self.get_ptav(sofa, self.size_attribute_s)

        # Create an attribute exclusion for red, small sofas
        red_ptav.exclude_for = [Command.create({
            'product_tmpl_id': sofa.id,
            'value_ids': [Command.set([small_ptav.id])],
        })]

        # Archive blue, small sofa variant
        sofa_blue_s = sofa._get_variant_for_combination(small_ptav + blue_ptav)
        sofa_blue_s.action_archive()

        Product = self.env['product.product']
        unavailable_combinations = Product._get_archived_combinations_per_product_tmpl_id(sofa.ids)
        unavailable_sofas = [set(combination) for combination in unavailable_combinations[sofa.id]]

        self.assertEqual(len(unavailable_sofas), 2, "There should be 2 unavailable combinations")
        self.assertIn(
            {red_ptav.id, small_ptav.id},
            unavailable_sofas,
            "Red, small sofas should be unavailable for sale due to attribute exclusion",
        )
        self.assertIn(
            {blue_ptav.id, small_ptav.id},
            unavailable_sofas,
            "Blue, small sofas should be unavailable for sale due to being archived",
        )

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
