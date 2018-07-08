# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPacking(TransactionCase):

    def setUp(self):
        super(TestPacking, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.stock_location.id)], limit=1)
        self.warehouse.write({'delivery_steps': 'pick_pack_ship'})
        self.pack_location = self.warehouse.wh_pack_stock_loc_id
        self.ship_location = self.warehouse.wh_output_stock_loc_id
        self.customer_location = self.env.ref('stock.stock_location_customers')

        self.productA = self.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        self.productB = self.env['product.product'].create({'name': 'Product B', 'type': 'product'})

    def test_put_in_pack(self):
        """ In a pick pack ship scenario, create two packs in pick and check that
        they are correctly recognised and handled by the pack and ship picking.
        Along this test, we'll use action_toggle_processed to process a pack
        from the entire_package_ids one2many and we'll directly fill the move
        lines, the latter is the behavior when the user did not enable the display
        of entire packs on the picking type.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 20.0)
        ship_move_a = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.ship_location.id,
            'location_dest_id': self.customer_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })
        ship_move_b = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productB.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productB.uom_id.id,
            'location_id': self.ship_location.id,
            'location_dest_id': self.customer_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })
        ship_move_a._assign_picking()
        ship_move_b._assign_picking()
        ship_move_a._action_confirm()
        ship_move_b._action_confirm()
        pack_move_a = ship_move_a.move_orig_ids[0]
        pick_move_a = pack_move_a.move_orig_ids[0]

        pick_picking = pick_move_a.picking_id
        packing_picking = pack_move_a.picking_id
        shipping_picking = ship_move_a.picking_id

        pick_picking.action_assign()
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA).qty_done = 1.0
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productB).qty_done = 2.0

        first_pack = pick_picking.put_in_pack()
        self.assertEquals(len(pick_picking.package_level_ids), 1, 'Put some products in pack should create a package_level')
        self.assertEquals(pick_picking.package_level_ids[0].state, 'new', 'A new pack should be in state "new"')
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA and ml.qty_done == 0.0).qty_done = 4.0
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productB and ml.qty_done == 0.0).qty_done = 3.0
        second_pack = pick_picking.put_in_pack()
        pick_picking.button_validate()
        self.assertEqual(len(first_pack.quant_ids), 2)
        self.assertEqual(len(second_pack.quant_ids), 2)
        packing_picking.action_assign()
        self.assertEqual(len(packing_picking.package_level_ids), 2, 'Two package levels must be created after assigning picking')
        packing_picking.package_level_ids.write({'is_done': True})
        packing_picking.action_done()


    def test_pick_a_pack_confirm(self):
        pack = self.env['stock.quant.package'].create({'name': 'The pack to pick'})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, package_id=pack)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        self.assertEquals(package_level.state, 'draft',
                          'The package_level should be in draft as it has no moves, move lines and is not confirmed')
        picking.action_confirm()
        self.assertEqual(len(picking.move_lines), 1,
                         'One move should be created when the package_level has been confirmed')
        self.assertEquals(len(package_level.move_ids), 1,
                          'The move should be in the package level')
        self.assertEquals(package_level.state, 'confirmed',
                          'The package level must be state confirmed when picking is confirmed')
        picking.action_assign()
        self.assertEqual(len(picking.move_lines), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_lines.move_line_ids), 1,
                         'The move  should have one move line which is the reservation')
        self.assertEquals(picking.move_line_ids.package_level_id.id, package_level.id,
                          'The move line created should be linked to the package level')
        self.assertEquals(picking.move_line_ids.package_id.id, pack.id,
                          'The move line must have been reserved on the package of the package_level')
        self.assertEquals(picking.move_line_ids.result_package_id.id, pack.id,
                          'The move line must have the same package as result package')
        self.assertEquals(package_level.state, 'assigned', 'The package level must be in state assigned')
        package_level.write({'is_done': True})
        self.assertEquals(len(package_level.move_line_ids), 1,
                          'The package level should still keep one move line after have been set to "done"')
        self.assertEquals(package_level.move_line_ids[0].qty_done, 20.0,
                          'All quantity in package must be procesed in move line')
        picking.button_validate()
        self.assertEqual(len(picking.move_lines), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_lines.move_line_ids), 1,
                         'The move  should have one move line which is the reservation')
        self.assertEquals(package_level.state, 'done', 'The package level must be in state done')
        self.assertEquals(pack.location_id.id, picking.location_dest_id.id,
                          'The quant package must be in the destination location')
        self.assertEquals(pack.quant_ids[0].location_id.id, picking.location_dest_id.id,
                          'The quant must be in the destination location')
