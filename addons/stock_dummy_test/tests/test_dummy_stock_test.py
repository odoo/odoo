# coding: utf-8
from openerp.tests.common import TransactionCase


class TestDummyStockTest(TransactionCase):

    def setUp(self):
        super(TestDummyStockTest, self).setUp()
        self.move = self.env['stock.move']
        self.stock = self.env.ref('stock.stock_location_stock')
        self.customer = self.env.ref('stock.stock_location_customers')

    def create_move(self, src_loc, dest_loc, qty):
        prod = self.env.ref('product.product_product_18')
        values = self.move.onchange_product_id(
            prod_id=prod.id, loc_id=src_loc, loc_dest_id=dest_loc)['value']
        values.update({'product_id': prod.id})
        return self.move.create(values)

    def test_01_normal_moves(self):
        self.create_move(self.stock.id, self.customer.id, 4)
