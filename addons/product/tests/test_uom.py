from openerp.tests.common import TransactionCase
from openerp.tools import float_compare

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
        tonne_id = self.imd.get_object_reference(cr, uid, 'product', 'product_uom_ton')[1]

        qty = self.uom._compute_qty(cr, uid, gram_id, 1020000, tonne_id)
        self.assertEqual(float_compare(qty, 1.02, precision_digits=2), 0, "Converted quantity does not correspond.")

        price = self.uom._compute_price(cr, uid, gram_id, 2, tonne_id)
        self.assertEqual(float_compare(price, 2000000.0, precision_digits=0), 0, "Converted price does not correspond.")

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
        self.assertEqual(float_compare(qty, 1.0, precision_digits=0), 0, "Converted quantity should be rounded up.")
