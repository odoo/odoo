# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import Command


class TestPackingCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestPackingCommon, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.warehouse = cls.env['stock.warehouse'].search([('lot_stock_id', '=', cls.stock_location.id)], limit=1)
        cls.warehouse.write({'delivery_steps': 'pick_pack_ship'})
        cls.warehouse.int_type_id.reservation_method = 'manual'
        cls.pack_location = cls.warehouse.wh_pack_stock_loc_id
        cls.ship_location = cls.warehouse.wh_output_stock_loc_id
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.picking_type_in = cls.env.ref('stock.picking_type_in')

        cls.productA = cls.env['product.product'].create({'name': 'Product A', 'is_storable': True})
        cls.productB = cls.env['product.product'].create({'name': 'Product B', 'is_storable': True})
        cls.shelf1 = cls.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': cls.stock_location.id,
        })


class TestPacking(TestPackingCommon):

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
        pick_move_a = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        pick_move_b = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productB.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productB.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        pick_move_a._assign_picking()
        pick_move_b._assign_picking()
        picking = pick_move_a.picking_id
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        self.warehouse.pick_type_id.show_entire_packs = True
        self.warehouse.pack_type_id.show_entire_packs = True
        self.warehouse.out_type_id.show_entire_packs = True

        pack_move_a = pick_move_a.move_dest_ids[0]
        pack_picking = pack_move_a.picking_id
        pack_picking.action_assign()
        self.assertEqual(len(pack_picking.move_ids_without_package), 2)
        pack_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA).quantity = 1.0
        pack_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productB).quantity = 2.0
        pack_picking.move_ids_without_package.picked = True

        first_pack = pack_picking.action_put_in_pack()
        self.assertEqual(len(pack_picking.package_level_ids), 1, 'Put some products in pack should create a package_level')
        self.assertEqual(pack_picking.package_level_ids[0].state, 'new', 'A new pack should be in state "new"')
        ml = pack_picking.move_line_ids[0].copy()
        ml.write({
            'quantity': 4.0,
            'result_package_id': False,
        })
        ml = pack_picking.move_line_ids[1].copy()
        ml.write({
            'quantity': 3.0,
            'result_package_id': False,
        })
        second_pack = pack_picking.action_put_in_pack()
        self.assertEqual(len(pack_picking.move_ids_without_package), 2)
        pack_picking.move_ids.picked = True
        pack_picking.button_validate()
        self.assertEqual(len(pack_picking.move_ids_without_package), 2)
        self.assertEqual(len(first_pack.quant_ids), 2)
        self.assertEqual(len(second_pack.quant_ids), 2)
        ship_picking = pack_move_a.move_dest_ids[0].picking_id
        ship_picking.action_assign()
        self.assertEqual(len(ship_picking.package_level_ids), 2, 'Two package levels must be created after assigning picking')
        ship_picking.package_level_ids.write({'is_done': True})
        ship_picking._action_done()

    def test_pick_a_pack_confirm(self):
        pack = self.env['stock.quant.package'].create({'name': 'The pack to pick'})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, package_id=pack)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        picking.picking_type_id.show_entire_packs = True
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'company_id': picking.company_id.id,
        })
        self.assertEqual(package_level.state, 'draft',
                          'The package_level should be in draft as it has no moves, move lines and is not confirmed')
        picking.action_confirm()
        self.assertEqual(len(picking.move_ids_without_package), 0)
        self.assertEqual(len(picking.move_ids), 1,
                         'One move should be created when the package_level has been confirmed')
        self.assertEqual(len(package_level.move_ids), 1,
                          'The move should be in the package level')
        self.assertEqual(package_level.state, 'confirmed',
                          'The package level must be state confirmed when picking is confirmed')
        picking.action_assign()
        self.assertEqual(len(picking.move_ids), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_ids.move_line_ids), 1,
                         'The move  should have one move line which is the reservation')
        self.assertEqual(picking.move_line_ids.package_level_id.id, package_level.id,
                          'The move line created should be linked to the package level')
        self.assertEqual(picking.move_line_ids.package_id.id, pack.id,
                          'The move line must have been reserved on the package of the package_level')
        self.assertEqual(picking.move_line_ids.result_package_id.id, pack.id,
                          'The move line must have the same package as result package')
        self.assertEqual(package_level.state, 'assigned', 'The package level must be in state assigned')
        package_level.write({'is_done': True})
        self.assertEqual(len(package_level.move_line_ids), 1,
                          'The package level should still keep one move line after have been set to "done"')
        self.assertEqual(package_level.move_line_ids[0].quantity, 20.0,
                          'All quantity in package must be procesed in move line')
        picking.button_validate()
        self.assertEqual(len(picking.move_ids), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_ids.move_line_ids), 1,
                         'The move  should have one move line which is the reservation')
        self.assertEqual(package_level.state, 'done', 'The package level must be in state done')
        self.assertEqual(pack.location_id.id, picking.location_dest_id.id,
                          'The quant package must be in the destination location')
        self.assertEqual(pack.quant_ids[0].location_id.id, picking.location_dest_id.id,
                          'The quant must be in the destination location')

    def test_pick_a_pack_cancel(self):
        """Cancel a reserved operation with a not-done package level (is_done=False)."""
        pack = self.env['stock.quant.package'].create({'name': 'The pack to pick'})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, package_id=pack)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        picking.picking_type_id.show_entire_packs = True
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'location_dest_id': self.stock_location.id,
            'company_id': picking.company_id.id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(package_level.state, 'assigned')
        self.assertTrue(package_level.move_line_ids)
        picking.action_cancel()
        self.assertEqual(package_level.state, 'cancel')
        self.assertFalse(package_level.move_line_ids)

    def test_pick_a_pack_cancel_is_done(self):
        """Cancel a reserved operation with a package level that is done (is_done=True)."""
        pack = self.env['stock.quant.package'].create({'name': 'The pack to pick'})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, package_id=pack)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        picking.picking_type_id.show_entire_packs = True
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'location_dest_id': self.stock_location.id,
            'company_id': picking.company_id.id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(package_level.state, 'assigned')
        self.assertTrue(package_level.move_line_ids)
        # By setting the package_level as 'done', all related lines will be kept
        # when cancelling the transfer
        package_level.is_done = True
        picking.action_cancel()
        self.assertEqual(picking.state, 'cancel')
        self.assertEqual(package_level.state, 'cancel')

    def test_multi_pack_reservation(self):
        """ When we move entire packages, it is possible to have a multiple times
            the same package in package level list, we make sure that only one is reserved,
            and that the location_id of the package is the one where the package is once it
            is reserved.
        """
        pack = self.env['stock.quant.package'].create({'name': 'The pack to pick'})
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.productA, shelf1_location, 20.0, package_id=pack)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'company_id': picking.company_id.id,
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'company_id': picking.company_id.id,
        })
        picking.action_confirm()
        self.assertEqual(picking.package_level_ids.location_id.ids, [shelf1_location.id],
                         'The package levels should still in the same location after confirmation.')
        picking.action_assign()
        package_level_reserved = picking.package_level_ids.filtered(lambda pl: pl.state == 'assigned')
        self.assertEqual(package_level_reserved.location_id.id, shelf1_location.id, 'The reserved package level must be reserved in shelf1')
        picking.do_unreserve()
        self.assertEqual(picking.package_level_ids.location_id.ids, [shelf1_location.id],
                         'The package levels should have back the original location.')
        picking.package_level_ids.write({'is_done': True})
        picking.action_assign()
        package_level_reserved = picking.package_level_ids.filtered(lambda pl: pl.state == 'assigned')
        self.assertEqual(package_level_reserved.location_id.id, shelf1_location.id, 'The reserved package level must be reserved in shelf1')
        self.assertEqual(picking.package_level_ids.mapped('is_done'), [True, True], 'Both package should still done')

    def test_put_in_pack_to_different_location(self):
        """ Hitting 'Put in pack' button while some move lines go to different
            location should trigger a wizard. This wizard applies the same destination
            location to all the move lines
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        ship_move_a = self.env['stock.move'].create({
            'name': 'move 1',
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.customer_location.id,
            'location_dest_id': shelf1_location.id,
            'picking_id': picking.id,
            'state': 'draft',
        })
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.filtered(lambda ml: ml.product_id == self.productA).picked = True
        picking.action_put_in_pack()
        pack1 = self.env['stock.quant.package'].search([], order='id')[-1]
        picking.write({
            'move_line_ids': [(0, 0, {
                'product_id': self.productB.id,
                'quantity': 7.0,
                'product_uom_id': self.productB.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': shelf2_location.id,
                'picking_id': picking.id,
                'state': 'confirmed',
            })]
        })
        picking.write({
            'move_line_ids': [(0, 0, {
                'product_id': self.productA.id,
                'quantity': 5.0,
                'product_uom_id': self.productA.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': shelf1_location.id,
                'picking_id': picking.id,
                'state': 'confirmed',
            })]
        })
        picking.move_ids.picked = True
        wizard_values = picking.action_put_in_pack()
        wizard = self.env[(wizard_values.get('res_model'))].browse(wizard_values.get('res_id'))
        wizard.location_dest_id = shelf2_location.id
        wizard.action_done()
        picking._action_done()
        pack2 = self.env['stock.quant.package'].search([], order='id')[-1]
        self.assertEqual(pack2.location_id.id, shelf2_location.id, 'The package must be stored  in shelf2')
        self.assertEqual(pack1.location_id.id, shelf1_location.id, 'The package must be stored  in shelf1')
        qp1 = pack2.quant_ids[0]
        qp2 = pack2.quant_ids[1]
        self.assertEqual(qp1.quantity + qp2.quantity, 12, 'The quant has not the good quantity')

    def test_move_picking_with_package(self):
        """
        355.4 rounded with 0.01 precision is 355.4.
        check that nonetheless, moving a picking is accepted
        """
        self.assertEqual(self.productA.uom_id.rounding, 0.01)
        location_dict = {
            'location_id': self.stock_location.id,
        }
        quant = self.env['stock.quant'].create({
            **location_dict,
            **{'product_id': self.productA.id, 'quantity': 355.4},  # important number
        })
        package = self.env['stock.quant.package'].create({
            **location_dict, **{'quant_ids': [(6, 0, [quant.id])]},
        })
        location_dict.update({
            'state': 'draft',
            'location_dest_id': self.ship_location.id,
        })
        move = self.env['stock.move'].create({
            **location_dict,
            **{
                'name': "XXX",
                'product_id': self.productA.id,
                'product_uom': self.productA.uom_id.id,
                'product_uom_qty': 355.40000000000003,  # other number
            }})
        picking = self.env['stock.picking'].create({
            **location_dict,
            **{
                'picking_type_id': self.warehouse.in_type_id.id,
                    'move_ids': [(6, 0, [move.id])],
        }})

        picking.action_confirm()
        picking.action_assign()
        move.picked = True
        picking._action_done()
        # if we managed to get there, there was not any exception
        # complaining that 355.4 is not 355.40000000000003. Good job!

    def test_move_picking_with_package_2(self):
        """ Generate two move lines going to different location in the same
        package.
        """
        shelf1 = self.env['stock.location'].create({
            'location_id': self.stock_location.id,
            'name': 'Shelf 1',
        })
        shelf2 = self.env['stock.location'].create({
            'location_id': self.stock_location.id,
            'name': 'Shelf 2',
        })
        package = self.env['stock.quant.package'].create({})

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        self.env['stock.move.line'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': shelf1.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'quantity': 5.0,
            'picking_id': picking.id,
            'result_package_id': package.id,
        })
        self.env['stock.move.line'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': shelf2.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'quantity': 5.0,
            'picking_id': picking.id,
            'result_package_id': package.id,
        })
        picking.action_confirm()
        picking.move_ids.picked = True
        with self.assertRaises(UserError):
            picking._action_done()

    def test_pack_delivery_three_step_propagate_package_consumable(self):
        """ Checks all works right in the following case:
          * For a three-step delivery
          * Put products in a package then validate the receipt.
          * The automatically generated internal transfer should have package set by default.
        """
        prod = self.env['product.product'].create({'name': 'bad dragon', 'type': 'consu'})
        pick_move = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': prod.id,
            'product_uom_qty': 5.0,
            'product_uom': prod.uom_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.wh_pack_stock_loc_id.id,
            'warehouse_id':  self.warehouse.id,
            'picking_type_id':  self.warehouse.pick_type_id.id,
            'state': 'draft',
        })

        pick_move._assign_picking()
        picking = pick_move.picking_id
        picking.action_confirm()
        picking.action_put_in_pack()

        self.assertTrue(picking.move_line_ids.result_package_id)
        picking.button_validate()
        self.assertEqual(pick_move.move_dest_ids.move_line_ids.result_package_id, picking.move_line_ids.result_package_id)

    def test_pack_in_receipt_two_step_single_putway(self):
        """ Checks all works right in the following specific corner case:

          * For a two-step receipt, receives two products using the same putaway
          * Puts these products in a package then valid the receipt.
          * Cancels the automatically generated internal transfer then create a new one.
          * In this internal transfer, adds the package then valid it.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_step_rule = self.env.ref('stock.group_adv_location')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(3, grp_multi_step_rule.id)]})
        self.env.user.write({'groups_id': [(3, grp_pack.id)]})
        self.warehouse.reception_steps = 'two_steps'
        # Settings of receipt.
        self.warehouse.in_type_id.show_entire_packs = True
        # Settings of internal transfer.
        self.warehouse.store_type_id.show_entire_packs = True

        # Creates two new locations for putaway.
        location_form = Form(self.env['stock.location'])
        location_form.name = 'Shelf A'
        location_form.location_id = self.stock_location
        loc_shelf_A = location_form.save()

        # Creates a new putaway rule for productA and productB.
        putaway_A = self.env['stock.putaway.rule'].create({
            'product_id': self.productA.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': loc_shelf_A.id,
        })
        putaway_B = self.env['stock.putaway.rule'].create({
            'product_id': self.productB.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': loc_shelf_A.id,
        })
        self.stock_location.putaway_rule_ids = [(4, putaway_A.id, 0), (4, putaway_B.id, 0)]

        # Create a new receipt with the two products.
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.warehouse.in_type_id
        # Add 2 lines
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.product_uom_qty = 1
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.product_uom_qty = 1
        receipt = receipt_form.save()
        receipt.action_confirm()

        # Adds quantities then packs them and valids the receipt.
        move_form = Form(receipt.move_ids_without_package[0], view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as move_line:
            move_line.quantity = 1
        move_form = Form(receipt.move_ids_without_package[1], view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as move_line:
            move_line.quantity = 1
        move_form.save()
        receipt = receipt_form.save()
        receipt.move_ids.picked = True
        receipt.action_put_in_pack()
        receipt.button_validate()

        receipt_package = receipt.package_level_ids[0]
        self.assertEqual(receipt_package.location_dest_id.id, receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[0].location_dest_id.id,
            receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[1].location_dest_id.id,
            receipt.location_dest_id.id)

        # Checks an internal transfer was created following the validation of the receipt.
        internal_transfer = self.env['stock.picking'].search([
            ('picking_type_id', '=', self.warehouse.store_type_id.id)
        ], order='id desc', limit=1)
        self.assertEqual(internal_transfer.origin, receipt.name)
        self.assertEqual(
            len(internal_transfer.package_level_ids), 1)
        internal_package = internal_transfer.package_level_ids[0]
        self.assertNotEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        self.assertEqual(
            internal_package.location_dest_id.id,
            putaway_A.location_out_id.id,
            "The package destination location must be the one from the putaway.")
        self.assertEqual(
            internal_package.move_line_ids[0].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the putaway.")
        self.assertEqual(
            internal_package.move_line_ids[1].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the putaway.")

        # Cancels the internal transfer and creates a new one.
        internal_transfer.action_cancel()
        picking = self.env['stock.picking'].create({
            'state': 'draft',
            'picking_type_id':  self.warehouse.store_type_id.id,
            })
        internal_form = Form(picking)
        # The test specifically removes the ability to see the location fields
        # grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        # self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        # Hence, `internal_form.location_id` shouldn't be changed
        with internal_form.package_level_ids.new() as pack_line:
            pack_line.package_id = receipt_package.package_id
        internal_transfer = internal_form.save()

        # Checks the package fields have been correctly set.
        internal_package = internal_transfer.package_level_ids[0]
        self.assertEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        internal_transfer.action_assign()
        self.assertNotEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        self.assertEqual(
            internal_package.location_dest_id.id,
            putaway_A.location_out_id.id,
            "The package destination location must be the one from the putaway.")
        self.assertEqual(
            internal_package.move_line_ids[0].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the putaway.")
        self.assertEqual(
            internal_package.move_line_ids[1].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the putaway.")
        internal_transfer.button_validate()

    def test_pack_in_receipt_two_step_multi_putaway(self):
        """ Checks all works right in the following specific corner case:

          * For a two-step receipt, receives two products using two putaways
          targeting different locations.
          * Puts these products in a package then valid the receipt.
          * Cancels the automatically generated internal transfer then create a new one.
          * In this internal transfer, adds the package then valid it.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_step_rule = self.env.ref('stock.group_adv_location')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(3, grp_multi_step_rule.id)]})
        self.env.user.write({'groups_id': [(3, grp_pack.id)]})
        self.warehouse.reception_steps = 'two_steps'
        # Settings of receipt.
        self.warehouse.in_type_id.show_entire_packs = True
        # Settings of internal transfer.
        self.warehouse.store_type_id.show_entire_packs = True

        # Creates two new locations for putaway.
        location_form = Form(self.env['stock.location'])
        location_form.name = 'Shelf A'
        location_form.location_id = self.stock_location
        loc_shelf_A = location_form.save()
        location_form = Form(self.env['stock.location'])
        location_form.name = 'Shelf B'
        location_form.location_id = self.stock_location
        loc_shelf_B = location_form.save()

        # Creates a new putaway rule for productA and productB.
        putaway_A = self.env['stock.putaway.rule'].create({
            'product_id': self.productA.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': loc_shelf_A.id,
        })
        putaway_B = self.env['stock.putaway.rule'].create({
            'product_id': self.productB.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': loc_shelf_B.id,
        })
        self.stock_location.putaway_rule_ids = [(4, putaway_A.id, 0), (4, putaway_B.id, 0)]
        # location_form = Form(self.stock_location)
        # location_form.putaway_rule_ids = [(4, putaway_A.id, 0), (4, putaway_B.id, 0), ],
        # self.stock_location = location_form.save()

        # Create a new receipt with the two products.
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.warehouse.in_type_id
        # Add 2 lines
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.product_uom_qty = 1
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.product_uom_qty = 1
        receipt = receipt_form.save()
        receipt.action_confirm()

        # Adds quantities then packs them and valids the receipt.
        move_form = Form(receipt.move_ids_without_package[0], view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as move_line:
            move_line.quantity = 1
        move_form = Form(receipt.move_ids_without_package[1], view='stock.view_stock_move_operations')
        with move_form.move_line_ids.edit(0) as move_line:
            move_line.quantity = 1
        move_form.save()
        receipt = receipt_form.save()
        receipt.move_ids.picked = True
        receipt.action_put_in_pack()
        receipt.button_validate()

        receipt_package = receipt.package_level_ids[0]
        self.assertEqual(receipt_package.location_dest_id.id, receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[0].location_dest_id.id,
            receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[1].location_dest_id.id,
            receipt.location_dest_id.id)

        # Checks an internal transfer was created following the validation of the receipt.
        internal_transfer = self.env['stock.picking'].search([
            ('picking_type_id', '=', self.warehouse.store_type_id.id)
        ], order='id desc', limit=1)
        self.assertEqual(internal_transfer.origin, receipt.name)
        self.assertEqual(
            len(internal_transfer.package_level_ids), 1)
        internal_package = internal_transfer.package_level_ids[0]
        self.assertEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        self.assertNotEqual(
            internal_package.location_dest_id.id,
            putaway_A.location_out_id.id,
            "The package destination location must be the one from the picking.")
        self.assertNotEqual(
            internal_package.move_line_ids[0].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the picking.")
        self.assertNotEqual(
            internal_package.move_line_ids[1].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the picking.")

        # Cancels the internal transfer and creates a new one.
        internal_transfer.action_cancel()
        picking = self.env['stock.picking'].create({
            'state': 'draft',
            'picking_type_id':  self.warehouse.store_type_id.id,
            })
        internal_form = Form(picking)
        # The test specifically removes the ability to see the location fields
        # grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        # self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        # Hence, `internal_form.location_id` shouldn't be changed
        with internal_form.package_level_ids.new() as pack_line:
            pack_line.package_id = receipt_package.package_id
        internal_transfer = internal_form.save()

        # Checks the package fields have been correctly set.
        internal_package = internal_transfer.package_level_ids[0]
        self.assertEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        internal_transfer.action_assign()
        self.assertEqual(
            internal_package.location_dest_id.id,
            internal_transfer.location_dest_id.id)
        self.assertNotEqual(
            internal_package.location_dest_id.id,
            putaway_A.location_out_id.id,
            "The package destination location must be the one from the picking.")
        self.assertNotEqual(
            internal_package.move_line_ids[0].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the picking.")
        self.assertNotEqual(
            internal_package.move_line_ids[1].location_dest_id.id,
            putaway_A.location_out_id.id,
            "The move line destination location must be the one from the picking.")
        internal_transfer.button_validate()

    def test_partial_put_in_pack(self):
        """ Create a simple move in a delivery. Reserve the quantity but set as quantity done only a part.
        Call Put In Pack button. """
        self.productA.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'product_id': self.productA.id,
            'name': '00001',
        })
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, lot_id=lot1)
        pick_move_a = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.ship_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        pick_move_a._action_confirm()
        pick_move_a._action_assign()
        pick_move_a.picked = True
        pick_move_a.picking_id.button_validate()
        pack_move_a = pick_move_a.move_dest_ids[0]

        pack_picking = pack_move_a.picking_id

        pack_picking.picking_type_id.show_entire_packs = True

        pack_picking.action_assign()

        pack_picking.move_line_ids.quantity = 3
        pack_picking.action_put_in_pack()

    def test_serial_partial_put_in_pack(self):
        """ Create a simple delivery order with a serial tracked product. Then split the move lines into two
         different packages. """
        self.productA.tracking = 'serial'
        self.warehouse.delivery_steps = 'ship_only'
        serials = self.env['stock.lot'].create([{
            'product_id': self.productA.id,
            'name': f'SN{i}',
            'company_id': self.warehouse.company_id.id
        } for i in range(1, 6)])
        for serial in serials:
            self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1.0, lot_id=serial)

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        picking_form = Form(picking)
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 5.0
        picking = picking_form.save()

        picking.action_confirm()
        picking.action_assign()
        move_lines = picking.move_line_ids
        mls_part_1, mls_part_2 = move_lines[:3], move_lines[3:]
        mls_part_1.action_put_in_pack()

        self.assertEqual(len(mls_part_1.result_package_id), 1, 'First three move lines should be assigned a destination package')
        self.assertEqual(len(mls_part_2.result_package_id), 0, 'Other move lines should not be affected')

        mls_part_2.action_put_in_pack()
        self.assertEqual(len(mls_part_2.result_package_id), 1, 'Other move lines should be assigned a package now')
        self.assertNotEqual(mls_part_1.result_package_id, mls_part_2.result_package_id, 'There should be two different packages')

    def test_action_assign_package_level(self):
        """calling _action_assign on move does not erase lines' "result_package_id"
        At the end of the method ``StockMove._action_assign()``, the method
        ``StockPicking._check_entire_pack()`` is called. This method compares
        the move lines with the quants of their source package, and if the entire
        package is moved at once in the same transfer, a ``stock.package_level`` is
        created. On creation of a ``stock.package_level``, the result package of
        the move lines is directly updated with the entire package.
        This is good on the first assign of the move, but when we call assign for
        the second time on a move, for instance because it was made partially available
        and we want to assign the remaining, it can override the result package we
        selected before.
        An override of ``StockPicking._check_move_lines_map_quant_package()`` ensures
        that we ignore:
        * picked lines (quantity > 0)
        * lines with a different result package already
        """
        package = self.env["stock.quant.package"].create({"name": "Src Pack"})
        dest_package1 = self.env["stock.quant.package"].create({"name": "Dest Pack1"})

        # Create new picking: 120 productA
        picking = self.env['stock.picking'].create({
            'state': 'draft',
            'picking_type_id': self.warehouse.pick_type_id.id,
        })
        picking_form = Form(picking)
        with picking_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.product_uom_qty = 120
        picking = picking_form.save()

        # mark as TO-DO
        picking.action_confirm()

        # Update quantity on hand: 100 units in package
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 100, package_id=package)

        # Check Availability
        picking.action_assign()

        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.package_level_ids.package_id, package)

        move = picking.move_ids
        line = move.move_line_ids

        # change the result package and set a quantity
        line.quantity = 100
        line.result_package_id = dest_package1

        # Update quantity on hand: 20 units in new_package
        new_package = self.env["stock.quant.package"].create({"name": "New Pack"})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20, package_id=new_package)

        # Check Availability
        picking.action_assign()

        # Check that result package is not changed on first line
        new_line = move.move_line_ids - line
        self.assertRecordValues(
            line + new_line,
            [
                {"quantity": 100, "result_package_id": dest_package1.id},
                {"quantity": 20, "result_package_id": new_package.id},
            ],
        )

    def test_entire_pack_overship(self):
        """
        Test the scenario of overshipping: we send the customer an entire package, even though it might be more than
        what they initially ordered, and update the quantity on the sales order to reflect what was actually sent.
        """
        self.warehouse.delivery_steps = 'ship_only'
        package = self.env["stock.quant.package"].create({"name": "Src Pack"})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 100, package_id=package)
        self.warehouse.out_type_id.show_entire_packs = True
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        with Form(picking) as picking_form:
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 75
        picking.action_confirm()
        picking.action_assign()
        with Form(picking) as picking_form:
            with picking_form.package_level_ids.new() as package_level:
                package_level.package_id = package
        self.assertEqual(len(picking.move_ids), 1, 'Should have only 1 stock move')
        self.assertEqual(len(picking.move_ids), 1, 'Should have only 1 stock move')
        with Form(picking) as picking_form:
            with picking_form.package_level_ids.edit(0) as package_level:
                package_level.is_done = True
        action = picking.button_validate()

        self.assertEqual(action, True, 'Should not open wizard')

        for ml in picking.move_line_ids:
            self.assertEqual(ml.package_id, package, 'move_line.package')
            self.assertEqual(ml.result_package_id, package, 'move_line.result_package')
            self.assertEqual(ml.state, 'done', 'move_line.state')
        quant = package.quant_ids.filtered(lambda q: q.location_id == self.customer_location)
        self.assertEqual(len(quant), 1, 'Should have quant at customer location')
        self.assertEqual(quant.reserved_quantity, 0, 'quant.reserved_quantity should = 0')
        self.assertEqual(quant.quantity, 100.0, 'quant.quantity should = 100')
        self.assertEqual(sum(ml.quantity for ml in picking.move_line_ids), 100.0, 'total move_line.quantity should = 100')
        backorders = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorders), 0, 'Should not create a backorder')

    def test_remove_package(self):
        """
        In the overshipping scenario, if I remove the package after adding it, we should not remove the associated 
        stock move.
        """
        self.warehouse.delivery_steps = 'ship_only'
        package = self.env["stock.quant.package"].create({"name": "Src Pack"})
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 100, package_id=package)
        self.warehouse.out_type_id.show_entire_packs = True
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        with Form(picking) as picking_form:
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 75
        picking.action_assign()
        with Form(picking) as picking_form:
            with picking_form.package_level_ids.new() as package_level:
                package_level.package_id = package
        with Form(picking) as picking_form:
            picking_form.package_level_ids.remove(0)
        self.assertEqual(len(picking.move_ids), 1, 'Should have only 1 stock move')

    def test_picking_state_with_null_qty(self):
        """ Exclude empty stock move of the picking state computation """
        delivery_form = Form(self.env['stock.picking'])
        picking_type_id = self.warehouse.out_type_id
        delivery_form.picking_type_id = picking_type_id
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.product_uom_qty = 10
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.product_uom_qty = 10
        delivery = delivery_form.save()
        delivery.action_confirm()
        self.assertEqual(delivery.state, 'confirmed')
        delivery.move_ids_without_package[1].product_uom_qty = 0
        self.assertEqual(delivery.state, 'confirmed')

        delivery_form = Form(self.env['stock.picking'])
        picking_type_id = self.warehouse.out_type_id
        delivery_form.picking_type_id = picking_type_id
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.quantity = 10
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.quantity = 10
        delivery = delivery_form.save()
        self.assertEqual(delivery.state, 'assigned')
        delivery.move_ids_without_package[1].quantity = 0
        self.assertEqual(delivery.state, 'assigned')

    def test_2_steps_and_backorder(self):
        """ When creating a backorder with a package, the latter should be reserved in the new picking. Moreover,
         the initial picking shouldn't have any line about this package """
        def create_picking(pick_type, from_loc, to_loc):
            picking = self.env['stock.picking'].create({
                'picking_type_id': pick_type.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
                'state': 'draft',
                })
            move_A, move_B = self.env['stock.move'].create([{
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 1,
                'product_uom': self.productA.uom_id.id,
                'picking_id': picking.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
            }, {
                'name': self.productB.name,
                'product_id': self.productB.id,
                'product_uom_qty': 1,
                'product_uom': self.productB.uom_id.id,
                'picking_id': picking.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
            }])
            picking.action_confirm()
            picking.action_assign()
            return picking, move_A, move_B

        self.warehouse.delivery_steps = 'pick_ship'
        pick_type = self.warehouse.pick_type_id
        delivery_type = self.warehouse.out_type_id

        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 1)

        picking, moveA, moveB = create_picking(pick_type, pick_type.default_location_src_id, pick_type.default_location_dest_id)
        moveA.picked = True
        picking.action_put_in_pack()
        moveB.picked = True
        picking.action_put_in_pack()
        picking.button_validate()
        delivery_type.show_entire_packs = True
        picking = moveA.move_dest_ids.picking_id
        packB = picking.package_level_ids[1]
        picking.package_level_ids_details[0].is_done = True

        action_data = picking.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action_data['context'])).save()
        backorder_wizard.process()
        bo = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])

        self.assertNotIn(packB, picking.package_level_ids)
        self.assertEqual(packB, bo.package_level_ids)
        self.assertEqual(bo.package_level_ids.state, 'assigned')

    def test_package_and_sub_location(self):
        """
        Suppose there are some products P available in shelf1, a child location of the pack location.
        When moving these P to another child location of pack location, the source location of the
        related package level should be shelf1
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.pack_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.pack_location.id,
        })

        pack = self.env['stock.quant.package'].create({'name': 'Super Package'})
        self.env['stock.quant']._update_available_quantity(self.productA, shelf1_location, 20.0, package_id=pack)

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.pack_location.id,
            'location_dest_id': shelf2_location.id,
            'state': 'draft',
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'company_id': picking.company_id.id,
        })

        self.assertEqual(package_level.location_id, shelf1_location)

        picking.action_confirm()
        package_level.is_done = True
        picking.button_validate()

        self.assertEqual(package_level.location_id, shelf1_location)

    def test_pack_in_receipt_two_step_multi_putaway_02(self):
        """
        Suppose a product P, its weight is equal to 1kg
        We have 100 x P on two pallets.
        Receipt in two steps + Sub locations in WH/Stock + Storage Category
        The Storage Category adds some constraints on weight/pallets capacity
        """
        warehouse = self.stock_location.warehouse_id
        warehouse.reception_steps = "two_steps"
        self.productA.weight = 1.0
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id)]})
        # Required for `result_package_id` to be visible in the view
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_tracking_lot').id)]})

        package_type = self.env['stock.package.type'].create({
            'name': "Super Pallet",
        })
        package_01, package_02 = self.env['stock.quant.package'].create([{
            'name': 'Pallet %s' % i,
            'package_type_id': package_type.id,
        } for i in [1, 2]])

        # max 100kg (so 100 x P) and max 1 pallet -> we will work with pallets,
        # so the pallet capacity constraint should be the effective one
        stor_category = self.env['stock.storage.category'].create({
            'name': 'Super Storage Category',
            'max_weight': 100,
            'package_capacity_ids': [(0, 0, {
                'package_type_id': package_type.id,
                'quantity': 1,
            })]
        })

        # 3 sub locations with the storage category
        # (the third location should never be used)
        sub_loc_01, sub_loc_02, dummy = self.env['stock.location'].create([{
            'name': 'Sub Location %s' % i,
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': stor_category.id,
        } for i in [1, 2, 3]])

        self.env['stock.putaway.rule'].create({
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'package_type_ids': [(4, package_type.id)],
            'storage_category_id': stor_category.id,
            'sublocation': 'closest_location',
        })

        # Receive 100 x P
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom': self.productA.uom_id.id,
            'product_uom_qty': 100.0,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        })
        receipt_picking.action_confirm()

        # Distribute the products on two pallets, one with 49 x P and a second
        # one with 51 x P (to easy the debugging in case of trouble)
        move_form = Form(receipt_picking.move_ids, view="stock.view_stock_move_operations")
        with move_form.move_line_ids.edit(0) as line:
            line.quantity = 49
            line.result_package_id = package_01
        with move_form.move_line_ids.new() as line:
            line.quantity = 51
            line.result_package_id = package_02
        move_form.save()
        receipt_picking.move_ids.picked = True
        receipt_picking.button_validate()

        # We are in two-steps receipt -> check the internal picking
        internal_picking = self.env['stock.picking'].search([], order='id desc', limit=1)
        self.assertRecordValues(internal_picking.move_line_ids, [
            {'quantity': 51, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_01.id},
            {'quantity': 49, 'result_package_id': package_01.id, 'location_dest_id': sub_loc_02.id},
        ])

        # Change the constraints of the storage category:
        # max 75kg (so 75 x P) and max 2 pallet -> this time, the weight
        # constraint should be the effective one
        stor_category.max_weight = 75
        stor_category.package_capacity_ids.quantity = 2
        internal_picking.do_unreserve()
        internal_picking.action_assign()
        self.assertRecordValues(internal_picking.move_line_ids, [
            {'quantity': 51, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_01.id},
            {'quantity': 49, 'result_package_id': package_01.id, 'location_dest_id': sub_loc_02.id},
        ])

    def test_pack_in_receipt_two_step_multi_putaway_03(self):
        """
        Two sublocations (max 100kg, max 2 pallet)
        Two products P1, P2, weight = 1kg
        There are 10 x P1 on a pallet in the first sub location
        Receive a pallet of 50 x P1 + 50 x P2 => because of weight constraint, should be redirected to the
            second sub location
        Then, same with max 200kg max 1 pallet => same result, this time because of pallet count constraint
        """
        warehouse = self.stock_location.warehouse_id
        warehouse.reception_steps = "two_steps"
        self.productA.weight = 1.0
        self.productB.weight = 1.0
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id)]})
        # Required for `result_package_id` to be visible in the view
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_tracking_lot').id)]})

        package_type = self.env['stock.package.type'].create({
            'name': "Super Pallet",
        })
        package_01, package_02 = self.env['stock.quant.package'].create([{
            'name': 'Pallet %s' % i,
            'package_type_id': package_type.id,
        } for i in [1, 2]])

        # max 100kg and max 2 pallets
        stor_category = self.env['stock.storage.category'].create({
            'name': 'Super Storage Category',
            'max_weight': 100,
            'package_capacity_ids': [(0, 0, {
                'package_type_id': package_type.id,
                'quantity': 2,
            })]
        })

        # 3 sub locations with the storage category
        # (the third location should never be used)
        sub_loc_01, sub_loc_02, dummy = self.env['stock.location'].create([{
            'name': 'Sub Location %s' % i,
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': stor_category.id,
        } for i in [1, 2, 3]])

        self.env['stock.quant']._update_available_quantity(self.productA, sub_loc_01, 10, package_id=package_01)

        self.env['stock.putaway.rule'].create({
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'package_type_ids': [(4, package_type.id)],
            'storage_category_id': stor_category.id,
            'sublocation': 'closest_location',
        })

        # Receive 50 x P_A and 50 x P_B
        receipt_picking = self.env['stock.picking'].create({
            'picking_type_id': warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'state': 'draft',
        })
        self.env['stock.move'].create([{
            'name': p.name,
            'product_id': p.id,
            'product_uom': p.uom_id.id,
            'product_uom_qty': 50,
            'picking_id': receipt_picking.id,
            'location_id': receipt_picking.location_id.id,
            'location_dest_id': receipt_picking.location_dest_id.id,
        } for p in [self.productA, self.productB]])
        receipt_picking.action_confirm()

        move_form = Form(receipt_picking.move_ids[0], view="stock.view_stock_move_operations")
        with move_form.move_line_ids.edit(0) as line:
            line.quantity = 50
            line.result_package_id = package_02
        move_form.save()
        move_form = Form(receipt_picking.move_ids[1], view="stock.view_stock_move_operations")
        with move_form.move_line_ids.edit(0) as line:
            line.quantity = 50
            line.result_package_id = package_02
        move_form.save()
        receipt_picking.move_ids.picked = True
        receipt_picking.button_validate()

        # We are in two-steps receipt -> check the internal picking
        internal_picking = self.env['stock.picking'].search([], order='id desc', limit=1)
        self.assertRecordValues(internal_picking.move_line_ids, [
            {'product_id': self.productA.id, 'quantity': 50, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_02.id},
            {'product_id': self.productB.id, 'quantity': 50, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_02.id},
        ])

        # Change the constraints of the storage category:
        # max 200kg and max 1 pallet
        stor_category.max_weight = 200
        stor_category.package_capacity_ids.quantity = 1
        internal_picking.do_unreserve()
        internal_picking.action_assign()
        self.assertRecordValues(internal_picking.move_line_ids, [
            {'product_id': self.productA.id, 'quantity': 50, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_02.id},
            {'product_id': self.productB.id, 'quantity': 50, 'result_package_id': package_02.id, 'location_dest_id': sub_loc_02.id},
        ])

    def test_pack_in_receipt_two_step_multi_putaway_04(self):
        """
        Create a putaway rules for package type T and storage category SC. SC
        only allows same products and has a maximum of 2 x T. Four SC locations
        L1, L2, L3 and L4.
        First, move a package that contains two different products: should not
        redirect to L1/L2 because of the "same products" contraint.
        Then, add one T-package (with product P01) at L1 and move 2 T-packages
        (both with product P01): one should be redirected to L1 and the second
        one to L2
        Finally, move 3 T-packages (two with 1xP01, one with 1xP02): one P01
        should be redirected to L2 and the second one to L3 (because of capacity
        constraint), then P02 should be redirected to L4 (because of "same
        product" policy)
        """
        self.warehouse.reception_steps = "two_steps"
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        input_location = self.warehouse.wh_input_stock_loc_id

        package_type = self.env['stock.package.type'].create({
            'name': "package type",
        })

        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'allow_new_product': "same",
            'max_weight': 1000,
            'package_capacity_ids': [(0, 0, {
                'package_type_id': package_type.id,
                'quantity': 2,
            })],
        })

        loc01, loc02, loc03, loc04 = self.env['stock.location'].create([{
            'name': 'loc 0%d' % i,
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        } for i in range(1, 5)])

        self.env['stock.putaway.rule'].create({
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
            'sublocation': 'closest_location',
            'package_type_ids': [(4, package_type.id, 0)],
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': input_location.id,
            'state': 'draft',
            'move_ids': [(0, 0, {
                'name': p.name,
                'location_id': supplier_location.id,
                'location_dest_id': input_location.id,
                'product_id': p.id,
                'product_uom': p.uom_id.id,
                'product_uom_qty': 1.0,
            }) for p in (self.productA, self.productB)],
        })
        receipt.action_confirm()

        moves = receipt.move_ids
        moves.move_line_ids.quantity = 1
        moves.move_line_ids.result_package_id = self.env['stock.quant.package'].create({'package_type_id': package_type.id})
        moves.picked = True
        receipt.button_validate()
        internal_picking = moves.move_dest_ids.picking_id
        self.assertEqual(internal_picking.move_line_ids.location_dest_id, self.stock_location,
                         'Storage location only accepts one same product. Here the package contains two different '
                         'products so it should not be redirected.')
        internal_picking.action_cancel()

        # Second test part
        package = self.env['stock.quant.package'].create({'package_type_id': package_type.id})
        self.env['stock.quant']._update_available_quantity(self.productA, loc01, 1.0, package_id=package)

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': input_location.id,
            'move_ids': [(0, 0, {
                'name': self.productA.name,
                'location_id': supplier_location.id,
                'location_dest_id': input_location.id,
                'product_id': self.productA.id,
                'product_uom': self.productA.uom_id.id,
                'product_uom_qty': 2.0,
            })],
        })
        receipt.action_confirm()

        receipt.do_unreserve()
        self.env['stock.move.line'].create([{
            'move_id': receipt.move_ids.id,
            'quantity': 1,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': input_location.id,
            'result_package_id': self.env['stock.quant.package'].create({'package_type_id': package_type.id}).id,
            'picking_id': receipt.id,
        } for _ in range(2)])
        receipt.move_ids.picked = True
        receipt.button_validate()

        internal_transfer = receipt.move_ids.move_dest_ids.picking_id
        self.assertEqual(internal_transfer.move_line_ids.location_dest_id, loc01 | loc02,
                         'There is already one package at L1, so the first SML should be redirected to L1 '
                         'and the second one to L2')
        internal_transfer.move_line_ids.quantity = 1
        internal_transfer.move_ids.picked = True
        internal_transfer.button_validate()

        # Third part (move 3 packages, 2 x P01 and 1 x P02)
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': input_location.id,
            'move_ids': [(0, 0, {
                'name': product.name,
                'location_id': supplier_location.id,
                'location_dest_id': input_location.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': qty,
            }) for qty, product in [(2.0, self.productA), (1.0, self.productB)]],
        })
        receipt.action_confirm()

        receipt.do_unreserve()
        moves = receipt.move_ids
        self.env['stock.move.line'].create([{
            'move_id': move.id,
            'quantity': 1,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': input_location.id,
            'result_package_id': self.env['stock.quant.package'].create({'package_type_id': package_type.id}).id,
            'picking_id': receipt.id,
        } for product, move in [
            (self.productA, moves[0]),
            (self.productA, moves[0]),
            (self.productB, moves[1]),
        ]])
        receipt.move_ids.picked = True
        receipt.button_validate()

        internal_transfer = receipt.move_ids.move_dest_ids.picking_id
        self.assertRecordValues(internal_transfer.move_line_ids, [
            {'product_id': self.productA.id, 'quantity': 1.0, 'location_dest_id': loc02.id},
            {'product_id': self.productA.id, 'quantity': 1.0, 'location_dest_id': loc03.id},
            {'product_id': self.productB.id, 'quantity': 1.0, 'location_dest_id': loc04.id},
        ])

    def test_rounding_and_reserved_qty(self):
        """
        Basic use case: deliver a storable product put in two packages. This
        test actually ensures that the process 'put in pack' handles some
        possible issues with the floating point representation
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 0.4)

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [(0, 0, {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 0.4,
                'product_uom': self.productA.uom_id.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'picking_type_id': self.warehouse.out_type_id.id,
            })],
            'state': 'draft',
        })
        picking.action_confirm()

        picking.move_line_ids.quantity = 0.3
        picking.move_ids.picked = True
        picking.action_put_in_pack()

        ml = picking.move_line_ids.copy()
        ml.write({
            'quantity': 0.1,
            'result_package_id': False,
        })
        picking.action_put_in_pack()

        quant = self.env['stock.quant'].search([('product_id', '=', self.productA.id), ('location_id', '=', self.stock_location.id)])
        self.assertEqual(quant.available_quantity, 0)

        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.move_ids.quantity, 0.4)
        self.assertEqual(len(picking.move_line_ids.result_package_id), 2)

    def test_put_out_of_pack_transfer(self):
        """ When a transfer has multiple products all in the same package, removing a product from the destination package
        (i.e. removing it from the package but still putting it in the same location) shouldn't remove it for other products. """
        loc_1 = self.env['stock.location'].create({
            'name': 'Location A',
            'location_id': self.stock_location.id,
        })
        loc_2 = self.env['stock.location'].create({
            'name': 'Location B',
            'location_id': self.stock_location.id,
        })
        pack = self.env['stock.quant.package'].create({'name': 'New Package'})
        self.env['stock.quant']._update_available_quantity(self.productA, loc_1, 5, package_id=pack)
        self.env['stock.quant']._update_available_quantity(self.productB, loc_1, 4, package_id=pack)

        picking = self.env['stock.picking'].create({
            'location_id': loc_1.id,
            'location_dest_id': loc_2.id,
            'picking_type_id': self.warehouse.int_type_id.id,
            'state': 'draft',
        })
        moveA = self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': loc_1.id,
            'location_dest_id': loc_2.id,
        })
        moveB = self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 4,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking.id,
            'location_id': loc_1.id,
            'location_dest_id': loc_2.id,
        })
        # Check availabilities
        picking.action_assign()
        self.assertEqual(len(moveA.move_line_ids), 1, "A move line should have been created for the reservation of the package.")
        self.assertEqual(moveA.move_line_ids.package_id.id, pack.id, "The package should have been reserved for both products.")
        self.assertEqual(moveB.move_line_ids.package_id.id, pack.id, "The package should have been reserved for both products.")
        pack_level = moveA.move_line_ids.package_level_id

        # Remove the product A from the package in the destination.
        moveA.move_line_ids.result_package_id = False
        self.assertEqual(moveA.move_line_ids.result_package_id.id, False, "No package should be linked in the destination.")
        self.assertEqual(moveA.move_line_ids.package_level_id.id, False, "Package level should have been unlinked from this move line.")
        self.assertEqual(moveB.move_line_ids.result_package_id.id, pack.id, "Package should have stayed the same.")
        self.assertEqual(moveB.move_line_ids.package_level_id.id, pack_level.id, "Package level should have stayed the same.")

        # Validate the picking
        picking.move_ids.picked = True
        picking.button_validate()

        # Check that the quants have their expected location/package/quantities
        quantA = self.env['stock.quant'].search([('product_id', '=', self.productA.id), ('location_id', '=', loc_2.id)])
        quantB = self.env['stock.quant'].search([('product_id', '=', self.productB.id), ('location_id', '=', loc_2.id)])
        self.assertEqual(pack.location_id.id, loc_2.id, "Package should have been moved to Location B.")
        self.assertEqual(quantA.quantity, 5, "All 5 units of product A should be in location B")
        self.assertEqual(quantA.package_id.id, False, "There should be no package for product A as it was removed in the move.")
        self.assertEqual(quantB.quantity, 4, "All 4 units of product B should be in location B")
        self.assertEqual(quantB.package_id.id, pack.id, "Product B should still be in the initial package.")

    def test_expected_to_pack(self):
        """ Test direct calling of `_to_pack` since it doesn't handle all multi-record cases
        It's unlikely this situations will occur, but in case it is for customizations/future features,
        ensure that we don't have unexpected behavior """

        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0)

        internal_picking_1 = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'quantity': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': internal_picking_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })

        internal_picking_2 = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'quantity': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': internal_picking_2.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })

        in_picking_1 = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'quantity': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_id': in_picking_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })

        # can't mix operation types
        with self.assertRaises(UserError):
            move_lines_to_pack = (internal_picking_1 | in_picking_1).move_line_ids._to_pack()

        move_lines_to_pack = (internal_picking_1 | internal_picking_2).move_line_ids._to_pack()
        self.assertEqual(len(move_lines_to_pack), 2, "all move lines in pickings should have been selected to pack")

    def test_package_selection(self):
        """
        Test that the package selection is correct when using the least_package_strategy:
        - Pack 1 -> 10 unit, PAck 2 -> 10 unit, Pack 3 -> 20 unit
        - SO 1 -> 20 unit, SO 2 -> 10 unit, SO 3 -> 10 unit
        SO 1 should be in Pack 3, SO 2 in Pack 1 and SO 3 in Pack 2
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })

        # Set the removal strategy to 'least_packages'
        least_package_strategy = self.env['product.removal'].search(
            [('method', '=', 'least_packages')])
        product.categ_id.removal_strategy_id = least_package_strategy.id
        # Create three packages with different quantities: 10, 10 and 20
        pack_1 = self.env['stock.quant.package'].create({
            'name': 'Pack 1',
            'quant_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 10,
                'location_id': self.stock_location.id,
            })],
        })
        pack_2 = self.env['stock.quant.package'].create({
            'name': 'Pack 2',
            'quant_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 10,
                'location_id': self.stock_location.id,
            })],
        })
        pack_3 = self.env['stock.quant.package'].create({
            'name': 'Pack 3',
            'quant_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 20,
                'location_id': self.stock_location.id,
            })],
        })
        # Create a quant without package to include none element in the selection of the package
        self.env['stock.quant'].create({
            'product_id': product.id,
            'quantity': 5,
            'location_id': self.stock_location.id,
        })
        # Check that the total quantity of the product is 40
        self.assertEqual(product.qty_available, 45)

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'product_uom_qty': 20,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking.action_confirm()
        self.assertEqual(move.move_line_ids.result_package_id, pack_3)

        picking_02 = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_02 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'picking_id': picking_02.id,
            'product_uom_qty': 10,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_02.action_confirm()
        self.assertEqual(move_02.move_line_ids.result_package_id, pack_1)

        picking_03 = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move_03 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'picking_id': picking_03.id,
            'product_uom_qty': 10,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_03.action_confirm()
        self.assertEqual(move_03.move_line_ids.result_package_id, pack_2)

    def test_change_package_location(self):
        pack_1 = self.env['stock.quant.package'].create({
            'name': 'Pack 1',
            'quant_ids': [Command.create({
                'product_id': self.productA.id,
                'quantity': 10,
                'location_id': self.stock_location.id,
            })],
        })
        pack_2 = self.env['stock.quant.package'].create({
            'name': 'Pack 2',
            'quant_ids': [Command.create({
                'product_id': self.productB.id,
                'quantity': 10,
                'location_id': self.stock_location.id,
            })],
        })
        (pack_1 | pack_2).location_id = self.shelf1
        moves = self.env['stock.move'].search([
            ('location_id', '=', self.stock_location.id),
            ('location_dest_id', '=', self.shelf1.id),
            ('reference', '=', 'Package manually relocated'),
        ])
        self.assertEqual(pack_1.location_id, self.shelf1)
        self.assertEqual(pack_2.location_id, self.shelf1)
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves.product_id, self.productA | self.productB)
        with self.assertRaises(UserError):
            pack_1.location_id = False
        pack_1.quant_ids = False
        with self.assertRaises(UserError):
            pack_1.location_id = self.shelf1

    def test_action_split_transfer(self):
        """ Check Split Picking if quantity `0 <= done < demand`
        """
        loc_1 = self.env['stock.location'].create({
            'name': 'Location A',
            'location_id': self.stock_location.id,
        })
        loc_2 = self.env['stock.location'].create({
            'name': 'Location B',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.productA, loc_1, 10)
        self.env['stock.quant']._update_available_quantity(self.productB, loc_1, 10)
        picking = self.env['stock.picking'].create({
            'location_id': loc_1.id,
            'location_dest_id': loc_2.id,
            'picking_type_id': self.warehouse.int_type_id.id,
            'state': 'draft',
            'move_ids': [
                Command.create({
                    'name': self.productA.name,
                    'product_id': self.productA.id,
                    'product_uom_qty': 10,
                    'location_id': loc_1.id,
                    'location_dest_id': loc_2.id,
                    'quantity': 8,
                }),
                Command.create({
                    'name': self.productB.name,
                    'product_id': self.productB.id,
                    'product_uom_qty': 10,
                    'location_id': loc_1.id,
                    'location_dest_id': loc_2.id,
                    'quantity': 0,
                }),
            ]
        })
        picking.action_confirm()
        picking.action_split_transfer()
        self.assertEqual(len(picking.move_ids), 1)
        self.assertEqual(picking.move_ids[0].product_uom_qty, 8)
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder.move_ids), 2)
        self.assertEqual(backorder.move_ids[0].product_uom_qty, 2)
        self.assertEqual(backorder.move_ids[1].product_uom_qty, 10)

    def test_put_in_pack_partial_different_destinations(self):
        """ Test putting some of the move lines of a pikcing with different destinations in a package """
        self.productA.tracking = 'serial'

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
        })
        picking_form = Form(picking)
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productA
            move.product_uom_qty = 5.0
        picking = picking_form.save()
        picking.action_confirm()

        self.assertItemsEqual(picking.move_line_ids.mapped('quantity'), [1.0] * 5)

        sub_location = self.env['stock.location'].create({
            'name': 'Sub Location',
            'location_id': self.stock_location.id,
        })
        picking.move_line_ids[0].location_dest_id = sub_location

        destination_wizard_dict = picking.move_line_ids[0:2].action_put_in_pack()
        destination_wizard = self.env[destination_wizard_dict['res_model']].browse(destination_wizard_dict['res_id'])
        self.assertEqual(len(destination_wizard.move_line_ids), 2)
        destination_wizard.action_done()

        self.assertEqual(len(picking.move_line_ids[0:2].result_package_id), 1)
        self.assertEqual(picking.move_line_ids[0].result_package_id, picking.move_line_ids[1].result_package_id)
        self.assertEqual(len(picking.move_line_ids[2:].result_package_id), 0)
        self.assertEqual(picking.move_line_ids[0:2].location_dest_id, destination_wizard.location_dest_id)

    def test_pick_another_pack(self):
        """ Do a receipt and split the products in three different packages.
        Enable move entire package for the delivery picking type
        Create a delivery that require the quantities in the first two packages.
        Remove the second package and use the third instead. Pick both package.
        Check availability on the picking.
        Ensure it results with the two first package reserved. The first and the third package
        should be picked.
        """
        self.warehouse.write({'delivery_steps': 'ship_only'})

        pack1, pack2, pack3 = self.env['stock.quant.package'].create([
            {'name': 'pack1'},
            {'name': 'pack2'},
            {'name': 'pack3'}
        ])
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1, package_id=pack2)
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1, package_id=pack3)

        # Enable move entire package for the delivery picking type
        self.warehouse.out_type_id.show_entire_packs = True

        # Create a delivery that require the quantities in the first two packages
        delivery = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 2.0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': delivery.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        delivery.action_confirm()
        self.assertEqual(delivery.package_level_ids.package_id, pack1 | pack2, 'The two first packages should be picked')
        delivery.package_level_ids[-1].unlink()
        self.env['stock.package_level'].create({
            'package_id': pack3.id,
            'picking_id': delivery.id,
            'company_id': delivery.company_id.id,
            'location_dest_id': delivery.location_dest_id.id,
        })
        delivery.package_level_ids.is_done = True
        delivery.move_line_ids.filtered(lambda ml: ml.package_id == pack2).unlink()
        delivery.action_assign()
        delivery.package_level_ids.invalidate_recordset()
        self.assertRecordValues(delivery.package_level_ids, [
            {'package_id': pack1.id, 'state': 'assigned', 'is_done': True},
            {'package_id': pack3.id, 'state': 'assigned', 'is_done': True},
        ])


@odoo.tests.tagged('post_install', '-at_install')
class TestPackagePropagation(TestPackingCommon):

    def test_reusable_package_propagation(self):
        """ Test a reusable package should not be propagated to the next picking
        of a mto chain """
        reusable_package = self.env['stock.quant.package'].create({
            'name': 'Reusable Package',
            'package_use': 'reusable',
        })
        disposable_package = self.env['stock.quant.package'].create({
            'name': 'disposable Package',
            'package_use': 'disposable',
        })
        self.productA = self.env['product.product'].create({
            'name': 'productA',
            'is_storable': True,
            'tracking': 'none',
        })
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 2)
        pg = self.env['procurement.group'].create({'name': 'propagation_test'})
        self.env['procurement.group'].run([
            pg.Procurement(
                self.productA,
                2.0,
                self.productA.uom_id,
                self.customer_location,
                'propagation_test',
                'propagation_test',
                self.warehouse.company_id,
                {
                    'warehouse_id': self.warehouse,
                    'group_id': pg
                }
            )
        ])
        picking = self.env['stock.picking'].search([
            ('group_id', '=', pg.id),
            ('location_id', '=', self.stock_location.id),
        ])
        picking.action_assign()
        picking.move_ids.move_line_ids.result_package_id = reusable_package
        picking.move_ids.move_line_ids.copy({'result_package_id': disposable_package.id})
        picking.move_ids.move_line_ids.quantity = 1
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        pack_lines = self.env['stock.picking'].search([
            ('group_id', '=', pg.id),
            ('location_id', '=', self.pack_location.id),
        ]).move_line_ids

        self.assertEqual(len(pack_lines), 2, 'Should have only 2 stock move line')
        self.assertFalse(pack_lines[0].result_package_id, 'Should not have the reusable package')
        self.assertEqual(pack_lines[1].result_package_id, disposable_package, 'Should have only the disposable package')
