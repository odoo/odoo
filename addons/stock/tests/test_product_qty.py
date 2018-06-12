# -*- coding: utf-8 -*-
# © 2016 Cyril Gaudin (Camptocamp)
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestProductQty(common.TransactionCase):

    def test_quant_location_context(self):

        test_location = self.env['stock.location'].create({
            'name': 'Unittest sub location',
            'location_id': self.ref('stock.stock_location_locations'),
            'usage': 'internal',
        })

        # Create a test product
        test_product = self.env['product.product'].create({
            'name': 'Unittest product',
        })

        # Put 5 qty of test product in created location
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory for test product',
            'location_id': test_location.id,
            'filter': 'partial'
        })
        inventory.prepare_inventory()

        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': test_product.id,
            'location_id': test_location.id,
            'product_qty': 5,
        })
        inventory.action_done()

        # Check product qty in 2 locations
        product_qty = test_product.with_context(
            location=[
                # First location may already exists (parent_left is computed)
                # Second was just created (parent_left not computed in test)
                self.ref('stock.stock_location_components'), test_location.id
            ]
        ).qty_available
        self.assertEqual(5, product_qty)
