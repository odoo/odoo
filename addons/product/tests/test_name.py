# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestName(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_name = 'Product Test Name'
        cls.product_code = 'PTN'
        cls.product = cls.env['product.product'].create({
            'name': cls.product_name,
            'default_code': cls.product_code,
        })

    def test_10_product_name(self):
        display_name = self.product.display_name
        self.assertEqual(display_name, "[%s] %s" % (self.product_code, self.product_name),
                         "Code should be preprended the name as the context is not preventing it.")
        display_name = self.product.with_context(display_default_code=False).display_name
        self.assertEqual(display_name, self.product_name,
                         "Code should not be preprended to the name as context should prevent it.")

    def test_default_code_and_negative_operator(self):
        res = self.env['product.template'].name_search(name='PTN', operator='not ilike')
        res_ids = [r[0] for r in res]
        self.assertNotIn(self.product.id, res_ids)

    def test_product_template_search_name_no_product_product(self):
        # To be able to test dynamic variant "variants" feature must be set up
        self.env.user.write({'group_ids': [(4, self.env.ref('product.group_product_variant').id)]})
        color_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'dynamic'})
        color_attr_value_r = self.env['product.attribute.value'].create({'name': 'Red', 'attribute_id': color_attr.id})
        color_attr_value_b = self.env['product.attribute.value'].create({'name': 'Blue', 'attribute_id': color_attr.id})
        template_dyn = self.env['product.template'].create({
            'name': 'Test Dynamical',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(4, color_attr_value_r.id), (4, color_attr_value_b.id)],
            })]
        })
        product = self.env['product.product'].create({
            'name': 'Dynamo Lamp',
            'default_code': 'Dynamo',
        })
        self.assertTrue(template_dyn.has_dynamic_attributes())
        # Ensure that template_dyn hasn't any product_product
        self.assertEqual(len(template_dyn.product_variant_ids), 0)
        # Ensure that Dynam search return Dynamo and Test Dynamical as this
        # last have no product_product
        res = self.env['product.template'].name_search(name='Dynam', operator='ilike')
        res_ids = [r[0] for r in res]
        self.assertIn(template_dyn.id, res_ids)
        self.assertIn(product.product_tmpl_id.id, res_ids)

    def test_product_product_search_name_is_case_insensitive(self):
        # case 1: in case of 2 different products with same name but different case in default_code
        product_1 = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'Aa1',
        })

        product_2 = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'aa1',
        })
        res_products = self.env['product.product'].name_search(name='Aa1')
        res_products_ids = [r[0] for r in res_products]
        self.assertIn(product_1.id, res_products_ids)
        self.assertIn(product_2.id, res_products_ids)

        # case 2: in case of 2 variants of the same product template with different case in default_code
        product_template = self.env['product.template'].create({
            'name': 'Test Product Template',
        })
        variant_1 = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'Bb1',
            'product_tmpl_id': product_template.id,
        })
        variant_2 = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'bb1',
            'product_tmpl_id': product_template.id,
        })
        res_variants = self.env['product.product'].name_search(name='Bb1')
        res_variants_ids = [r[0] for r in res_variants]
        self.assertIn(variant_1.id, res_variants_ids)
        self.assertIn(variant_2.id, res_variants_ids)
