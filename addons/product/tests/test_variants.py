# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from datetime import timedelta
from unittest.mock import patch

import io
import unittest.mock

from PIL import Image

from odoo.fields import Command
from odoo.exceptions import UserError
from odoo.tests import tagged, TransactionCase, Form
from odoo.tools import mute_logger

from odoo.addons.product.tests.common import ProductVariantsCommon, ProductAttributesCommon


@tagged('post_install', '-at_install')
class TestVariantsSearch(ProductVariantsCommon):

    def test_attribute_line_search(self):
        search_not_to_be_found = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'M')]
        )
        self.assertNotIn(self.product_template_shirt, search_not_to_be_found,
                         'Shirt should not be found searching M')

        search_attribute = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'Size')]
        )
        self.assertIn(self.product_template_shirt, search_attribute,
                      'Shirt should be found searching Size')

        search_value = self.env['product.template'].search(
            [('attribute_line_ids', '=', 'L')]
        )
        self.assertIn(self.product_template_shirt, search_value,
                      'Shirt should be found searching L')

    def test_name_search(self):
        self.product_slip_template = self.env['product.template'].create({
            'name': 'Slip',
            'default_code': 'ABC',
        })
        res = self.env['product.product'].name_search('Shirt', [], 'not ilike', None)
        res_ids = [r[0] for r in res]
        self.assertIn(self.product_slip_template.product_variant_ids.id, res_ids,
                      'Slip should be found searching \'not ilike\'')

        templates = self.product_slip_template.name_search(
            "ABC",
            [['id', '!=', -1]],
        )
        self.assertFalse(templates, "Should not return template when searching on code")
        templates = self.product_slip_template.with_context(search_product_product=True).name_search(
            "ABC",
            [['id', '!=', -1]],
        )
        self.assertTrue(templates, "Should return template when searching on code")

        templates = self.product_slip_template.with_context(search_product_product=True).name_search(
            "ABC",
            [['id', '!=', self.product_slip_template.id]],
        )
        self.assertFalse(templates, "Should not return template.")

@tagged('post_install', '-at_install')
class TestVariants(ProductVariantsCommon):

    def test_variants_is_product_variant(self):
        template = self.product_template_sofa
        variants = template.product_variant_ids
        self.assertFalse(template.is_product_variant,
                         'Product template is not a variant')
        self.assertEqual({True}, set(v.is_product_variant for v in variants),
                         'Product variants are variants')

    def test_variants_pricelist_code(self):
        vendor = self.env['res.partner'].create({'name': 'Bidou', 'email': 'bidou@odoo.com'})
        codes = ['bidou-red', 'bidou-green', 'bidou-blue']
        self.env['product.supplierinfo'].create([{
            'partner_id': vendor.id,
            'product_tmpl_id': self.product_template_sofa.id,
            'product_id': product.id,
            'product_code': code,
        } for product, code in zip(self.product_template_sofa.product_variant_ids, codes)])
        variants = self.product_template_sofa.product_variant_ids.with_context(partner_id=vendor.id)
        self.assertEqual(variants[0].code, codes[0], "sofa red should have code bidou-red")
        self.assertEqual(variants[1].code, codes[1], "sofa green should have code bidou-green")
        self.assertEqual(variants[2].code, codes[2], "sofa blue should have code bidou-blue")

    def test_variants_creation_mono(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id)],
            })]
        })

        # produced variants: one variant, because mono value
        self.assertEqual(len(test_template.product_variant_ids), 1)
        self.assertEqual(test_template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id, self.size_attribute_s)

    def test_variants_creation_mono_double(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.color_attribute.id,
                'value_ids': [Command.link(self.color_attribute_blue.id)],
            }), Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id)],
            })]
        })

        # produced variants: one variant, because only 1 combination is possible
        self.assertEqual(len(test_template.product_variant_ids), 1)
        self.assertEqual(test_template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id, self.size_attribute_s + self.color_attribute_blue)

    def test_variants_creation_mono_multi(self):
        test_template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.link(self.color_attribute_blue.id)],
                }), Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [Command.link(self.size_attribute_s.id), Command.link(self.size_attribute_m.id)],
                }),
            ],
        })
        size_attribute_line = test_template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.size_attribute
        )
        color_attribute_line = test_template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.color_attribute
        )
        sofa_attr1_v2 = color_attribute_line.product_template_value_ids[0]
        sofa_size_s = size_attribute_line.product_template_value_ids[0]
        sofa_size_m = size_attribute_line.product_template_value_ids[1]

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
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.set([self.color_attribute_red.id, self.color_attribute_blue.id])],
                }), Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [Command.set(self.size_attribute.value_ids.ids)],
                }),
            ],
        })

        size_attribute_line = test_template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.size_attribute
        )
        color_attribute_line = test_template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.color_attribute
        )
        sofa_attr1_v1 = color_attribute_line.product_template_value_ids[0]
        sofa_attr1_v2 = color_attribute_line.product_template_value_ids[1]
        sofa_size_s = size_attribute_line.product_template_value_ids[0]
        sofa_size_m = size_attribute_line.product_template_value_ids[1]
        sofa_size_l = size_attribute_line.product_template_value_ids[2]

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
            'attribute_line_ids': [Command.create({
                'attribute_id': self.color_attribute.id,
                'value_ids': [Command.link(self.color_attribute_red.id), Command.link(self.color_attribute_blue.id)],
            }), Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id), Command.link(self.size_attribute_m.id)],
            })]
        })
        size_attribute_line = test_template.attribute_line_ids.filtered(lambda line: line.attribute_id == self.size_attribute)
        test_template.write({
            'attribute_line_ids': [(1, size_attribute_line.id, {
                'value_ids': [Command.link(self.size_attribute_l.id)],
            })]
        })

    def test_variants_copy(self):
        template = self.env['product.template'].create({
            'name': 'Test Copy',
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id), Command.link(self.size_attribute_m.id)],
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

    def test_dynamic_variants_copy(self):
        self.color_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'dynamic'})
        self.color_attr_value_r = self.env['product.attribute.value'].create({'name': 'Red', 'attribute_id': self.color_attr.id})
        self.color_attr_value_b = self.env['product.attribute.value'].create({'name': 'Blue', 'attribute_id': self.color_attr.id})

        # test copy of variant with dynamic attribute
        template_dyn = self.env['product.template'].create({
            'name': 'Test Dynamical',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.color_attr.id,
                'value_ids': [(4, self.color_attr_value_r.id), (4, self.color_attr_value_b.id)],
            })]
        })

        self.assertEqual(len(template_dyn.product_variant_ids), 0)
        self.assertEqual(template_dyn.name, 'Test Dynamical')

        variant_dyn = template_dyn._create_product_variant(template_dyn._get_first_possible_combination())
        if 'create_product_product' in variant_dyn._context:
            new_context = dict(variant_dyn._context)
            new_context.pop('create_product_product')
            variant_dyn = variant_dyn.with_context(new_context)
        self.assertEqual(len(template_dyn.product_variant_ids), 1)

        variant_dyn_copy = variant_dyn.copy()
        template_dyn_copy = variant_dyn_copy.product_tmpl_id
        self.assertEqual(len(template_dyn_copy.product_variant_ids), 1)
        self.assertEqual(template_dyn_copy.name, 'Test Dynamical (copy)')

    def test_standard_price(self):
        """ Ensure template values are correctly (re)computed depending on the context """
        one_variant_product = self.product
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

    @mute_logger('odoo.models.unlink')
    def test_archive_variant(self):
        template = self.env['product.template'].create({
            'name': 'template'
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [
                    Command.link(self.size_attribute_s.id),
                    Command.link(self.size_attribute_m.id),
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

    @mute_logger('odoo.models.unlink')
    def test_template_barcode(self):
        template = self.env['product.template'].create({
            'name': 'template',
            'barcode': 'test',
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertEqual(template.barcode, 'test')

        template.product_variant_ids.action_archive()
        self.assertFalse(template.active)
        template.invalidate_model(['barcode'])
        self.assertEqual(template.barcode, 'test')
        template.product_variant_ids.action_unarchive()
        template.action_unarchive()

        template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [
                    Command.link(self.size_attribute_s.id),
                    Command.link(self.size_attribute_m.id),
                ],
            })]
        })
        self.assertFalse(template.barcode)  # 2 active variants --> no barcode on template

        variant_1 = template.product_variant_ids[0]
        variant_2 = template.product_variant_ids[1]

        variant_1.barcode = 'v1_barcode'
        variant_2.barcode = 'v2_barcode'

        variant_1.action_archive()
        template.invalidate_model(['barcode'])
        self.assertEqual(template.barcode, variant_2.barcode)  # 1 active variant --> barcode on template

        variant_1.action_unarchive()
        template.invalidate_model(['barcode'])
        self.assertFalse(template.barcode)  # 2 active variants --> no barcode on template

    @mute_logger('odoo.models.unlink')
    def test_archive_all_variants(self):
        template = self.env['product.template'].create({
            'name': 'template'
        })
        self.assertEqual(len(template.product_variant_ids), 1)

        template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [
                    Command.link(self.size_attribute_s.id),
                    Command.link(self.size_attribute_m.id),
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

    def test_open_product_form_with_default_uom_id_is_false(self):
        """ Test default UoM is False when creating a product. """
        uom_unit = self.env.ref('uom.product_uom_unit')
        product_form = Form(self.env['product.product'].with_context(
            default_uom_id=False,
        ))
        product_form.name = 'Test Product'
        product = product_form.save()
        self.assertEqual(uom_unit, product.uom_id)

@tagged('post_install', '-at_install')
class TestVariantsNoCreate(ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.size_attribute.create_variant = 'no_variant'

    def test_create_mono(self):
        """ create a product with a 'nocreate' attribute with a single value """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id)],
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
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.link(self.size_attribute_s.id)],
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
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.set(self.size_attribute.value_ids.ids)],
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
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [(6, 0, self.size_attribute.value_ids.ids)],
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
                Command.create({ # no variants for this one
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [Command.link(self.size_attribute_s.id)],
                }),
                Command.create({ # two variants for this one
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.link(self.color_attribute_red.id), Command.link(self.color_attribute_blue.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
            {self.color_attribute_red, self.color_attribute_blue},
        )

    @mute_logger('odoo.models.unlink')
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
                Command.create({ # no variants for this one
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [Command.link(self.size_attribute_s.id)],
                }),
                Command.create({ # two variants for this one
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.link(self.color_attribute_red.id), Command.link(self.color_attribute_blue.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
            {self.color_attribute_red, self.color_attribute_blue},
        )

    def test_create_mixed_multi(self):
        """ create a product with regular and 'nocreate' attributes """
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                Command.create({ # no variants for this one
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [(6, 0, self.size_attribute.value_ids.ids)],
                }),
                Command.create({ # two variants for this one
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.link(self.color_attribute_red.id), Command.link(self.color_attribute_blue.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
            {self.color_attribute_red, self.color_attribute_blue},
        )

    @mute_logger('odoo.models.unlink')
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
                Command.create({ # no variants for this one
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [(6, 0, self.size_attribute.value_ids.ids)],
                }),
                Command.create({ # two variants for this one
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.link(self.color_attribute_red.id), Command.link(self.color_attribute_blue.id)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            {variant.product_template_attribute_value_ids.product_attribute_value_id for variant in template.product_variant_ids},
            {self.color_attribute_red, self.color_attribute_blue},
        )

    def test_update_variant_with_nocreate(self):
        """ update variants with a 'nocreate' value on variant """
        template = self.env['product.template'].create({
            'name': 'Sofax',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'attribute_line_ids': [
                Command.create({ # one variant for this one
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [(6, 0, self.color_attribute_red.ids)],
                }),
            ],
        })
        self.assertEqual(len(template.product_variant_ids), 1)
        template.attribute_line_ids = [Command.create({
            'attribute_id': self.size_attribute.id,
            'value_ids': [(6, 0, self.size_attribute_s.ids)],
        })]
        self.assertEqual(len(template.product_variant_ids), 1)
        # no_variant attribute should not appear on the variant
        self.assertNotIn(self.size_attribute_s, template.product_variant_ids.product_template_attribute_value_ids.product_attribute_value_id)

    def test_unarchive_multiple_products_with_variants(self):
        product_attribut = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 1,
            'create_variant': 'dynamic',
        })
        attr_value = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': product_attribut.id,
            'sequence': 1,
        })
        first_product = self.env['product.template'].create({
            'name': 'Sofa',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': product_attribut.id,
                'value_ids': [(6, 0, [attr_value.id])],
            })]
        })
        second_product = first_product.copy({
            'product_variant_ids': [(0, 0, {
            'name': 'Sofa',
            })]
        })

        products = first_product + second_product
        products.action_archive()
        self.assertFalse(first_product.active)
        self.assertFalse(second_product.active)
        self.assertFalse(second_product.product_variant_ids)
        products.action_unarchive()
        # check products should be unarchived successfully.
        self.assertTrue(first_product.active)
        self.assertTrue(second_product.active)
        self.assertTrue(second_product.product_variant_ids)

@tagged('post_install', '-at_install')
class TestVariantsManyAttributes(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # create 10 attributes with 10 values each
        cls.attributes = cls.env['product.attribute'].create([
            {
                'name': name,
                'create_variant': 'no_variant',
                'value_ids': [Command.create({'name': n}) for n in range(10)]
            } for name in "ABCDEFGHIJ"
        ])

    def test_01_create_no_variant(self):
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [Command.create({
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
            'attribute_line_ids': [Command.create({
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
                'attribute_line_ids': [Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, attribute.value_ids.ids)],
                }) for attribute in self.attributes],
            })

    def test_04_create_no_variant_dynamic(self):
        self.attributes[:5].write({'create_variant': 'dynamic'})
        toto = self.env['product.template'].create({
            'name': 'Toto',
            'attribute_line_ids': [Command.create({
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
            'attribute_line_ids': [Command.create({
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
            'attribute_line_ids': [Command.create({
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
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            }) for attribute in self.attributes],
        })
        self.assertEqual(len(toto.attribute_line_ids.mapped('attribute_id')), 10)
        self.assertEqual(len(toto.attribute_line_ids.mapped('value_ids')), 100)
        self.assertEqual(len(toto.product_variant_ids), 0)


@tagged('post_install', '-at_install')
class TestVariantsImages(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        cls.colors = OrderedDict([
            ('none', ''),
            ('red', '#FF0000'),
            ('green', '#00FF00'),
            ('blue', '#0000FF'),
        ])
        cls.images = {}

        product_attribute = cls.env['product.attribute'].create({'name': 'Color'})

        cls.template = cls.env['product.template'].create({
            'name': 'template',
        })

        color_values = cls.env['product.attribute.value'].create([{
            'name': color,
            'attribute_id': product_attribute.id,
            'sequence': i,
        } for i, color in enumerate(cls.colors)])

        ptal = cls.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute.id,
            'product_tmpl_id': cls.template.id,
            'value_ids': [(6, 0, color_values.ids)],
        })

        for color_value in ptal.product_template_value_ids[1:]:
            f = io.BytesIO()
            Image.new('RGB', (800, 500), cls.colors[color_value.name]).save(f, 'PNG')
            f.seek(0)
            cls.images.update({color_value.name: base64.b64encode(f.read())})

            cls.template._get_variant_for_combination(color_value).write({
                'image_variant_1920': cls.images[color_value.name],
            })
        # the first one has no image
        cls.variants = cls.template.product_variant_ids

        return res

    def test_variant_images(self):
        """Check that on variant, the image used is the image_variant_1920 if set,
        and defaults to the template image otherwise.
        """
        # Pretend setup happened in an older transaction by updating on the SQL layer and making sure it gets reloaded
        # Using _write() instead of write() because write() only allows updating log access fields at boot time
        before = self.cr.now() - timedelta(milliseconds=1)
        self.template._write({
            'create_date': before,
            'write_date': before,
        })
        self.variants._write({
            'create_date': before,
            'write_date': before,
        })
        self.template.invalidate_recordset(['create_date', 'write_date'])
        self.variants.invalidate_recordset(['create_date', 'write_date'])

        f = io.BytesIO()
        Image.new('RGB', (800, 500), '#000000').save(f, 'PNG')
        f.seek(0)
        image_black = base64.b64encode(f.read())

        images = self.variants.mapped('image_1920')
        self.assertEqual(len(set(images)), 4)
        variant_no_image = self.variants[0]
        old_last_update = variant_no_image.write_date

        self.assertFalse(variant_no_image.image_1920)
        self.template.image_1920 = image_black
        new_last_update = variant_no_image.write_date

        # the first has no image variant, all the others do
        self.assertFalse(variant_no_image.image_variant_1920)
        self.assertTrue(all(images[1:]))

        # template image is the same as this one, since it has no image variant
        self.assertEqual(variant_no_image.image_1920, self.template.image_1920)
        # having changed the template image should not have changed these
        self.assertEqual(images[1:], self.variants.mapped('image_1920')[1:])

        # last update changed for the variant without image
        self.assertLess(old_last_update, new_last_update)

    def test_update_images_with_archived_variants(self):
        """Update images after variants have been archived"""
        self.variants[1:].write({'active': False})
        self.variants[0].image_1920 = self.images['red']
        self.assertEqual(self.template.image_1920, self.images['red'])
        self.assertEqual(self.variants[0].image_variant_1920, False)
        self.assertEqual(self.variants[0].image_1920, self.images['red'])


@tagged('post_install', '-at_install')
class TestVariantsArchive(ProductVariantsCommon):
    """Once a variant is used on orders/invoices, etc, they can't be unlinked.
       As a result, updating attributes on a product template would simply
       archive the variants instead. We make sure that at each update, we have
       the correct active and inactive records.

       In these tests, we use the commands sent by the JS framework to the ORM
       when using the interface.
    """
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        cls.template = cls.env['product.template'].create({
            'name': 'consume product',
            'attribute_line_ids': cls._get_add_all_attributes_command(),
        })
        cls.ptal_color = cls.template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == cls.color_attribute
        )
        cls.ptav_color_white = cls.ptal_color.product_template_value_ids[0]
        cls.ptav_color_black = cls.ptal_color.product_template_value_ids[1]

        cls.ptal_size = cls.template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == cls.size_attribute
        )
        cls.ptav_size_s = cls.ptal_size.product_template_value_ids[0]
        if len(cls.ptal_size.product_template_value_ids) > 1:
            cls.ptav_size_m = cls.ptal_size.product_template_value_ids[1]
        return res

    @mute_logger('odoo.models.unlink')
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

    @mute_logger('odoo.models.unlink')
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
        self.patch(type(Product), 'unlink', unlink)

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

    def test_02_update_variant_archive_2_value(self):
        """We do the same operations on the template as in the previous tests,
           except we simulate that the variants can't be unlinked.

           It follows that variants should be archived instead, so the results
           should all be different from previous test.
        """
        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        self.patch(type(Product), 'unlink', unlink)

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

    @mute_logger('odoo.models.unlink')
    def test_03_update_variant_archive_3_value(self):
        self._remove_ptal_size()
        self._add_ptal_size_s()

        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        self.patch(type(Product), 'unlink', unlink)

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
        self._update_color_vars(self._get_ptal_color())
        self._update_size_vars(self._get_ptal_size())
        self._assert_2color_x_2size()
        archived_variants = self._get_archived_variants()
        self.assertEqual(archived_variants, variants_2x1 + variant_0x0)

    def test_04_from_to_single_values(self):
        Product = self.env['product.product']

        def unlink(slef):
            raise Exception('just')
        self.patch(type(Product), 'unlink', unlink)

        # CASE: remove one value, line becoming single value
        variants_2x2 = self.template.product_variant_ids
        self.ptal_size.write({'value_ids': [(3, self.size_attribute_m.id)]})
        self._assert_2color_x_1size()
        self.assertEqual(self.template.product_variant_ids, variants_2x2[0] + variants_2x2[2])
        archived_variants = self._get_archived_variants()
        self._assert_2color_x_1size(archived_variants, ptav=self.ptav_size_m)
        self.assertEqual(archived_variants, variants_2x2[1] + variants_2x2[3])

        # CASE: add back the value
        self.ptal_size.write({'value_ids': [Command.link(self.size_attribute_m.id)]})
        self._assert_2color_x_2size()
        self.assertEqual(self.template.product_variant_ids, variants_2x2)
        archived_variants = self._get_archived_variants()
        self.assertFalse(archived_variants)

        # CASE: remove one value, line becoming single value, and then remove
        # the remaining value
        self.ptal_size.write({'value_ids': [(3, self.size_attribute_m.id)]})
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

    def test_name_search_dynamic_attributes(self):
        # To be able to test dynamic variant "variants" feature must be set up
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_product_variant').id)]})
        dynamic_attr = self.env['product.attribute'].create({
            'name': 'Dynamic',
            'create_variant': 'dynamic',
            'value_ids': [Command.create({'name': 'ValueDynamic'})],
        })
        template = self.env['product.template'].create({
            'name': 'cimanyd',
            'attribute_line_ids': [Command.create({
                'attribute_id': dynamic_attr.id,
                'value_ids': [Command.link(dynamic_attr.value_ids[0].id)],
            })]
        })
        self.assertEqual(len(template.product_variant_ids), 0)

        name_searched = self.env['product.template'].name_search(name='cima')
        self.assertIn(template.id, [ng[0] for ng in name_searched])

    @mute_logger('odoo.models.unlink')
    def test_uom_update_variant(self):
        """ Changing the uom on the template do not behave the same
        as changing on the product product."""
        # Required for `uom_id` to be visible in the view
        self._enable_uom()

        units = self.uom_unit
        cm = self.env.ref('uom.product_uom_cm')
        template = self.product.product_tmpl_id

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

    @mute_logger('odoo.models.unlink')
    def test_dynamic_attributes_archiving(self):
        Product = self.env['product.product']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        # Patch unlink method to force archiving instead deleting
        def unlink(self):
            self.active = False
        self.patch(type(Product), 'unlink', unlink)

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
            'attribute_line_ids': [Command.create({
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
                'value_ids': [Command.link(pav_color_black.id)],
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
                'value_ids': [Command.link(pav_color_white.id)],
            })]
        })
        self.assertTrue(product_white.active)
        self.assertFalse(product_white_duplicate.active)

        # Adding a new attribute should archive the old variant
        template.write({
            'attribute_line_ids': [Command.create({
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
            'attribute_line_ids': [Command.create({
                'attribute_id': pa_material.id,
                'value_ids': [(6, 0, [pav_material_wood.id])],
            })]
        })
        self.assertTrue(product_white.active)

    def test_set_barcode(self):
        tmpl = self.product.product_tmpl_id
        tmpl.barcode = '123'
        self.assertEqual(tmpl.barcode, '123')
        self.assertEqual(self.product.barcode, '123')

        tmpl.toggle_active()

        tmpl.barcode = '456'
        tmpl.invalidate_recordset(fnames=['barcode'])
        self.assertEqual(tmpl.barcode, '456')
        self.assertEqual(self.product.barcode, '456')

    def _update_color_vars(self, ptal):
        self.ptal_color = ptal
        self.assertEqual(self.ptal_color.attribute_id, self.color_attribute)
        self.ptav_color_red = self.ptal_color.product_template_value_ids[0]
        self.assertEqual(self.ptav_color_red.product_attribute_value_id, self.color_attribute_red)
        self.ptav_color_blue = self.ptal_color.product_template_value_ids[1]
        self.assertEqual(self.ptav_color_blue.product_attribute_value_id, self.color_attribute_blue)

    def _update_size_vars(self, ptal):
        self.ptal_size = ptal
        self.assertEqual(self.ptal_size.attribute_id, self.size_attribute)
        self.ptav_size_s = self.ptal_size.product_template_value_ids[0]
        self.assertEqual(self.ptav_size_s.product_attribute_value_id, self.size_attribute_s)
        if len(self.ptal_size.product_template_value_ids) > 1:
            self.ptav_size_m = self.ptal_size.product_template_value_ids[1]
            self.assertEqual(self.ptav_size_m.product_attribute_value_id, self.size_attribute_m)

    @classmethod
    def _get_add_all_attributes_command(cls):
        return [
            Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([cls.color_attribute_red.id, cls.color_attribute_blue.id])],
            }),
            Command.create({
                'attribute_id': cls.size_attribute.id,
                'value_ids': [Command.set([cls.size_attribute_s.id, cls.size_attribute_m.id])],
            })
        ]

    def _get_archived_variants(self):
        # Change context to also get archived values when reading them from the
        # variants.
        return self.env['product.product'].with_context(active_test=False).search([
            ('active', '=', False),
            ('product_tmpl_id', '=', self.template.id)
        ])

    def _get_ptal_size(self):
        return self.template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.size_attribute
        )

    def _get_ptal_color(self):
        return self.template.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.color_attribute
        )

    def _remove_ptal_size(self):
        self.template.write({'attribute_line_ids': [(2, self.ptal_size.id)]})

    def _add_ptal_size_s_m(self):
        self.template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [(6, 0, (self.size_attribute_s + self.size_attribute_m).ids)],
            })],
        })
        self._update_size_vars(self._get_ptal_size())

    def _add_ptal_size_s(self):
        self.template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [(6, 0, self.size_attribute_s.ids)],
            })],
        })
        self._update_size_vars(self._get_ptal_size())

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

    @mute_logger('odoo.models.unlink')
    def test_unlink_and_archive_multiple_variants(self):
        """
        Test unlinking multiple variants in various scenarios
        - Unlink one archived variant
        - Unlink one archived and one active variant
        - Unlink multiple archived variants and multiple active variants at once
        """
        products = self.env['product.product'].create([
            {'name': 'variant 1', 'description': 'var 1'},
            {'name': 'variant 2', 'description': 'var 2'},
            {'name': 'variant 3', 'description': 'var 3'},
            {'name': 'variant 4', 'description': 'var 4'},
            {'name': 'variant 5', 'description': 'var 5'},
            {'name': 'variant 6', 'description': 'var 6'},
            {'name': 'variant 7', 'description': 'var 7'},
        ])
        # Unlink one archived variant
        products[0].action_archive()
        products[0].unlink()
        self.assertFalse(products[0].exists())

        # Unlink one archived and one active variant
        products[1].action_archive()
        active_and_archived = products[1] + products[2]
        active_and_archived.unlink()
        self.assertFalse(active_and_archived.exists())

        # Unlink multiple archived variants and multiple active variants at once
        multiple_archived = products[3] + products[4]
        multiple_active = products[5] + products[6]
        multiple_archived.action_archive()
        (multiple_archived + multiple_active).unlink()
        self.assertFalse(products.exists())

@tagged('post_install', '-at_install')
class TestVariantWrite(TransactionCase):

    def test_active_one2many(self):
        template = self.env['product.template'].create({'name': 'Foo', 'description': 'Foo'})
        self.assertEqual(len(template.product_variant_ids), 1)

        # check the consistency of one2many field product_variant_ids w.r.t. active variants
        variant1 = template.product_variant_ids
        variant2 = self.env['product.product'].create({'product_tmpl_id': template.id})
        self.assertEqual(template.product_variant_ids, variant1 + variant2)

        variant2.active = False
        self.assertEqual(template.product_variant_ids, variant1)

        variant2.active = True
        self.assertEqual(template.product_variant_ids, variant1 + variant2)

        variant1.active = False
        self.assertEqual(template.product_variant_ids, variant2)

    def test_write_inherited_field(self):
        product = self.env['product.product'].create({'name': 'Foo', 'sequence': 1})
        self.assertEqual(product.name, 'Foo')
        self.assertEqual(product.sequence, 1)

        self.env['product.pricelist'].create({
            'name': 'Foo',
            'item_ids': [Command.create({'product_id': product.id, 'fixed_price': 1})],
        })

        # patch template.write to modify pricelist items, which causes some
        # cache invalidation
        Template = self.registry['product.template']
        Template_write = Template.write

        def write(self, vals):
            result = Template_write(self, vals)
            items = self.env['product.pricelist.item'].search([('product_id', '=', product.id)])
            items.fixed_price = 2
            return result

        with unittest.mock.patch.object(Template, 'write', write):
            # change both 'name' and 'sequence': due to some programmed cache
            # invalidation, the second field may not be properly assigned
            product.write({'name': 'Bar', 'sequence': 2})
            self.assertEqual(product.name, 'Bar')
            self.assertEqual(product.sequence, 2)


@tagged('post_install', '-at_install')
class TestVariantsExclusion(ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.smartphone = cls.env['product.template'].create({
            'name': 'Smartphone',
        })

        cls.storage_attr = cls.env['product.attribute'].create({'name': 'Storage'})
        cls.storage_attr_value_128 = cls.env['product.attribute.value'].create({'name': '128', 'attribute_id': cls.storage_attr.id})
        cls.storage_attr_value_256 = cls.env['product.attribute.value'].create({'name': '256', 'attribute_id': cls.storage_attr.id})

        # add attributes to product
        cls.env['product.template.attribute.line'].create([{
            'product_tmpl_id': cls.smartphone.id,
            'attribute_id': cls.size_attribute.id,
            'value_ids': [(6, 0, [cls.size_attribute_s.id, cls.size_attribute_l.id])],
        }, {
            'product_tmpl_id': cls.smartphone.id,
            'attribute_id': cls.storage_attr.id,
            'value_ids': [(6, 0, [cls.storage_attr_value_128.id, cls.storage_attr_value_256.id])],
        }])

        def get_ptav(template, ptav):
            return template.valid_product_template_attribute_line_ids.filtered(
                lambda l: l.attribute_id == ptav.attribute_id
            ).product_template_value_ids.filtered(
                lambda v: v.product_attribute_value_id == ptav
            )

        cls.smartphone_s = get_ptav(cls.smartphone, cls.size_attribute_s)
        cls.smartphone_l = get_ptav(cls.smartphone, cls.size_attribute_l)
        cls.smartphone_256 = get_ptav(cls.smartphone, cls.storage_attr_value_256)
        cls.smartphone_128 = get_ptav(cls.smartphone, cls.storage_attr_value_128)

    @mute_logger('odoo.models.unlink')
    def test_variants_1_exclusion(self):
        # Create one exclusion for Smartphone S
        self.smartphone_s.write({
            'exclude_for': [Command.create({
                'product_tmpl_id': self.smartphone.id,
                'value_ids': [(6, 0, [self.smartphone_256.id])]
            })]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 3, 'With exclusion {s: [256]}, the smartphone should have 3 active different variants')

        # Delete exclusion
        self.smartphone_s.write({
            'exclude_for': [(2, self.smartphone_s.exclude_for.id, 0)]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 4, 'With no exclusion, the smartphone should have 4 active different variants')

    @mute_logger('odoo.models.unlink')
    def test_variants_2_exclusions_same_line(self):
        # Create two exclusions for Smartphone S on the same line
        self.smartphone_s.write({
            'exclude_for': [Command.create({
                'product_tmpl_id': self.smartphone.id,
                'value_ids': [(6, 0, [self.smartphone_128.id, self.smartphone_256.id])]
            })]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 2, 'With exclusion {s: [128, 256]}, the smartphone should have 2 active different variants')

        # Delete one exclusion of the line
        self.smartphone_s.write({
            'exclude_for': [(1, self.smartphone_s.exclude_for.id, {
                'product_tmpl_id': self.smartphone.id,
                'value_ids': [(6, 0, [self.smartphone_128.id])]
            })]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 3, 'With exclusion {s: [128]}, the smartphone should have 3 active different variants')

        # Delete exclusion
        self.smartphone_s.write({
            'exclude_for': [(2, self.smartphone_s.exclude_for.id, 0)]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 4, 'With no exclusion, the smartphone should have 4 active different variants')

    @mute_logger('odoo.models.unlink')
    def test_variants_2_exclusions_different_lines(self):
        # add 1 exclusion
        self.smartphone_s.write({
            'exclude_for': [Command.create({
                'product_tmpl_id': self.smartphone.id,
                'value_ids': [(6, 0, [self.smartphone_128.id])]
            })]
        })

        # add 1 exclusion on a different line
        self.smartphone_s.write({
            'exclude_for': [Command.create({
                'product_tmpl_id': self.smartphone.id,
                'value_ids': [(6, 0, [self.smartphone_256.id])]
            })]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 2, 'With exclusion {s: [128, 256]}, the smartphone should have 2 active different variants')

        # delete one exclusion line
        self.smartphone_s.write({
            'exclude_for': [(2, self.smartphone_s.exclude_for.ids[0], 0)]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 3, 'With one exclusion, the smartphone should have 3 active different variants')

    @mute_logger('odoo.models.unlink')
    def test_exclusions_crud(self):
        """ Make sure that exclusions creation, update & delete are correctly handled.

        Exclusions updates are not necessarily done from a specific template.
        """
        PTAE = self.env['product.template.attribute.exclusion']

        exclude = PTAE.create({
            'product_tmpl_id': self.smartphone.id,
            'product_template_attribute_value_id': self.smartphone_s.id,
            'value_ids': [Command.set(self.smartphone_256.ids)]
        })
        self.assertEqual(len(self.smartphone.product_variant_ids), 3)
        self.assertNotIn(
            self.smartphone_s + self.smartphone_256,
            [product.product_template_attribute_value_ids for product in self.smartphone.product_variant_ids],
        )

        exclude.value_ids = [Command.set(self.smartphone_128.ids)]
        self.assertEqual(len(self.smartphone.product_variant_ids), 3)
        self.assertNotIn(
            self.smartphone_s + self.smartphone_128,
            [product.product_template_attribute_value_ids for product in self.smartphone.product_variant_ids],
        )

        exclude.unlink()
        self.assertEqual(len(self.smartphone.product_variant_ids), 4)

    @mute_logger('odoo.models.unlink')
    def test_dynamic_variants_unarchive(self):
        """ Make sure that exclusions creation, update & delete are correctly handled.

        Exclusions updates are not necessarily done from a specific template.
        """
        product_template = self.env['product.template'].create({
            'name': 'Test dynamic',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.dynamic_attribute.id,
                    'value_ids': [Command.set(self.dynamic_attribute.value_ids.ids)],
                }),
                Command.create({
                    'attribute_id': self.dynamic_attribute.id,
                    'value_ids': [Command.set(self.dynamic_attribute.value_ids.ids)],
                })
            ]
        })
        self.assertFalse(product_template.product_variant_ids)
        first_line_ptavs = product_template.attribute_line_ids[0].product_template_value_ids
        second_line_ptavs = product_template.attribute_line_ids[1].product_template_value_ids
        for ptav1, ptav2 in zip(first_line_ptavs, second_line_ptavs, strict=True):
            product_template._create_product_variant(ptav1 + ptav2)

        self.assertEqual(len(product_template.product_variant_ids), 2)

        pav_to_remove = self.dynamic_attribute.value_ids[:1]
        variant_to_archive = product_template.product_variant_ids.filtered(
            lambda pp:
                pav_to_remove in pp.product_template_attribute_value_ids.product_attribute_value_id
        )

        # Removing one option will archive one variant
        with patch(
            'odoo.addons.product.models.product_product.ProductProduct._filter_to_unlink',
            lambda products: products.filtered(
                lambda pp: pp.product_tmpl_id.id != product_template.id
            ),
        ):
            product_template.attribute_line_ids[1].value_ids = [
                Command.unlink(self.dynamic_attribute.value_ids[:1].id)
            ]
        self.assertEqual(len(product_template.product_variant_ids), 1)
        self.assertFalse(variant_to_archive.active)

        # Putting it back should unarchive the archived variant
        product_template.attribute_line_ids[1].value_ids = [
            Command.link(self.dynamic_attribute.value_ids[:1].id)
        ]
        self.assertEqual(len(product_template.product_variant_ids), 2)
        self.assertTrue(variant_to_archive.active)
