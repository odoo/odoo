# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from odoo.exceptions import except_orm


class TestWarehouse(common.TestMrpCommon):

    def test_manufacturing_route(self):
        warehouse_1_stock_manager = self.warehouse_1.sudo(self.user_stock_manager)
        manu_rule = self.env['procurement.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        manu_route = manu_rule.route_id
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.write({
            'manufacture_to_resupply': False
        })
        self.assertFalse(self.warehouse_1.manufacture_pull_id)
        self.assertFalse(self.warehouse_1.manu_type_id.active)
        self.assertNotIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.write({
            'manufacture_to_resupply': True
        })
        manu_rule = self.env['procurement.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        self.assertTrue(self.warehouse_1.manu_type_id.active)
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())

    def test_manufacturing_scrap(self):
        """
            Testing to do a scrap of consumed material.
        """

        # Update demo products
        (self.product_4 | self.product_2).write({
            'tracking': 'lot',
        })

        # Update Bill Of Material to remove product with phantom bom.
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()

        # Create Inventory Adjustment For Stick and Stone Tools with lot.
        lot_product_4 = self.env['stock.production.lot'].create({
            'name': '0000000000001',
            'product_id': self.product_4.id,
        })
        lot_product_2 = self.env['stock.production.lot'].create({
            'name': '0000000000002',
            'product_id': self.product_2.id,
        })

        stock_inv_product_4 = self.env['stock.inventory'].create({
            'name': 'Stock Inventory for Stick',
            'filter': 'product',
            'product_id': self.product_4.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_4.id, 'product_uom_id': self.product_4.uom_id.id, 'product_qty': 8, 'prod_lot_id': lot_product_4.id, 'location_id': self.ref('stock.stock_location_14')}),
            ]})

        stock_inv_product_2 = self.env['stock.inventory'].create({
            'name': 'Stock Inventory for Stone Tools',
            'filter': 'product',
            'product_id': self.product_2.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_uom_id': self.product_2.uom_id.id, 'product_qty': 12, 'prod_lot_id': lot_product_2.id, 'location_id': self.ref('stock.stock_location_14')})
            ]})
        (stock_inv_product_4 | stock_inv_product_2).prepare_inventory()
        (stock_inv_product_4 | stock_inv_product_2).action_done()

        #Create Manufacturing order.
        production_3 = self.env['mrp.production'].create({
            'name': 'MO-Test003',
            'product_id': self.product_6.id,
            'product_qty': 12,
            'bom_id': self.bom_3.id,
            'product_uom_id': self.product_6.uom_id.id,
        })
        production_3.action_assign()

        # Check Manufacturing order's availability.
        self.assertEqual(production_3.availability, 'assigned', "Production order's availability should be Available.")

        location_id = production_3.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) and production_3.location_src_id.id or production_3.location_dest_id.id,

        # Scrap Product Wood without lot to check assert raise ?.
        with self.assertRaises(except_orm):
            self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'production_id': production_3.id})

        # Scrap Product Wood with lot.
        self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'lot_id': lot_product_2.id, 'production_id': production_3.id})

        #Check scrap move is created for this production order.
        #TODO: should check with scrap objects link in between
        
#        scrap_move = production_3.move_raw_ids.filtered(lambda x: x.product_id == self.product_2 and x.scrapped)
#        self.assertTrue(scrap_move, "There are no any scrap move created for production order.")
