# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
import io
from PIL import Image

from . import common
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, Form


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

    def test_variants_is_product_variant(self):
        template = self.product_7_template
        variants = template.product_variant_ids
        self.assertFalse(template.is_product_variant,
                         'Product template is not a variant')
        self.assertEqual({True}, set(v.is_product_variant for v in variants),
                         'Product variants are variants')

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
        self.assertEqual(test_template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id, self.size_attr_value_s)

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
        self.assertEqual(test_template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id, self.size_attr_value_s + self.prod_attr1_v2)

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
        sofa_attr1_v2 = test_template.attribute_line_ids[0].product_template_value_ids[0]
        sofa_size_s = test_template.attribute_line_ids[1].product_template_value_ids[0]
        sofa_size_m = test_template.attribute_line_ids[1].product_template_value_ids[1]

        # produced variants: two variants, simple matrix
        self.assertEqual(len(test_template.product_variant_ids), 2)
        for ptav in sofa_size_s + sofa_size_m:
            products = self.env['product.product'].search([
                ('product_tmpl_id', '=', test_template.id),
                ('product_template_attribute_value_ids', 'in', ptav.id),
                ('product_template_attribute_value_ids', 'in', sofa_attr1_v2.id)
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

        sofa_attr1_v1 = test_template.attribute_line_ids[0].product_template_value_ids[0]
        sofa_attr1_v2 = test_template.attribute_line_ids[0].product_template_value_ids[1]
        sofa_size_s = test_template.attribute_line_ids[1].product_template_value_ids[0]
        sofa_size_m = test_template.attribute_line_ids[1].product_template_value_ids[1]
        sofa_size_l = test_template.attribute_line_ids[1].product_template_value_ids[2]

        # produced variants: value matrix : 2x3 values
        self.assertEqual(len(test_template.product_variant_ids), 6)
        for value_1 in sofa_attr1_v1 + sofa_attr1_v2:
            for value_2 in sofa_size_s + sofa_size_m + sofa_size_l:
                products = self.env['product.product'].search([
                    ('product_tmpl_id', '=', test_template.id),
                    ('product_template_attribute_value_ids', 'in', value_1.id),
                    ('product_template_attribute_value_ids', 'in', value_2.id)
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

    def test_variants_copy(self):
        template = self.env['product.template'].create({
            'name': 'Test Copy',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.size_attr.id,
                'value_ids': [(4, self.size_attr_value_s.id), (4, self.size_attr_value_m.id)],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(template.name, 'Test Copy')

        # test copy of template
        template_copy = template.copy()
        self.assertEqual(template.name, 'Test Copy')
        self.assertEqual(template_copy.name, 'Test Copy (copy)')
        self.assertEqual(len(template_copy.product_variant_ids), 2)

        # test copy of variant (actually just copying template)
        variant_copy = template_copy.product_variant_ids[0].copy()
        self.assertEqual(template.name, 'Test Copy')
        self.assertEqual(template_copy.name, 'Test Copy (copy)')
        self.assertEqual(variant_copy.name, 'Test Copy (copy) (copy)')
        self.assertEqual(len(variant_copy.product_variant_ids), 2)

    def test_standard_price(self):
        """ Ensure template values are correctly (re)computed depending on the context """
        one_variant_product = self.product_1
        self.assertEqual(one_variant_product.product_variant_count, 1)

        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'CB', 'currency_id': self.env.ref('base.VEF').id})

        self.assertEqual(one_variant_product.cost_currency_id, company_a.currency_id)
        self.assertEqual(one_variant_product.with_company(company_b).cost_currency_id, company_b.currency_id)

        one_variant_template = one_variant_product.product_tmpl_id
        self.assertEqual(one_variant_product.standard_price, one_variant_template.standard_price)
        one_variant_product.with_company(company_b).standard_price = 500.0
        self.assertEqual(
            one_variant_product.with_company(company_b).standard_price,
            one_variant_template.with_company(company_b).standard_price
        )
        self.assertEqual(
            500.0,
            one_variant_template.with_company(company_b).standard_price
        )

    def test_archive_variant(self):
        template = self.env['product.template'].create({
            'name': 'template'
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [(0, False, {
                'attribute_id': self.size_attr.id,
                'value_ids': [
                    (4, self.size_attr.value_ids[0].id, self.size_attr_value_s),
                    (4, self.size_attr.value_ids[1].id, self.size_attr_value_m)
                ],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        variant_1 = template.product_variant_ids[0]
        variant_1.toggle_active()
        self.assertFalse(variant_1.active)
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertEqual(len(template.with_context(
            active_test=False).product_variant_ids), 2)
        variant_1.toggle_active()
        self.assertTrue(variant_1.active)
        self.assertTrue(template.active)

    def test_archive_all_variants(self):
        template = self.env['product.template'].create({
            'name': 'template'
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [(0, False, {
                'attribute_id': self.size_attr.id,
                'value_ids': [
                    (4, self.size_attr.value_ids[0].id, self.size_attr_value_s),
                    (4, self.size_attr.value_ids[1].id, self.size_attr_value_m)
                ],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        variant_1 = template.product_variant_ids[0]
        variant_2 = template.product_variant_ids[1]
        template.product_variant_ids.toggle_active()
        self.assertFalse(variant_1.active, 'Should archive all variants')
        self.assertFalse(template.active, 'Should archive related template')
        variant_1.toggle_active()
        self.assertTrue(variant_1.active, 'Should activate variant')
        self.assertFalse(variant_2.active, 'Should not re-activate other variant')
        self.assertTrue(template.active, 'Should re-activate template')

class TestVariantsNoCreate(common.TestProductCommon):

    def setUp(self):
        super(TestVariantsNoCreate, self).setUp()
        self.size = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'no_variant',
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
        self.assertFalse(template.product_variant_ids.product_template_attribute_value_ids)

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
        self.assertFalse(template.product_variant_ids.product_template_attribute_value_ids)

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
        self.assertFalse(template.product_variant_ids.product_template_attribute_value_ids)

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
        self.assertFalse(template.product_variant_ids.product_template_attribute_value_ids)

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
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
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
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
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
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
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
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
            {self.prod_attr1_v1, self.prod_attr1_v2},
        )

    def test_update_variant_with_nocreate(self):
        """ update variants with a 'nocreate' value on variant """
        template = self.env['product.template'].create({
            'name': 'Sofax',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                (0, 0, { # one variant for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(6, 0, self.prod_attr1_v1.ids)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        template.attribute_line_ids = [(0, 0, {
            'attribute_id': self.size.id,
            'value_ids': [(6, 0, self.size_S.ids)],
        })]
        self.assertEqual(len(template.product_variant_ids), 1)
        # no_variant attribute should not appear on the variant
        self.assertNotIn(self.size_S, template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id)


class TestVariantsManyAttributes(common.TestAttributesCommon):

    def test_01_create_no_variant(self):
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 1)

    def test_02_create_dynamic(self):
        self.attributes.write({'create_variant': 'dynamic'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 0)

    def test_03_create_always(self):
        self.attributes.write({'create_variant': 'always'})
        with self.assertRaises(UserError):
            self.env['product.template'].create({
                'name': 'Toto',
                'attribute_line_ids': [(0, 0, {
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, attribute.value_ids.ids)],
                }) for attribute in self.attributes],
            })

    def test_04_create_no_variant_dynamic(self):
        self.attributes[:5].write({'create_variant': 'dynamic'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 0)

    def test_05_create_no_variant_always(self):
        self.attributes[:2].write({'create_variant': 'always'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 100)

    def test_06_create_dynamic_always(self):
        self.attributes[:5].write({'create_variant': 'dynamic'})
        self.attributes[5:].write({'create_variant': 'always'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 0)

    def test_07_create_no_create_dynamic_always(self):
        self.attributes[3:6].write({'create_variant': 'dynamic'})
        self.attributes[6:].write({'create_variant': 'always'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 0)


class TestVariantsImages(common.TestProductCommon):

    def setUp(self):
        res = super(TestVariantsImages, self).setUp()

        self.colors = OrderedDict([('none', ''), ('red', '#FF0000'), ('green', '#00FF00'), ('blue', '#0000FF')])
        self.images = {}

        product_attribute = self.env['product.attribute'].create({'name': 'Color'})

        self.template = self.env['product.template'].create({
            'name': 'template',
        })

        color_values = self.env['product.attribute.value'].create([{
            'name': color,
            'attribute_id': product_attribute.id,
            'sequence': i,
        } for i, color in enumerate(self.colors)])

        ptal = self.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute.id,
            'product_tmpl_id': self.template.id,
            'value_ids': [(6, 0, color_values.ids)],
        })

        for color_value in ptal.product_template_value_ids[1:]:
            f = io.BytesIO()
            Image.new('RGB', (800, 500), self.colors[color_value.name]).save(f, 'PNG')
            f.seek(0)
            self.images.update({color_value.name: base64.b64encode(f.read())})

            self.template._get_variant_for_combination(color_value).write({
                'image_variant_1920': self.images[color_value.name],
            })
        # the first one has no image
        self.variants = self.template.product_variant_ids

        return res

    def test_variant_images(self):
        """Check that on variant, the image used is the image_variant_1920 if set,
        and defaults to the template image otherwise.
        """
        f = io.BytesIO()
        Image.new('RGB', (800, 500), '#000000').save(f, 'PNG')
        f.seek(0)
        image_black = base64.b64encode(f.read())

        images = self.variants.mapped('image_1920')
        self.assertEqual(len(set(images)), 4)

        variant_no_image = self.variants[0]
        self.assertFalse(variant_no_image.image_1920)
        self.template.image_1920 = image_black

        # the first has no image variant, all the others do
        self.assertFalse(variant_no_image.image_variant_1920)
        self.assertTrue(all(images[1:]))

        # template image is the same as this one, since it has no image variant
        self.assertEqual(variant_no_image.image_1920, self.template.image_1920)
        # having changed the template image should not have changed these
        self.assertEqual(images[1:], self.variants.mapped('image_1920')[1:])

    def test_update_images_with_archived_variants(self):
        """Update images after variants have been archived"""
        self.variants[1:].write({'active': False})
        self.variants[0].image_1920 = self.images['red']
        self.assertEqual(self.template.image_1920, self.images['red'])
        self.assertEqual(self.variants[0].image_variant_1920, False)
        self.assertEqual(self.variants[0].image_1920, self.images['red'])


class TestVariantsArchive(common.TestProductCommon):
    """Once a variant is used on orders/invoices, etc, they can't be unlinked.
       As a result, updating attributes on a product template would simply
       archive the variants instead. We make sure that at each update, we have
       the correct active and inactive records.

       In these tests, we use the commands sent by the JS framework to the ORM
       when using the interface.
    """
    def setUp(self):
        res = super(TestVariantsArchive, self).setUp()

        self.pa_color = self.env['product.attribute'].create({'name': "color", 'sequence': 1})
        color_values = self.env['product.attribute.value'].create([{
            'name': n,
            'sequence': i,
            'attribute_id': self.pa_color.id,
        } for i, n in enumerate(['white', 'black'])])
        self.pav_color_white = color_values[0]
        self.pav_color_black = color_values[1]

        self.pa_size = self.env['product.attribute'].create({'name': "size", 'sequence': 2})
        size_values = self.env['product.attribute.value'].create([{
            'name': n,
            'sequence': i,
            'attribute_id': self.pa_size.id,
        } for i, n in enumerate(['s', 'm'])])
        self.pav_size_s = size_values[0]
        self.pav_size_m = size_values[1]

        self.template = self.env['product.template'].create({
            'name': 'consume product',
            'attribute_line_ids': self._get_add_all_attributes_command(),
        })
        self._update_color_vars(self.template.attribute_line_ids[0])
        self._update_size_vars(self.template.attribute_line_ids[1])
        return res

    def test_01_update_variant_unlink(self):
        """Variants are not used anywhere, so removing an attribute line would
           unlink the variants and create new ones. Nothing too fancy here.
        """
        variants_2x2 = self.template.product_variant_ids
        self._assert_2color_x_2size()

        # Remove the size line, corresponding variants will be removed too since
        # they are used nowhere. Since we only kept color, we should have as many
        # variants as it has values.
        self._remove_ptal_size()
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # We re-add the line we just removed, so we should get new variants.
        self._add_ptal_size_s_m()
        self._assert_2color_x_2size()
        self.assertFalse(self.template.product_variant_ids & variants_2x2)

    def test_02_update_variant_archive_1_value(self):
        """We do the same operations on the template as in the previous test,
           except we simulate that the variants can't be unlinked.

           It follows that variants should be archived instead, so the results
           should all be different from previous test.

           In this test we have a line that has only one possible value:
           this is handled differently than the case where we have more than
           one value, since it does not add new variants.
        """
        self._remove_ptal_size()
        self._add_ptal_size_s()

        # create a patch to make as if one variant was undeletable
        # (e.g. present in a field with ondelete=restrict)
        Product = self.env['product.product']

        def unlink(self):
            raise Exception('just')
        Product._patch_method('unlink', unlink)

        variants_2x1 = self.template.product_variant_ids
        self._assert_2color_x_1size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # Remove the size line, which is the one with only one possible value.
        # Variants should be kept, just the single value removed from them.
        self._remove_ptal_size()
        self.assertEqual(variants_2x1, self.template.product_variant_ids)
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # Add the line just removed, so it is added back to the variants.
        self._add_ptal_size_s()
        self.assertEqual(variants_2x1, self.template.product_variant_ids)
        self._assert_2color_x_1size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        Product._revert_method('unlink')

    def test_02_update_variant_archive_2_value(self):
        """We do the same operations on the template as in the previous tests,
           except we simulate that the variants can't be unlinked.

           It follows that variants should be archived instead, so the results
           should all be different from previous test.
        """
        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        Product._patch_method('unlink', unlink)

        variants_2x2 = self.template.product_variant_ids
        self._assert_2color_x_2size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # CASE remove one attribute line (going from 2*2 to 2*1)
        # Since they can't be unlinked, existing variants should be archived.
        self._remove_ptal_size()
        variants_2x0 = self.template.product_variant_ids
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x2)
        self._assert_2color_x_2size(archived_variants)

        # Add the line just removed, so get back the previous variants.
        # Since they can't be unlinked, existing variants should be archived.
        self._add_ptal_size_s_m()
        self.assertEqual(self.template.product_variant_ids, variants_2x2)
        self._assert_2color_x_2size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x0)
        self._assert_2color_x_0size(archived_variants)

        # we redo the whole remove/read to check
        self._remove_ptal_size()
        self.assertEqual(self.template.product_variant_ids, variants_2x0)
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x2)
        self._assert_2color_x_2size(archived_variants)

        self._add_ptal_size_s_m()
        self.assertEqual(self.template.product_variant_ids, variants_2x2)
        self._assert_2color_x_2size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x0)
        self._assert_2color_x_0size(archived_variants)

        self._remove_ptal_size()
        self.assertEqual(self.template.product_variant_ids, variants_2x0)
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x2)
        self._assert_2color_x_2size(archived_variants)

        # This time we only add one of the two attributes we've been removing.
        # This is a single value line, so the value is simply added to existing
        # variants.
        self._add_ptal_size_s()
        self.assertEqual(self.template.product_variant_ids, variants_2x0)
        self._assert_2color_x_1size()
        self.assertEqual(archived_variants, variants_2x2)
        self._assert_2color_x_2size(archived_variants)

        Product._revert_method('unlink')

    def test_03_update_variant_archive_3_value(self):
        self._remove_ptal_size()
        self._add_ptal_size_s()

        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        Product._patch_method('unlink', unlink)

        self._assert_2color_x_1size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)
        variants_2x1 = self.template.product_variant_ids

        # CASE: remove single value line, no variant change
        self._remove_ptal_size()
        self.assertEqual(self.template.product_variant_ids, variants_2x1)
        self._assert_2color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # CASE: empty combination, this generates a new variant
        self.template.write({'attribute_line_ids': [(2, self.ptal_color.id)]})
        self._assert_0color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x1)
        self._assert_2color_x_0size(archived_variants)  # single value are removed
        variant_0x0 = self.template.product_variant_ids

        # CASE: add single value on empty
        self._add_ptal_size_s()
        self.assertEqual(self.template.product_variant_ids, variant_0x0)
        self._assert_0color_x_1size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x1)
        self._assert_2color_x_0size(archived_variants)  # single value are removed

        # CASE: empty again
        self._remove_ptal_size()
        self.assertEqual(self.template.product_variant_ids, variant_0x0)
        self._assert_0color_x_0size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x1)
        self._assert_2color_x_0size(archived_variants)  # single value are removed

        # CASE: re-add everything
        self.template.write({
            'attribute_line_ids': self._get_add_all_attributes_command(),
        })
        self._update_color_vars(self.template.attribute_line_ids[0])
        self._update_size_vars(self.template.attribute_line_ids[1])
        self._assert_2color_x_2size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x1 + variant_0x0)

        Product._revert_method('unlink')

    def test_04_from_to_single_values(self):
        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        Product._patch_method('unlink', unlink)

        # CASE: remove one value, line becoming single value
        variants_2x2 = self.template.product_variant_ids
        self.ptal_size.write({'value_ids': [(3, self.pav_size_m.id)]})
        self._assert_2color_x_1size()
        self.assertEqual(self.template.product_variant_ids, variants_2x2[0] + variants_2x2[2])
        archived_variants = self._get_archived_variants()
        self._assert_2color_x_1size(archived_variants, ptav=self.ptav_size_m)
        self.assertEqual(archived_variants, variants_2x2[1] + variants_2x2[3])

        # CASE: add back the value
        self.ptal_size.write({'value_ids': [(4, self.pav_size_m.id)]})
        self._assert_2color_x_2size()
        self.assertEqual(self.template.product_variant_ids, variants_2x2)
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # CASE: remove one value, line becoming single value, and then remove
        # the remaining value
        self.ptal_size.write({'value_ids': [(3, self.pav_size_m.id)]})
        self._remove_ptal_size()
        self._assert_2color_x_0size()
        self.assertFalse(self.template.product_variant_ids & variants_2x2)
        archived_variants = self._get_archived_variants()
        self._assert_2color_x_2size(archived_variants)
        self.assertEqual(archived_variants, variants_2x2)
        variants_2x0 = self.template.product_variant_ids

        # CASE: add back the values
        self._add_ptal_size_s_m()
        self._assert_2color_x_2size()
        self.assertEqual(self.template.product_variant_ids, variants_2x2)
        archived_variants = self._get_archived_variants()
        self._assert_2color_x_0size(archived_variants)
        self.assertEqual(archived_variants, variants_2x0)

        Product._revert_method('unlink')

    def test_name_search_dynamic_attributes(self):
        dynamic_attr = self.env['product.attribute'].create({
            'name': 'Dynamic',
            'create_variant': 'dynamic',
            'value_ids': [(0, False, {'name': 'ValueDynamic'})],
        })
        template = self.env['product.template'].create({
            'name': 'cimanyd',
            'attribute_line_ids': [(0, False, {
                'attribute_id': dynamic_attr.id,
                'value_ids': [(4, dynamic_attr.value_ids[0].id, False)],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 0)

        name_searched = self.env['product.template'].name_search(name='cima')
        self.assertIn(template.id, [ng[0] for ng in name_searched])

    def test_uom_update_variant(self):
        """ Changing the uom on the template do not behave the same
        as changing on the product product."""
        units = self.env.ref('uom.product_uom_unit')
        cm = self.env.ref('uom.product_uom_cm')
        template = self.env['product.template'].create({
            'name': 'kardon'
        })

        template_form = Form(template)
        template_form.uom_id = cm
        self.assertEqual(template_form.uom_po_id, cm)
        template = template_form.save()

        variant_form = Form(template.product_variant_ids)
        variant_form.uom_id = units
        self.assertEqual(variant_form.uom_po_id, units)
        variant = variant_form.save()
        self.assertEqual(variant.uom_po_id, units)
        self.assertEqual(template.uom_po_id, units)

    def test_dynamic_attributes_archiving(self):
        Product = self.env['product.product']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        # Patch unlink method to force archiving instead deleting
        def unlink(self):
            self.active = False
        Product._patch_method('unlink', unlink)

        # Creating attributes
        pa_color = ProductAttribute.create({'sequence': 1, 'name': 'color', 'create_variant': 'dynamic'})
        color_values = ProductAttributeValue.create([{
            'name': n,
            'sequence': i,
            'attribute_id': pa_color.id,
        } for i, n in enumerate(['white', 'black'])])
        pav_color_white = color_values[0]
        pav_color_black = color_values[1]

        pa_size = ProductAttribute.create({'sequence': 2, 'name': 'size', 'create_variant': 'dynamic'})
        size_values = ProductAttributeValue.create([{
            'name': n,
            'sequence': i,
            'attribute_id': pa_size.id,
        } for i, n in enumerate(['s', 'm'])])
        pav_size_s = size_values[0]
        pav_size_m = size_values[1]

        pa_material = ProductAttribute.create({'sequence': 3, 'name': 'material', 'create_variant': 'no_variant'})
        material_values = ProductAttributeValue.create([{
            'name': 'Wood',
            'sequence': 1,
            'attribute_id': pa_material.id,
        }])
        pav_material_wood = material_values[0]

        # Define a template with only color attribute & white value
        template = self.env['product.template'].create({
            'name': 'test product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': pa_color.id,
                'value_ids': [(6, 0, [pav_color_white.id])],
            })],
        })

        # Create a variant (because of dynamic attribute)
        ptav_white = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', template.attribute_line_ids.id),
            ('product_attribute_value_id', '=', pav_color_white.id)
        ])
        product_white = template._create_product_variant(ptav_white)

        # Adding a new value to an existing attribute should not archive the variant
        template.write({
            'attribute_line_ids': [(1, template.attribute_line_ids[0].id, {
                'attribute_id': pa_color.id,
                'value_ids': [(4, pav_color_black.id, False)],
            })]
        })
        self.assertTrue(product_white.active)

        # Removing an attribute value should archive the product using it
        template.write({
            'attribute_line_ids': [(1, template.attribute_line_ids[0].id, {
                'value_ids': [(3, pav_color_white.id, 0)],
            })]
        })
        self.assertFalse(product_white.active)
        self.assertFalse(template._is_combination_possible_by_config(
            combination=product_white.product_template_attribute_value_ids,
            ignore_no_variant=True,
        ))

        # Creating a product with the same attributes for testing duplicates
        product_white_duplicate = Product.create({
            'product_tmpl_id': template.id,
            'product_template_attribute_value_ids': [(6, 0, [ptav_white.id])],
            'active': False,
        })
        # Reset archiving for the next assert
        template.write({
            'attribute_line_ids': [(1, template.attribute_line_ids[0].id, {
                'value_ids': [(4, pav_color_white.id, 0)],
            })]
        })
        self.assertTrue(product_white.active)
        self.assertFalse(product_white_duplicate.active)

        # Adding a new attribute should archive the old variant
        template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': pa_size.id,
                'value_ids': [(6, 0, [pav_size_s.id, pav_size_m.id])],
            })]
        })
        self.assertFalse(product_white.active)

        # Reset archiving for the next assert
        template.write({
            'attribute_line_ids': [(3, template.attribute_line_ids[1].id, 0)]
        })
        self.assertTrue(product_white.active)

        # Adding a no_variant attribute should not archive the product
        template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': pa_material.id,
                'value_ids': [(6, 0, [pav_material_wood.id])],
            })]
        })
        self.assertTrue(product_white.active)

        Product._revert_method('unlink')

    def _update_color_vars(self, ptal):
        self.ptal_color = ptal
        self.assertEqual(self.ptal_color.attribute_id, self.pa_color)
        self.ptav_color_white = self.ptal_color.product_template_value_ids[0]
        self.assertEqual(self.ptav_color_white.product_attribute_value_id, self.pav_color_white)
        self.ptav_color_black = self.ptal_color.product_template_value_ids[1]
        self.assertEqual(self.ptav_color_black.product_attribute_value_id, self.pav_color_black)

    def _update_size_vars(self, ptal):
        self.ptal_size = ptal
        self.assertEqual(self.ptal_size.attribute_id, self.pa_size)
        self.ptav_size_s = self.ptal_size.product_template_value_ids[0]
        self.assertEqual(self.ptav_size_s.product_attribute_value_id, self.pav_size_s)
        if len(self.ptal_size.product_template_value_ids) > 1:
            self.ptav_size_m = self.ptal_size.product_template_value_ids[1]
            self.assertEqual(self.ptav_size_m.product_attribute_value_id, self.pav_size_m)

    def _get_add_all_attributes_command(self):
        return [(0, 0, {
            'attribute_id': pa.id,
            'value_ids': [(6, 0, pa.value_ids.ids)],
        }) for pa in self.pa_color + self.pa_size]

    def _get_archived_variants(self):
        # Change context to also get archived values when reading them from the
        # variants.
        return self.env['product.product'].with_context(active_test=False).search([
            ('active', '=', False),
            ('product_tmpl_id', '=', self.template.id)
        ])

    def _remove_ptal_size(self):
        self.template.write({'attribute_line_ids': [(2, self.ptal_size.id)]})

    def _add_ptal_size_s_m(self):
        self.template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.pa_size.id,
                'value_ids': [(6, 0, (self.pav_size_s + self.pav_size_m).ids)],
            })],
        })
        self._update_size_vars(self.template.attribute_line_ids[-1])

    def _add_ptal_size_s(self):
        self.template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.pa_size.id,
                'value_ids': [(6, 0, self.pav_size_s.ids)],
            })],
        })
        self._update_size_vars(self.template.attribute_line_ids[-1])

    def _get_combinations_names(self, combinations):
        return ' | '.join([','.join(c.mapped('name')) for c in combinations])

    def _assert_required_combinations(self, variants, required_values):
        actual_values = [v.product_template_attribute_value_ids for v in variants]
        self.assertEqual(set(required_values), set(actual_values),
            "\nRequired: %s\nActual:   %s" % (self._get_combinations_names(required_values), self._get_combinations_names(actual_values)))

    def _assert_2color_x_2size(self, variants=None):
        """Assert the full matrix 2 color x 2 size"""
        variants = variants or self.template.product_variant_ids
        self.assertEqual(len(variants), 4)
        self._assert_required_combinations(variants, required_values=[
            self.ptav_color_white + self.ptav_size_s,
            self.ptav_color_white + self.ptav_size_m,
            self.ptav_color_black + self.ptav_size_s,
            self.ptav_color_black + self.ptav_size_m,
        ])

    def _assert_2color_x_1size(self, variants=None, ptav=None):
        """Assert the matrix 2 color x 1 size"""
        variants = variants or self.template.product_variant_ids
        self.assertEqual(len(variants), 2)
        self._assert_required_combinations(variants, required_values=[
            self.ptav_color_white + (ptav or self.ptav_size_s),
            self.ptav_color_black + (ptav or self.ptav_size_s),
        ])

    def _assert_2color_x_0size(self, variants=None):
        """Assert the matrix 2 color x no size"""
        variants = variants or self.template.product_variant_ids
        self.assertEqual(len(variants), 2)
        self._assert_required_combinations(variants, required_values=[
            self.ptav_color_white,
            self.ptav_color_black,
        ])

    def _assert_0color_x_1size(self, variants=None):
        """Assert the matrix no color x 1 size"""
        variants = variants or self.template.product_variant_ids
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].product_template_attribute_value_ids, self.ptav_size_s)

    def _assert_0color_x_0size(self, variants=None):
        """Assert the matrix no color x no size"""
        variants = variants or self.template.product_variant_ids
        self.assertEqual(len(variants), 1)
        self.assertFalse(variants[0].product_template_attribute_value_ids)
