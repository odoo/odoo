# -*- coding: utf-8 -*-
# © 2015 Numérigraphe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.addons.stock.tests.common import TestStockCommon


class TestPackopsQuantLocation(TestStockCommon):
    def setUp(self):
        super(TestPackopsQuantLocation, self).setUp()

        # Get the children of the main location
        self.child_locations = self.env['stock.location'].search(
            [('location_id', '=', self.stock_location),
             ('usage', '=', 'internal')])

        # Clean up the product from the inventory
        self.productA.type = 'product'
        inventory = self.InvObj.create({'name': 'Reset product for test',
                                        'filter': 'product',
                                        'product_id': self.productA.id})
        inventory.prepare_inventory()
        inventory.reset_real_qty()
        inventory.action_done()
        # Put the product in 2 locations
        inventory = self.InvObj.create({'name': 'Put product for test',
                                        'filter': 'none'})
        inventory.prepare_inventory()
        self.InvLineObj.create(
            {'inventory_id': inventory.id,
             'product_id': self.productA.id,
             'product_uom_id': self.productA.uom_id.id,
             'product_qty': 7.0,
             'location_id': self.child_locations[0].id})
        self.InvLineObj.create(
            {'inventory_id': inventory.id,
             'product_id': self.productA.id,
             'product_uom_id': self.productA.uom_id.id,
             'product_qty': 3.0,
             'location_id': self.child_locations[1].id})
        inventory.action_done()

        self.assertEquals(
            self.env['stock.quant'].search(
                [('product_id', '=', self.productA.id)], count=True), 2,
            'There should be 2 quants for the product')

    def test_packops_quant_location(self):
        """Test that operations are assigned quants in the right location

        There is a corner case where a product may be available in 2 locations
        and we use pack operations to move it.
        In such cases we want the reserved quants for each location to be
        assigned to the corresponding pack operation.
        Otherwise, one of the reserved quants will wrongly be split because
        it won't match the quantity of the pack operation.
        """
        # Create a delivery from the main stock location
        picking = self.PickingObj.create(
            {'picking_type_id': self.picking_type_out})
        move = self.MoveObj.create(
            {'name': 'Move with operations',
             'product_id': self.productA.id,
             'product_uom_qty': 10.0,
             'product_uom': self.productA.uom_id.id,
             'picking_id': picking.id,
             'location_id': self.stock_location,
             'location_dest_id': self.customer_location})
        picking.action_confirm()
        picking.action_assign()
        self.assertEquals(len(move.reserved_quant_ids), 2,
                          "The wrong quants were reserved: %s" % (
                                ["%s: %f" %
                                 (q.location_id.name, q.qty)
                                 for q in move.reserved_quant_ids]))
        picking.do_prepare_partial()
        self.assertEqual(len(picking.pack_operation_ids), 2,
                         "Two operations should be generated")
        for p in picking.pack_operation_ids:
            p.qty_done = p.product_qty
        self.PickingObj.action_done_from_ui(picking.id)
        picking.refresh()
        self.assertEquals(len(move.quant_ids), 2,
                          "The wrong quants were moved: %s" % (
                                ["%d:%s/%f" %
                                 (q.id, q.location_id.name, q.qty)
                                 for q in move.quant_ids]))
        self.assertItemsEqual(
            [q.qty for q in move.quant_ids], [7.0, 3.0],
            "The moved quants have the wrong quantities")
