# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestMove(TransactionCase):
    def test_stock_move(self):
        ProductObj = self.env['product.product']
        MoveObj = self.env['stock.move']

        move_product = ProductObj.create({
                'name': 'move prod',
                'type': 'product'
            })

        move_test0 = MoveObj.create({
            'name': 'Move Products',
            'product_id': move_product.id,
            'product_uom_qty': 5,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })

        move_test0.action_confirm()

        product = move_product.with_context({'location': False})
        assert product.qty_available == 0, 'Expecting 0 products in stock, got %.2f!' % (product.qty_available,)
        assert product.virtual_available == -5.0, 'Expecting -5 products in virtual stock, got %.2f!' % (product.virtual_available,)

        move_test0.action_done()

        product = move_product.with_context({'location': False})
        assert product.qty_available == -5, 'Expecting -5 products in stock, got %.2f!' % (product.qty_available,)

        product = move_product.with_context({'location': self.env.ref('stock.stock_location_customers').id})
        assert product.qty_available == 5, 'Expecting 5 products in customer location, got %.2f!' % (product.qty_available,)

        move_test2 = MoveObj.create({
            'name': 'Move 15 Products',
            'product_id': move_product.id,
            'product_uom_qty': 15,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            })

        move_test2.action_confirm()
        move_test2.action_done()

        product = move_product.with_context({'location': False})
        assert product.qty_available == 10, 'Expecting 10 products in stock, got %.2f!' % (product.qty_available,)
        assert product.virtual_available == 10.0, 'Expecting 10 products in virtual stock, got %.2f!' % (product.virtual_available,)

        move_test1 = MoveObj.create({
            'name': 'Move Products',
            'product_id': move_product.id,
            'product_uom_qty': 2,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })

        move_test1.action_confirm()

        product = move_product.with_context({'location': False})
        assert product.qty_available == 10, 'Expecting 10 products in stock, got %.2f!' % (product.qty_available,)
        assert product.virtual_available == 8.0, 'Expecting 8 products in virtual stock, got %.2f!' % (product.virtual_available,)

        move_test1.action_done()

        product = move_product.with_context({'location': False})
        assert product.qty_available == 8, 'Expecting 10 products in stock, got %.2f!' % (product.qty_available,)

        product = move_product.with_context({'location': self.env.ref('stock.stock_location_customers').id})
        assert product.qty_available == 7, 'Expecting 7 products in customer location, got %.2f!' % (product.qty_available,)
