# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from odoo.tests.common import TransactionCase

class TestVariantsSearch(TransactionCase):

    def setUp(self):
        res = super(TestVariantsSearch, self).setUp()
        self.size_attr = self.env['product.attribute'].create({'name': 'Size'})
        self.size_attr_value_s = self.env['product.attribute.value'].create({'name': 'S', 'attribute_id': self.size_attr.id})
        self.size_attr_value_m = self.env['product.attribute.value'].create({'name': 'M', 'attribute_id': self.size_attr.id})
        self.size_attr_value_l = self.env['product.attribute.value'].create({'name': 'L', 'attribute_id': self.size_attr.id})
        self.product_shirt_template = self.env['product.template'].create({
            'name': 'Shirt',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(6, 0, [self.size_attr_value_l.id])],
            })]
        })
        return res

    def test_attribute_line_search(self):
        search_not_to_be_found = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'M')]
        )
        self.assertNotIn(self.product_shirt_template, search_not_to_be_found,
                         'Shirt should not be found searching M')

        search_attribute = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'Size')]
        )
        self.assertIn(self.product_shirt_template, search_attribute,
                      'Shirt should be found searching Size')

        search_value = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'L')]
        )
        self.assertIn(self.product_shirt_template, search_value,
                      'Shirt should be found searching L')

    def test_name_search(self):
        self.product_slip_template = self.env['product.template'].create({
            'name': 'Slip',
        })
        res = self.env['product.product'].name_search('Shirt', [], 'not ilike', None)
        res_ids = [r[0] for r in res]
        self.assertIn(self.product_slip_template.product_variant_ids.id, res_ids,
                      'Slip should be found searching \'not ilike\'')


class TestVariants(common.TestProductCommon):

    def setUp(self):
        res = super(TestVariants, self).setUp()
        self.size_attr = self.env['product.attribute'].create({'name': 'Size'})
        self.size_attr_value_s = self.env['product.attribute.value'].create({'name': 'S', 'attribute_id': self.size_attr.id})
        self.size_attr_value_m = self.env['product.attribute.value'].create({'name': 'M', 'attribute_id': self.size_attr.id})
        self.size_attr_value_l = self.env['product.attribute.value'].create({'name': 'L', 'attribute_id': self.size_attr.id})
        return res

    def test_variants_creation_mono(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id)],
            })]
        })

        # produced variants: one variant, because mono value
        self.assertEqual(len(test_template.product_variant_ids), 1)
        self.assertEqual(test_template.product_variant_ids.attribute_value_ids, self.size_attr_value_s)

    def test_variants_creation_mono_double(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_1.id,
                'value_ids': [(4, self.prod_attr1_v2.id)],
            }), (0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id)],
            })]
        })

        # produced variants: one variant, because only 1 combination is possible
        self.assertEqual(len(test_template.product_variant_ids), 1)
        self.assertEqual(test_template.product_variant_ids.attribute_value_ids, self.size_attr_value_s + self.prod_attr1_v2)

    def test_variants_creation_mono_multi(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_1.id,
                'value_ids': [(4, self.prod_attr1_v2.id)],
            }), (0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id), (4, self.size_attr_value_m.id)],
            })]
        })

        # produced variants: two variants, simple matrix
        self.assertEqual(len(test_template.product_variant_ids), 2)
        for value in self.size_attr_value_s + self.size_attr_value_m:
            products = self.env['product.product'].search([
                ('product_tmpl_id', '=', test_template.id),
                ('attribute_value_ids', 'in', value.id),
                ('attribute_value_ids', 'in', self.prod_attr1_v2.id)
            ])
            self.assertEqual(len(products), 1)

    def test_variants_creation_matrix(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_1.id,
                'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
            }), (0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id), (4, self.size_attr_value_m.id), (4, self.size_attr_value_l.id)],
            })]
        })

        # produced variants: value matrix : 2x3 values
        self.assertEqual(len(test_template.product_variant_ids), 6)
        for value_1 in self.prod_attr1_v1 + self.prod_attr1_v2:
            for value_2 in self.size_attr_value_m + self.size_attr_value_m + self.size_attr_value_l:
                products = self.env['product.product'].search([
                    ('product_tmpl_id', '=', test_template.id),
                    ('attribute_value_ids', 'in', value_1.id),
                    ('attribute_value_ids', 'in', value_2.id)
                ])
                self.assertEqual(len(products), 1)

    def test_variants_creation_multi_update(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_1.id,
                'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
            }), (0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id), (4, self.size_attr_value_m.id)],
            })]
        })
        size_attribute_line = test_template.attribute_line_ids.filtered(lambda line: line.attribute_id == self.size_attr)
        test_template.write({
            'attribute_line_ids': [(1, size_attribute_line.id, {
                'value_ids': [(4, self.size_attr_value_l.id)],
            })]
        })


class TestVariantsNoCreate(common.TestProductCommon):

    def setUp(self):
        super(TestVariantsNoCreate, self).setUp()
        self.size = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': False,
            'value_ids': [(0, 0, {'name': 'S'}), (0, 0, {'name': 'M'}), (0, 0, {'name': 'L'})],
        })
        self.size_S = self.size.value_ids[0]
        self.size_M = self.size.value_ids[1]
        self.size_L = self.size.value_ids[2]

    def test_create_mono(self):
        """ create a product with a 'nocreate' attribute with a single value """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size.id,
                'value_ids': [(4, self.size_S.id)],
            })],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertFalse(template.product_variant_ids.attribute_value_ids)

    def test_update_mono(self):
        """ modify a product with a 'nocreate' attribute with a single value """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size.id,
                'value_ids': [(4, self.size_S.id)],
            })],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertFalse(template.product_variant_ids.attribute_value_ids)

    def test_create_multi(self):
        """ create a product with a 'nocreate' attribute with several values """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size.id,
                'value_ids': [(6, 0, self.size.value_ids.ids)],
            })],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertFalse(template.product_variant_ids.attribute_value_ids)

    def test_update_multi(self):
        """ modify a product with a 'nocreate' attribute with several values """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size.id,
                'value_ids': [(6, 0, self.size.value_ids.ids)],
            })],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertFalse(template.product_variant_ids.attribute_value_ids)

    def test_create_mixed_mono(self):
        """ create a product with regular and 'nocreate' attributes """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                (0, 0, { # no variants for this one
                    'attribute_id': self.size.id,
                    'value_ids': [(4, self.size_S.id)],
                }),
                (0, 0, { # two variants for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.attribute_value_ids for variant in template.product_variant_ids},
            {self.prod_attr1_v1, self.prod_attr1_v2},
        )

    def test_update_mixed_mono(self):
        """ modify a product with regular and 'nocreate' attributes """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [
                (0, 0, { # no variants for this one
                    'attribute_id': self.size.id,
                    'value_ids': [(4, self.size_S.id)],
                }),
                (0, 0, { # two variants for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.attribute_value_ids for variant in template.product_variant_ids},
            {self.prod_attr1_v1, self.prod_attr1_v2},
        )

    def test_create_mixed_multi(self):
        """ create a product with regular and 'nocreate' attributes """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                (0, 0, { # no variants for this one
                    'attribute_id': self.size.id,
                    'value_ids': [(6, 0, self.size.value_ids.ids)],
                }),
                (0, 0, { # two variants for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.attribute_value_ids for variant in template.product_variant_ids},
            {self.prod_attr1_v1, self.prod_attr1_v2},
        )

    def test_update_mixed_multi(self):
        """ modify a product with regular and 'nocreate' attributes """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [
                (0, 0, { # no variants for this one
                    'attribute_id': self.size.id,
                    'value_ids': [(6, 0, self.size.value_ids.ids)],
                }),
                (0, 0, { # two variants for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(4, self.prod_attr1_v1.id), (4, self.prod_attr1_v2.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.attribute_value_ids for variant in template.product_variant_ids},
            {self.prod_attr1_v1, self.prod_attr1_v2},
        )
