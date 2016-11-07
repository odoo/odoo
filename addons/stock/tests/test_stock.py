from openerp.tests import common
from openerp.tools.float_utils import float_compare


class TestStock(common.TransactionCase):

    def setUp(self):
        super(TestStock, self).setUp()
        cr, uid = self.cr, self.uid
        self.stock_location = self.registry('stock.location')
        self.stock_change_product_qty = self.registry(
            'stock.change.product.qty')
        self.uom = self.registry('product.uom')
        self.stock_location_shelf1 = self.ref(
            'stock.stock_location_components')
        self.stock_location_shelf2 = self.ref(
            'stock.stock_location_14')
        self.unit_id = self.ref('product.product_uom_unit')
        categ_unit_id = self.ref('product.product_uom_categ_unit')
        self.six_unit_id = self.uom.create(cr, uid, {
            'name': 'Score',
            'factor_inv': 6,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': categ_unit_id
        })
        self.product_id = self.ref('product.product_product_7')

        # put 721 qty in chelf1
        # and 7 qty in shelf2
        ctx = {'active_id':  self.product_id}
        wiz_id_1 = self.stock_change_product_qty.create(
            cr, uid, {'product_id': self.product_id,
                      'new_quantity': 721,
                      'location_id': self.stock_location_shelf1},
            context=ctx)
        wiz_id_2 = self.stock_change_product_qty.create(
            cr, uid, {'product_id': self.product_id,
                      'new_quantity': 7,
                      'location_id': self.stock_location_shelf2},
            context=ctx)
        self.stock_change_product_qty.change_product_qty(
            cr, uid, [wiz_id_1, wiz_id_2], context=ctx)

    def test_product_reserve_01(self):
        """Test product_reserve in unit_id
        """
        cr, uid = self.cr, self.uid
        res = self.stock_location._product_reserve(
            cr, uid, [self.stock_location_shelf1], self.product_id, 722)
        self.assertFalse(res, 'Only 721 unit available in shelf 1 not 722')
        res = self.stock_location._product_reserve(
            cr, uid, [self.stock_location_shelf1, self.stock_location_shelf2],
            self.product_id, 722)
        self.assertEquals(len(res), 2)
        total = 0.0
        for amount, _ in res:
            total += amount
        res_cmp = float_compare(total, 722, precision_digits=1.0)
        self.assertEqual(0, res_cmp)

    def test_product_reserve_06(self):
        """Test product_reserve in six_unit_id
        """
        cr, uid = self.cr, self.uid
        ctx = {'uom': self.six_unit_id}
        res = self.stock_location._product_reserve(
            cr, uid, [self.stock_location_shelf1], self.product_id, 121,
            context=ctx)
        self.assertFalse(res, 'Only 120 six_unit available in shelf 1 not 121')
        res = self.stock_location._product_reserve(
            cr, uid, [self.stock_location_shelf1, self.stock_location_shelf2],
            self.product_id, 121, context=ctx)
        self.assertEquals(len(res), 2)
        total = 0.0
        for amount, _ in res:
            total += amount
        res_cmp = float_compare(total, 121, precision_digits=1.0)
        self.assertEqual(0, res_cmp)
