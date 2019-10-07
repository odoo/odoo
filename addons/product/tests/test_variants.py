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


class TestVariantsArchive(common.TestProductCommon):
    """Once a variant is used on orders/invoices, etc, they can't be unlinked.
       As a result, updating attributes on a product template would simply archive the variants instead.
       We make sure that at each update, we have the correct number of active and inactive records.

       In these tests, we use the commands sent by the JS framework to the ORM when using the interface
       (even though using 3 commands would simplify the code compared to 2 commands).

       Note that: we don't overly test the ids of archived / modified variants.
       In some cases _create_product_variants reuse existing variants and in other create new ones,
       in a way that is not very predictable (without reading the code).
       We do not enshrine the current behaviour in the tests (yet) as it could change with only moderate functional impact.
       Consequently, if it is intentional the number of archived variants could change,
       in that case update the test; it is there to make sure that a fix is not going to break anything silently.
       The most important is to keep correct numbers of active variants.
    """
    def setUp(self):
        res = super(TestVariantsArchive, self).setUp()

        attribute_values = {
            'color': ['white', 'black'],
            'size': ['s', 'm'],
        }

        self.attributes = {}
        for attr, attr_values in attribute_values.items():
            attribute = self.env['product.attribute'].create({'name': attr})
            values = [self.env['product.attribute.value'].create({'name': name, 'attribute_id': attribute.id})
                      for name in attr_values]
            self.attributes.update({attr: {'a': attribute, 'v': values}})

        attribute_line_ids = [(0, 0, {
                'attribute_id': attr['a'].id,
                'value_ids': [(6, 0, [v.id for v in attr['v']])],
            }) for attr in self.attributes.values()]

        self.template = self.env['product.template'].create({
            'name': 'consume product',
            'attribute_line_ids': attribute_line_ids,
        })

        return res

    def test_update_variant_unlink(self):
        """Variants are not used anywhere, so removing an attribute line would
           unlink the variants and create new ones. Nothing too fancy here.
        """
        lines = self.template.attribute_line_ids
        self.assertEqual(len(self.template.product_variant_ids), 4)
        # we keep lines[0], remove and copy lines[1]
        line_copy_command = {'attribute_id': lines[1].attribute_id.id, 'value_ids': [(6, False, lines[1].value_ids.mapped('id'))]}
        self.template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(self.template.product_variant_ids), len(lines[0].value_ids),
            "Since we only kept line[0], we should have as many variants as it has values")
        archived_products = self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)])
        self.assertFalse(archived_products,
            "Since they are used nowhere, there should not be any archived variant.")
        # we re-add the line we just removed, so we should get new variants
        self.template.write({
            'attribute_line_ids': [
                (4, lines[0].id),
                (0, 'virtual', line_copy_command),
        ]})
        self.assertEqual(len(self.template.product_variant_ids), 4)

    def test_update_variant_archive_1_value(self):
        """We do the same operations on the template as in test_update_variant_unlink,
           except we simulate that the variants can't be unlinked.
           It follows that variants should be archived instead, so the results should all be different from previous test.
           In this test we have a line that have only one possible value:
           this is handled differently than the case where we have more than one,
           since in principle it does not add new variants.
        """
        # we create a new template with a line with only one attribute.
        # Since this does not create any additional variants, the behaviour is a little bit different:
        # it tries to add the new attribute to existing variants if possible
        attribute_line_ids = [(0, 0, {
            'attribute_id': attr['a'].id,
            'value_ids': [(6, 0, [v.id for v in (attr['v'] if attr['a'].display_name == 'color' else attr['v'][:1])])],
        }) for attr in self.attributes.values()]

        template = self.env['product.template'].create({
            'name': 'consume product',
            'attribute_line_ids': attribute_line_ids,
        })

        # create a patch to make as if one variant was undeletable
        # (e.g. present in a field with ondelete=restrict)
        Product = self.env['product.product']
        no_remove = template.product_variant_ids[0].id
        def unlink(self):
            if self.id == no_remove:
                raise Exception('just')
            else:
                return super(Product.__class__, self).unlink()
        Product._patch_method('unlink', unlink)

        variants_ids_history = []

        self.assertEqual(len(template.product_variant_ids), 2)
        variants_ids_history.append(template.product_variant_ids.ids)

        lines = template.attribute_line_ids
        # we keep lines[0], remove and copy lines[1], which is the one with only one possible value
        line_copy_command = {'attribute_id': lines[1].attribute_id.id,
                             'value_ids': [(6, False, lines[1].value_ids.mapped('id'))]}
        template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(lines[0].value_ids), 2)
        self.assertEqual(len(template.product_variant_ids), len(lines[0].value_ids),
                         "Since we only kept line[0], we should have as many variants as it has values")
        variants_ids_history.append(template.product_variant_ids.ids)

        archived_products_1 = self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', template.id)])
        self.assertEqual(len(archived_products_1), 1,
                         "One variant should have been unlinked, not the other.")
        # we re-add the line we just removed, so we should get new variants
        template.write({
            'attribute_line_ids': [
                (4, lines[0].id),
                (0, 'virtual', line_copy_command),
            ]})
        self.assertEqual(len(template.product_variant_ids), 2)
        variants_ids_history.append(template.product_variant_ids.ids)

        archived_products_2 = self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', template.id)])
        self.assertEqual(len(archived_products_2), 1,
                         "We did not reactivate this variant.")

        # tests on ids, see the doc_string
        self.assertEqual(archived_products_1, archived_products_2)
        self.assertEqual(len(set(variants_ids_history[0] + variants_ids_history[1])), 4,
                         "After the first update, we have new active variants.")
        self.assertEqual(len(set(variants_ids_history[1] + variants_ids_history[2])), 2,
                         "After the second update, we kept the same active variants.")

        Product._revert_method('unlink')

    def test_update_variant_archive_2_value(self):
        """We do the same operations on the template as in test_update_variant_unlink,
           except we simulate that the variants can't be unlinked.
           It follows that variants should be archived instead, so the results should all be different from previous test.
        """
        Product = self.env['product.product']
        def unlink(slef):
            raise Exception('just')
        Product._patch_method('unlink', unlink)
        variants_ids_history = []

        self.assertEqual(len(self.template.product_variant_ids), 4)
        variants_ids_history.append(self.template.product_variant_ids.ids)

        lines = self.template.attribute_line_ids
        # we keep lines[0], remove and copy lines[1]
        line_copy_command = {'attribute_id': lines[1].attribute_id.id,
                             'value_ids': [(6, False, lines[1].value_ids.mapped('id'))]}
        line_second_copy_command = {'attribute_id': lines[1].attribute_id.id,
                             'value_ids': [(6, False, lines[1].value_ids[:1].mapped('id'))]}
        self.template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(self.template.product_variant_ids), len(lines[0].value_ids),
                         "Since we only kept line[0], we should have as many variants as it has values")
        variants_ids_history.append(self.template.product_variant_ids.ids)

        archived_products = []
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.assertEqual(len(archived_products[0]), 4,
                         "Since they can't be unlinked, all variants should be archived.")
        # we re-add the line we just removed, so we should get new variants
        self.template.write({
            'attribute_line_ids': [
                (4, lines[0].id),
                (0, 'virtual', line_copy_command),
            ]})
        self.assertEqual(len(self.template.product_variant_ids), 4)
        variants_ids_history.append(self.template.product_variant_ids.ids)

        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.assertEqual(len(archived_products[1]), 2,
                         "Since they can't be unlinked, all previous variants should be archived.")

        # we redo the whole remove/readd to check
        lines = self.template.attribute_line_ids
        self.template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(self.template.product_variant_ids), 2)
        variants_ids_history.append(self.template.product_variant_ids.ids)
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.template.write({
            'attribute_line_ids': [
                (4, lines[0].id),
                (0, 'virtual', line_copy_command),
            ]})
        self.assertEqual(len(self.template.product_variant_ids), 4)
        variants_ids_history.append(self.template.product_variant_ids.ids)
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.assertEqual(len(archived_products[3]), 2)

        # now we test when we try to add the value back on existing products
        lines = self.template.attribute_line_ids
        self.template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(self.template.product_variant_ids), 2)
        variants_ids_history.append(self.template.product_variant_ids.ids)
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.assertEqual(len(archived_products[4]), 4)
        # this time we only add one of the two attributes we've been removing
        self.template.write({
            'attribute_line_ids': [
                (4, lines[0].id),
                (0, 'virtual', line_second_copy_command),
            ]})
        self.assertEqual(len(self.template.product_variant_ids), 2)
        variants_ids_history.append(self.template.product_variant_ids.ids)
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', self.template.id)]))
        self.assertEqual(len(archived_products[5]), 4)

        Product._revert_method('unlink')

    def test_update_variant_archive_3_value(self):
        """In this one, we have unique values for one lines, and one line with two values.
           We first remove the unique line to populate archived variants, then remove the two values line.
           Finally, we re-add athe two lines, bringing us back to the first situation:
           we should not have any more than two variants (rest should be archived)
        """
        attribute_line_ids = [(0, 0, {
            'attribute_id': attr['a'].id,
            'value_ids': [(6, 0, [v.id for v in (attr['v'] if attr['a'].display_name == 'color' else attr['v'][:1])])],
        }) for attr in self.attributes.values()]

        template = self.env['product.template'].create({
            'name': 'consume product',
            'attribute_line_ids': attribute_line_ids,
        })

        Product = self.env['product.product']
        def unlink(slef):
            raise Exception('just')
        Product._patch_method('unlink', unlink)

        variants_ids_history = []
        self.assertEqual(len(template.product_variant_ids), 2)
        variants_ids_history.append(template.product_variant_ids.ids)

        lines = template.attribute_line_ids

        template.write({'attribute_line_ids': [(4, lines[0].id), (2, lines[1].id)]})
        self.assertEqual(len(template.product_variant_ids), len(lines[0].value_ids),
                         "Since we only kept line[0], we should have as many variants as it has values")
        variants_ids_history.append(template.product_variant_ids.ids)

        archived_products = []
        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', template.id)]))
        self.assertEqual(len(archived_products[0]), 2,
                         "Since they can't be unlinked, all variants should be archived.")

        template.write({'attribute_line_ids': [(2, lines[0].id)]})
        self.assertEqual(len(template.product_variant_ids), 1)
        variants_ids_history.append(template.product_variant_ids.ids)

        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', template.id)]))
        self.assertEqual(len(archived_products[1]), 4,
                         "Since they can't be unlinked, all previous variants should be archived.")

        # we re-add everything:
        template.write({'attribute_line_ids': attribute_line_ids})

        archived_products.append(self.env['product.product'].search(
            [('active', '=', False), ('product_tmpl_id', '=', template.id)]))
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(len(archived_products[2]), 3,
                         "We should have re-activated one variant only.")

        Product._revert_method('unlink')

    def test_name_search_dynamic_attributes(self):
        dynamic_attr = self.env['product.attribute'].create({
            'name': 'Dynamic',
            'create_variant': 'dynamic',
            'value_ids': [(0, False, {'name': 'ValueDynamic'})],
        })
        template = self.env['product.template'].create({
            'name': 'cimanyd'
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [(0, False, {
                'attribute_id': dynamic_attr.id,
                'value_ids': [(4, dynamic_attr.value_ids[0].id, False)],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 0)

        name_searched = self.env['product.template'].name_search(name='cima')
        self.assertIn(template.id, [ng[0] for ng in name_searched])
