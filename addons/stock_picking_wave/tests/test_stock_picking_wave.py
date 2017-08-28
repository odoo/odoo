# -*- coding: utf-8 -*-

# Author: Tejas Shahu
# Date: 08/14/2017
from odoo.addons.stock.tests.common import TestStockCommon


class TestStockPickingWave(TestStockCommon):

    # create outgoing picking and move object
    def _create_picking(self, product, product_qty=1):
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.MoveObj.create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': product_qty,
            'product_uom': product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        return picking_out

    # check product availability
    def _increase_availability(self, product, location):
        self.StockQuantObj._update_available_quantity(
            product, location, 10)
        self.assertEqual(len(self.StockQuantObj._gather(
            product, location)), 1, "Wrong quant given.")
        self.assertEqual(self.StockQuantObj._get_available_quantity(
            product, location), 10)

    def test_00_stock_batch_picking(self):
        """ Test stock batch picking  with lot."""
        # -------------------------------------
        stock_location = self.env.ref('stock.stock_location_stock')

        # Product Created A, B, C
        productA = self.ProductObj.create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot'})
        productB = self.ProductObj.create({
            'name': 'Product B',
            'type': 'product',
            'tracking': 'lot'})
        productC = self.ProductObj.create({
            'name': 'Product C',
            'type': 'product',
            'tracking': 'lot'})

        picking_1 = self._create_picking(productA, 10)
        picking_2 = self._create_picking(productB, 10)
        picking_3 = self._create_picking(productC, 10)

        # Create Batch picking for three delivery order
        batch_picking = self.env['stock.picking.wave'].create({
            'name': 'wave1',
            'picking_ids': [(6, 0, [picking_1.id, picking_2.id, picking_3.id])]
        })

        batch_picking.confirm_picking()
        self.assertEqual(set(batch_picking.picking_ids.mapped('state')), set(['confirmed']), "Wrong state on batch picking")
        # Update Inventory each product with 10 qty
        self._increase_availability(productA, stock_location)
        self._increase_availability(productB, stock_location)
        self._increase_availability(productC, stock_location)
        # Assign inventory to pickings.
        picking_1.action_assign()
        picking_2.action_assign()
        picking_3.action_assign()
        # Check status of batch picking.
        self.assertEqual(set(batch_picking.picking_ids.mapped('state')), set(['assigned']), "Wrong state of pickings")
        batch_picking.done()
        # Check status of batch picking.
        self.assertEqual(set(batch_picking.picking_ids.mapped('state')), set(['done']), "Wrong state of pickings")
