# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from PIL import Image

from . import common
from odoo.exceptions import UserError
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

    def test_update_variant_with_nocreate(self):
        """ update variants with a 'nocreate' value on variant """
        template = self.env['product.template'].create({
            'name': 'Sofax',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                (0, 0, { # one variant for this one
                    'attribute_id': self.prod_att_1.id,
                    'value_ids': [(4, self.prod_attr1_v1.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        for variant_id in template.product_variant_ids:
            variant_id.attribute_value_ids += self.size_S
        template.attribute_line_ids += template.attribute_line_ids.browse()
        self.assertEqual(len(template.product_variant_ids), 1)


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

        self.colors = {'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF'}
        self.images = {}

        product_attribute = self.env['product.attribute'].create({'name': 'Color'})

        self.template = self.env['product.template'].create({
            'name': 'template',
        })

        for color in self.colors:
            attr = self.env['product.attribute.value'].create({
                'name': color,
                'attribute_id': product_attribute.id,
            })

            f = io.BytesIO()
            Image.new('RGB', (800, 500), self.colors[color]).save(f, 'PNG')
            f.seek(0)
            self.images.update({color: base64.b64encode(f.read())})

            self.env['product.product'].create({
                'image_variant': self.images[color],
                'attribute_value_ids': [(6, 0, [attr.id])],
                'product_tmpl_id': self.template.id,
            })
        # the first one has no image, no color
        self.variants = self.template.product_variant_ids.sorted('id')

        return res

    def test_variant_images(self):
        """Check that on variant, the image used is the image_variant if set,
        and defaults to the template image otherwise.
        """
        f = io.BytesIO()
        Image.new('RGB', (800, 500), '#000000').save(f, 'PNG')
        f.seek(0)
        image_black = base64.b64encode(f.read())

        images = self.variants.mapped('image_variant')
        self.assertEqual(len(set(images)), 4)

        variant_no_image = self.variants[0]
        self.assertFalse(variant_no_image.image)
        self.template.image = image_black

        # the first has no image variant, all the others do
        self.assertFalse(variant_no_image.image_variant)
        self.assertTrue(all(images[1:]))

        # template image is the same as this one, since it has no image variant
        self.assertEqual(variant_no_image.image, self.template.image)
        # having changed the template image should not have changed these
        self.assertEqual(images[1:], self.variants.mapped('image')[1:])


    def test_update_images_with_archived_variants(self):
        """Update images after variants have been archived"""
        self.variants[1:].write({'active': False})
        self.variants[0].image = self.images['red']
        self.assertEqual(self.template.image, self.images['red'])
        self.assertEqual(self.variants[0].image_variant, False)
        self.assertEqual(self.variants[0].image, self.images['red'])
