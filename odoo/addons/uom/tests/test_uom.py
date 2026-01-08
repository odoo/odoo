# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo.addons.uom.tests.common import UomCommon


class TestUom(UomCommon):

    def test_10_conversion(self):
        qty = self.uom_gram._compute_quantity(1020000, self.uom_ton)
        self.assertEqual(qty, 1.02, "Converted quantity does not correspond.")

        price = self.uom_gram._compute_price(2, self.uom_ton)
        self.assertEqual(price, 2000000.0, "Converted price does not correspond.")

        # If the conversion factor for Dozens (1/12) is not stored with sufficient precision,
        # the conversion of 1 Dozen into Units will give e.g. 12.00000000000047 Units
        # and the Unit rounding will round that up to 13.
        # This is a partial regression test for rev. 311c77bb, which is further improved
        # by rev. fa2f7b86.
        qty = self.uom_dozen._compute_quantity(1, self.uom_unit)
        self.assertEqual(qty, 12.0, "Converted quantity does not correspond.")

        # Regression test for side-effect of commit 311c77bb - converting 1234 Grams
        # into Kilograms should work even if grams are rounded to 1.
        self.uom_gram.write({'rounding': 1})
        qty = self.uom_gram._compute_quantity(1234, self.uom_kgm)
        self.assertEqual(qty, 1.24, "Converted quantity does not correspond.")

    def test_20_rounding(self):
        product_uom = self.env['uom.uom'].create({
            'name': 'Score',
            'factor_inv': 20,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': self.env.ref('uom.product_uom_categ_unit').id
        })

        qty = self.uom_unit._compute_quantity(2, product_uom)
        self.assertEqual(qty, 1, "Converted quantity should be rounded up.")

    def test_30_reference_uniqueness(self):
        """ Check the uniqueness of the reference UoM in a category """
        time_category = self.env.ref('uom.product_uom_categ_unit')

        with self.assertRaises(ValidationError):
            self.env['uom.uom'].create({
                'name': 'Second Time Reference',
                'factor_inv': 1,
                'uom_type': 'reference',
                'rounding': 1.0,
                'category_id': time_category.id,
                'active': False,
            })

    def test_40_custom_uom(self):
        """ A custom UoM is an UoM in a category without measurement type. It should behave like a normal UoM """
        category = self.env['uom.category'].create({
            'name': 'Custom UoM category',
        })

        # at first we can not create a non reference in custom category
        with self.assertRaises(ValidationError):
            self.env['uom.uom'].create({
                'name': 'Bigger UoM of my category',
                'factor_inv': 42,
                'uom_type': 'bigger',
                'rounding': 0.5,
                'category_id': category.id
            })

        # create the reference
        self.env['uom.uom'].create({
            'name': 'Reference UoM of my category',
            'factor_inv': 1,
            'uom_type': 'reference',
            'rounding': 1.0,
            'category_id': category.id
        })

        # we can create another UoM now
        self.env['uom.uom'].create({
            'name': 'Bigger UoM of my category',
            'factor_inv': 42,
            'uom_type': 'bigger',
            'rounding': 0.5,
            'category_id': category.id
        })

        # we can not create a second reference in custom category
        with self.assertRaises(ValidationError):
            self.env['uom.uom'].create({
                'name': 'Second Time Reference',
                'factor_inv': 1,
                'uom_type': 'reference',
                'rounding': 1.0,
                'category_id': category.id
            })

    def test_50_check_ratio(self):
        with self.assertRaises(ValidationError):
            self.env['uom.uom'].create({
                'name': 'Custom UoM',
                'uom_type': 'bigger',
                'ratio': 0,
                'category_id': self.env.ref('uom.product_uom_categ_unit').id
            })
