from openerp.tests.common import TransactionCase

class TestUom(TransactionCase):
    """Tests for unit of measure conversion"""

    def setUp(self):
        super(TestUom, self).setUp()
        self.product = self.registry('product.product')
        self.uom = self.registry('product.uom')
        self.imd = self.registry('ir.model.data')

    def test_10_conversion(self):
        cr, uid = self.cr, self.uid
        gram_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_gram')[1]
        kg_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_kgm')[1]
        tonne_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_ton')[1]
        unit_id = self.imd.get_object_reference(cr, uid, 'product','product_uom_unit')[1]
        dozen_id = self.imd.get_object_reference(cr, uid, 'product','product_uom_dozen')[1]

        qty = self.uom._compute_qty(cr, uid, gram_id, 1020000, tonne_id)
        self.assertEquals(qty, 1.02, "Converted quantity does not correspond.")

        price = self.uom._compute_price(cr, uid, gram_id, 2, tonne_id)
        self.assertEquals(price, 2000000.0, "Converted price does not correspond.")

        # If the conversion factor for Dozens (1/12) is not stored with sufficient precision,
        # the conversion of 1 Dozen into Units will give e.g. 12.00000000000047 Units
        # and the Unit rounding will round that up to 13.
        # This is a partial regression test for rev. 311c77bb, which is further improved
        # by rev. fa2f7b86.
        qty = self.uom._compute_qty(cr, uid, dozen_id, 1, unit_id)
        self.assertEquals(qty, 12.0, "Converted quantity does not correspond.")

        # Regression test for side-effect of commit 311c77bb - converting 1234 Grams
        # into Kilograms should work even if grams are rounded to 1.
        self.uom.write(cr, uid, gram_id, {'rounding': 1})
        qty = self.uom._compute_qty(cr, uid, gram_id, 1234, kg_id)
        self.assertEquals(qty, 1.234, "Converted quantity does not correspond.")

    def test_20_rounding(self):
        cr, uid = self.cr, self.uid
        unit_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_unit')[1]
        categ_unit_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_categ_unit')[1]
        
        score_id = self.uom.create(cr, uid, {
            'name': 'Score',
            'factor_inv': 20,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': categ_unit_id
        })

        qty = self.uom._compute_qty(cr, uid, unit_id, 2, score_id)
        self.assertEquals(qty, 1, "Converted quantity should be rounded up.")
