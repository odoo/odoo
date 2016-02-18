# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestInventory(TransactionCase):
    def test_stock_inventory(self):
        ProductObj = self.env['product.product']
        InvObj = self.env['stock.inventory']
        InvLineObj = self.env['stock.inventory.line']

        inventory_product = ProductObj.create({
                "name": "inventory prod",
                "type": "product"
            })

        inventory_test0 = InvObj.create({
                "name": "Test",
                "filter": "product",
                'product_id': inventory_product.id
            })

        inventory_test0.prepare_inventory()
        self.assertEqual(len(inventory_test0.line_ids), 0, "Wrong number of inventory lines.")

        inventory_testline0 = InvLineObj.create({
            "inventory_id": inventory_test0.id,
            "product_uom_id": self.env.ref('product.product_uom_unit').id,
            "product_id": inventory_product.id,
            "product_qty": 10,
            "location_id": self.env.ref('stock.stock_location_14').id,
        })

        inventory_test0.action_done()

        self.assertGreaterEqual(len(inventory_test0.move_ids), 1, "No move created for the inventory.")
        self.assertGreaterEqual(len(inventory_test0.move_ids[0].quant_ids), 1, "No quant created for this inventory")

        product = inventory_product.with_context({'location': self.env.ref('stock.stock_location_14').id})
        self.assertEqual(product.qty_available, 10, 'Expecting 10 products, got %.2f on location stock_location_14!' % (product.qty_available,))
        product = inventory_product.with_context({'location': self.env.ref('stock.stock_location_stock').id})
        self.assertEqual(product.qty_available, 10, 'Expecting 10 products, got %.2f on location stock_location_stock!' % (product.qty_available,))

        product = inventory_product.with_context({'location': self.env.ref('stock.stock_location_components').id})
        self.assertEqual(product.qty_available, 0, 'Expecting 0 products, got %.2f on location stock_location_components!' % (product.qty_available,))

        inventory_test1 = InvObj.create({
                'name': 'second test inventory',
                'filter': 'product',
                'product_id': inventory_product.id
            })

        inventory_test1.prepare_inventory()
        self.assertEqual(inventory_test1.line_ids and len(inventory_test1.line_ids), 1, "Wrong number of inventory lines.")
        self.assertEqual(inventory_test1.line_ids[0].product_qty, 10, "Wrong quantity in inventory line.")
        self.assertEqual(inventory_test1.line_ids[0].product_id.id, inventory_product.id, "Wrong product in inventory line.")

        inventory_test1.line_ids[0].write({'product_qty': 20})

        inventory_test1.action_done()

        inventory_product.invalidate_cache()
        product = inventory_product.with_context({'location': self.env.ref('stock.stock_location_14').id})
        self.assertEqual(product.qty_available, 20, 'Expecting 20 products, got %.2f on location stock_location_14!' % (product.qty_available,))
