# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestUom(TransactionCase):
    """Tests for unit of measure conversion"""

    def setUp(self):
        super(TestUom, self).setUp()
        self.product = self.env['product.product']
        self.uom = self.env['product.uom']
        self.imd = self.env['ir.model.data']

    def test_10_conversion(self):
        gram_id = self.env.ref('product.product_uom_gram')
        kg_id = self.env.ref('product.product_uom_kgm')
        tonne_id = self.env.ref('product.product_uom_ton')
        unit_id = self.env.ref('product.product_uom_unit')
        dozen_id = self.env.ref('product.product_uom_dozen')
        qty = gram_id._compute_qty(1020000, tonne_id.id)
        self.assertEquals(qty, 1.02, "Converted quantity does not correspond.")

        price = gram_id._compute_price(2, tonne_id.id)
        self.assertEquals(price, 2000000.0, "Converted price does not correspond.")

        # If the conversion factor for Dozens (1/12) is not stored with sufficient precision,
        # the conversion of 1 Dozen into Units will give e.g. 12.00000000000047 Units
        # and the Unit rounding will round that up to 13.
        # This is a partial regression test for rev. 311c77bb, which is further improved
        # by rev. fa2f7b86.
        qty = dozen_id._compute_qty(1, unit_id.id)
        self.assertEquals(qty, 12.0, "Converted quantity does not correspond.")

        # Regression test for side-effect of commit 311c77bb - converting 1234 Grams
        # into Kilograms should work even if grams are rounded to 1.
        gram_id.write({'rounding': 1})
        qty = gram_id._compute_qty(1234, kg_id.id)
        self.assertEquals(qty, 1.234, "Converted quantity does not correspond.")

    def test_20_rounding(self):
        unit_id = self.env.ref('product.product_uom_unit')
        categ_unit_id = self.env.ref('product.product_uom_categ_unit')

        score_id = self.uom.create({
            'name': 'Score',
            'factor_inv': 20,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': categ_unit_id.id
        })

        qty = unit_id._compute_qty(2, score_id.id)
        self.assertEquals(qty, 1, "Converted quantity should be rounded up.")
