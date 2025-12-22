# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


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
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_product_variant').id)]})
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

    def test_product_product_name_search(self):
        attribute = self.env['product.attribute'].create({
            'name': 'Attribute',
            'value_ids': [
                Command.create({'name': f'value {i}'})
                for i in range(3)
            ]
        })
        template = self.env['product.template'].create({
            'name': 'Whatever',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)]
                })
            ]
        })
        variant1, _variant2, _variant3 = template.product_variant_ids
        variant1.default_code = 'HOHO'
        product_search = self.env['product.product'].with_context(partner_id=33).search([
            ('display_name', '=', 'HOHO'),
        ])
        self.assertEqual(variant1, product_search)
