# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import SavepointCase
from odoo.tools import float_round
from odoo.exceptions import UserError


class TestPackingCommon(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPackingCommon, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.warehouse = cls.env['stock.warehouse'].search([('lot_stock_id', '=', cls.stock_location.id)], limit=1)
        cls.warehouse.write({'delivery_steps': 'pick_pack_ship'})
        cls.pack_location = cls.warehouse.wh_pack_stock_loc_id
        cls.ship_location = cls.warehouse.wh_output_stock_loc_id
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.productA = cls.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        cls.productB = cls.env['product.product'].create({'name': 'Product B', 'type': 'product'})


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

        pick_picking.picking_type_id.show_entire_packs = True
        packing_picking.picking_type_id.show_entire_packs = True
        shipping_picking.picking_type_id.show_entire_packs = True

        pick_picking.action_assign()
        self.assertEqual(len(pick_picking.move_ids_without_package), 2)
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA).qty_done = 1.0
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productB).qty_done = 2.0

        first_pack = pick_picking.action_put_in_pack()
        self.assertEqual(len(pick_picking.package_level_ids), 1, 'Put some products in pack should create a package_level')
        self.assertEqual(pick_picking.package_level_ids[0].state, 'new', 'A new pack should be in state "new"')
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA and ml.qty_done == 0.0).qty_done = 4.0
        pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productB and ml.qty_done == 0.0).qty_done = 3.0
        second_pack = pick_picking.action_put_in_pack()
        self.assertEqual(len(pick_picking.move_ids_without_package), 0)
        self.assertEqual(len(packing_picking.move_ids_without_package), 2)
        pick_picking.button_validate()
        self.assertEqual(len(packing_picking.move_ids_without_package), 0)
        self.assertEqual(len(first_pack.quant_ids), 2)
        self.assertEqual(len(second_pack.quant_ids), 2)
        packing_picking.action_assign()
        self.assertEqual(len(packing_picking.package_level_ids), 2, 'Two package levels must be created after assigning picking')
        packing_picking.package_level_ids.write({'is_done': True})
        packing_picking._action_done()

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
            'location_dest_id': self.stock_location.id,
            'company_id': picking.company_id.id,
        })
        self.assertEqual(package_level.state, 'draft',
                          'The package_level should be in draft as it has no moves, move lines and is not confirmed')
        picking.action_confirm()
        self.assertEqual(len(picking.move_ids_without_package), 0)
        self.assertEqual(len(picking.move_lines), 1,
                         'One move should be created when the package_level has been confirmed')
        self.assertEqual(len(package_level.move_ids), 1,
                          'The move should be in the package level')
        self.assertEqual(package_level.state, 'confirmed',
                          'The package level must be state confirmed when picking is confirmed')
        picking.action_assign()
        self.assertEqual(len(picking.move_lines), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_lines.move_line_ids), 1,
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
        self.assertEqual(package_level.move_line_ids[0].qty_done, 20.0,
                          'All quantity in package must be procesed in move line')
        picking.button_validate()
        self.assertEqual(len(picking.move_lines), 1,
                         'You still have only one move when the picking is assigned')
        self.assertEqual(len(picking.move_lines.move_line_ids), 1,
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
        self.assertTrue(package_level.move_line_ids)
        self.assertTrue(
            all(package_level.move_line_ids.mapped(lambda l: l.state == 'cancel'))
        )

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
            'location_dest_id': self.stock_location.id,
            'company_id': picking.company_id.id,
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'location_dest_id': self.stock_location.id,
            'company_id': picking.company_id.id,
        })
        picking.action_confirm()
        self.assertEqual(picking.package_level_ids.mapped('location_id.id'), [shelf1_location.id],
                         'The package levels should still in the same location after confirmation.')
        picking.action_assign()
        package_level_reserved = picking.package_level_ids.filtered(lambda pl: pl.state == 'assigned')
        package_level_confirmed = picking.package_level_ids.filtered(lambda pl: pl.state == 'confirmed')
        self.assertEqual(package_level_reserved.location_id.id, shelf1_location.id, 'The reserved package level must be reserved in shelf1')
        self.assertEqual(package_level_confirmed.location_id.id, shelf1_location.id, 'The not reserved package should keep its location')
        picking.do_unreserve()
        self.assertEqual(picking.package_level_ids.mapped('location_id.id'), [shelf1_location.id],
                         'The package levels should have back the original location.')
        picking.package_level_ids.write({'is_done': True})
        picking.action_assign()
        package_level_reserved = picking.package_level_ids.filtered(lambda pl: pl.state == 'assigned')
        package_level_confirmed = picking.package_level_ids.filtered(lambda pl: pl.state == 'confirmed')
        self.assertEqual(package_level_reserved.location_id.id, shelf1_location.id, 'The reserved package level must be reserved in shelf1')
        self.assertEqual(package_level_confirmed.location_id.id, shelf1_location.id, 'The not reserved package should keep its location')
        self.assertEqual(picking.package_level_ids.mapped('is_done'), [True, True], 'Both package should still done')

    def test_put_in_pack_to_different_location(self):
        """ Hitting 'Put in pack' button while some move lines go to different
            location should trigger a wizard. This wizard applies the same destination
            location to all the move lines
        """
        self.warehouse.in_type_id.show_reserved = True
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
            'location_id': self.stock_location.id,
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
        picking.move_line_ids.filtered(lambda ml: ml.product_id == self.productA).qty_done = 5.0
        picking.action_put_in_pack()
        pack1 = self.env['stock.quant.package'].search([])[-1]
        picking.write({
            'move_line_ids': [(0, 0, {
                'product_id': self.productB.id,
                'product_uom_qty': 7.0,
                'qty_done': 7.0,
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
                'product_uom_qty': 5.0,
                'qty_done': 5.0,
                'product_uom_id': self.productA.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': shelf1_location.id,
                'picking_id': picking.id,
                'state': 'confirmed',
            })]
        })
        wizard_values = picking.action_put_in_pack()
        wizard = self.env[(wizard_values.get('res_model'))].browse(wizard_values.get('res_id'))
        wizard.location_dest_id = shelf2_location.id
        wizard.action_done()
        picking._action_done()
        pack2 = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(pack2.location_id.id, shelf2_location.id, 'The package must be stored  in shelf2')
        self.assertEqual(pack1.location_id.id, shelf1_location.id, 'The package must be stored  in shelf1')
        qp1 = pack2.quant_ids[0]
        qp2 = pack2.quant_ids[1]
        self.assertEqual(qp1.quantity + qp2.quantity, 12, 'The quant has not the good quantity')

    def test_move_picking_with_package(self):
        """
        355.4 rounded with 0.01 precision is 355.40000000000003.
        check that nonetheless, moving a picking is accepted
        """
        self.assertEqual(self.productA.uom_id.rounding, 0.01)
        self.assertEqual(
            float_round(355.4, precision_rounding=self.productA.uom_id.rounding),
            355.40000000000003,
        )
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
                'move_lines': [(6, 0, [move.id])],
        }})

        picking.action_confirm()
        picking.action_assign()
        move.quantity_done = move.reserved_availability
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
            'qty_done': 5.0,
            'picking_id': picking.id,
            'result_package_id': package.id,
        })
        self.env['stock.move.line'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': shelf2.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'qty_done': 5.0,
            'picking_id': picking.id,
            'result_package_id': package.id,
        })
        picking.action_confirm()
        with self.assertRaises(UserError):
            picking._action_done()

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
        self.warehouse.in_type_id.show_operations = True
        self.warehouse.in_type_id.show_entire_packs = True
        self.warehouse.in_type_id.show_reserved = True
        # Settings of internal transfer.
        self.warehouse.int_type_id.show_operations = True
        self.warehouse.int_type_id.show_entire_packs = True
        self.warehouse.int_type_id.show_reserved = True

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
        receipt_form = Form(receipt)
        with receipt_form.move_line_ids_without_package.edit(0) as move_line:
            move_line.qty_done = 1
        with receipt_form.move_line_ids_without_package.edit(1) as move_line:
            move_line.qty_done = 1
        receipt = receipt_form.save()
        receipt.action_put_in_pack()
        receipt.button_validate()

        receipt_package = receipt.package_level_ids_details[0]
        self.assertEqual(receipt_package.location_dest_id.id, receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[0].location_dest_id.id,
            receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[1].location_dest_id.id,
            receipt.location_dest_id.id)

        # Checks an internal transfer was created following the validation of the receipt.
        internal_transfer = self.env['stock.picking'].search([
            ('picking_type_id', '=', self.warehouse.int_type_id.id)
        ], order='id desc', limit=1)
        self.assertEqual(internal_transfer.origin, receipt.name)
        self.assertEqual(
            len(internal_transfer.package_level_ids_details), 1)
        internal_package = internal_transfer.package_level_ids_details[0]
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
        internal_form = Form(self.env['stock.picking'])
        internal_form.picking_type_id = self.warehouse.int_type_id
        internal_form.location_id = self.warehouse.wh_input_stock_loc_id
        with internal_form.package_level_ids_details.new() as pack_line:
            pack_line.package_id = receipt_package.package_id
        internal_transfer = internal_form.save()

        # Checks the package fields have been correctly set.
        internal_package = internal_transfer.package_level_ids_details[0]
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
        self.warehouse.in_type_id.show_operations = True
        self.warehouse.in_type_id.show_entire_packs = True
        self.warehouse.in_type_id.show_reserved = True
        # Settings of internal transfer.
        self.warehouse.int_type_id.show_operations = True
        self.warehouse.int_type_id.show_entire_packs = True
        self.warehouse.int_type_id.show_reserved = True

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
        receipt_form = Form(receipt)
        with receipt_form.move_line_ids_without_package.edit(0) as move_line:
            move_line.qty_done = 1
        with receipt_form.move_line_ids_without_package.edit(1) as move_line:
            move_line.qty_done = 1
        receipt = receipt_form.save()
        receipt.action_put_in_pack()
        receipt.button_validate()

        receipt_package = receipt.package_level_ids_details[0]
        self.assertEqual(receipt_package.location_dest_id.id, receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[0].location_dest_id.id,
            receipt.location_dest_id.id)
        self.assertEqual(
            receipt_package.move_line_ids[1].location_dest_id.id,
            receipt.location_dest_id.id)

        # Checks an internal transfer was created following the validation of the receipt.
        internal_transfer = self.env['stock.picking'].search([
            ('picking_type_id', '=', self.warehouse.int_type_id.id)
        ], order='id desc', limit=1)
        self.assertEqual(internal_transfer.origin, receipt.name)
        self.assertEqual(
            len(internal_transfer.package_level_ids_details), 1)
        internal_package = internal_transfer.package_level_ids_details[0]
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
        internal_form = Form(self.env['stock.picking'])
        internal_form.picking_type_id = self.warehouse.int_type_id
        internal_form.location_id = self.warehouse.wh_input_stock_loc_id
        with internal_form.package_level_ids_details.new() as pack_line:
            pack_line.package_id = receipt_package.package_id
        internal_transfer = internal_form.save()

        # Checks the package fields have been correctly set.
        internal_package = internal_transfer.package_level_ids_details[0]
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
        lot1 = self.env['stock.production.lot'].create({
            'product_id': self.productA.id,
            'name': '00001',
            'company_id': self.warehouse.company_id.id
        })
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0, lot_id=lot1)
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
        ship_move_a._assign_picking()
        ship_move_a._action_confirm()
        pack_move_a = ship_move_a.move_orig_ids[0]
        pick_move_a = pack_move_a.move_orig_ids[0]

        pick_picking = pick_move_a.picking_id

        pick_picking.picking_type_id.show_entire_packs = True

        pick_picking.action_assign()

        pick_picking.move_line_ids.qty_done = 3
        first_pack = pick_picking.action_put_in_pack()

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
        * picked lines (qty_done > 0)
        * lines with a different result package already
        """
        package = self.env["stock.quant.package"].create({"name": "Src Pack"})
        dest_package1 = self.env["stock.quant.package"].create({"name": "Dest Pack1"})

        # Create new picking: 120 productA
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.warehouse.pick_type_id
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

        move = picking.move_lines
        line = move.move_line_ids

        # change the result package and set a qty_done
        line.qty_done = 100
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
                {"qty_done": 100, "result_package_id": dest_package1.id},
                {"qty_done": 0, "result_package_id": new_package.id},
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
        })
        with Form(picking) as picking_form:
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 75
        picking.action_confirm()
        picking.action_assign()
        with Form(picking) as picking_form:
            with picking_form.package_level_ids_details.new() as package_level:
                package_level.package_id = package
        self.assertEqual(len(picking.move_lines), 1, 'Should have only 1 stock move')
        self.assertEqual(len(picking.move_lines), 1, 'Should have only 1 stock move')
        with Form(picking) as picking_form:
            with picking_form.package_level_ids_details.edit(0) as package_level:
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
        self.assertEqual(sum(ml.qty_done for ml in picking.move_line_ids), 100.0, 'total move_line.qty_done should = 100')
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
        })
        with Form(picking) as picking_form:
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 75
        picking.action_assign()
        with Form(picking) as picking_form:
            with picking_form.package_level_ids_details.new() as package_level:
                package_level.package_id = package
        with Form(picking) as picking_form:
            picking_form.package_level_ids.remove(0)
        self.assertEqual(len(picking.move_lines), 1, 'Should have only 1 stock move')

    def test_picking_state_with_null_qty(self):
        receipt_form = Form(self.env['stock.picking'].with_context(default_immediate_transfer=False))
        picking_type_id = self.warehouse.out_type_id
        receipt_form.picking_type_id = picking_type_id
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.product_uom_qty = 10
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.product_uom_qty = 10
        receipt = receipt_form.save()
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'confirmed')
        receipt.move_ids_without_package[1].product_uom_qty = 0
        self.assertEqual(receipt.state, 'confirmed')

        receipt_form = Form(self.env['stock.picking'].with_context(default_immediate_transfer=True))
        picking_type_id = self.warehouse.out_type_id
        receipt_form.picking_type_id = picking_type_id
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productA
            move_line.quantity_done = 10
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.productB
            move_line.quantity_done = 10
        receipt = receipt_form.save()
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'assigned')
        receipt.move_ids_without_package[1].product_uom_qty = 0
        self.assertEqual(receipt.state, 'assigned')

    def test_2_steps_and_backorder(self):
        """ When creating a backorder with a package, the latter should be reserved in the new picking. Moreover,
         the initial picking shouldn't have any line about this package """
        def create_picking(type, from_loc, to_loc):
            picking = self.env['stock.picking'].create({
                'picking_type_id': type.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
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

        output_location = self.warehouse.wh_output_stock_loc_id
        pick_type = self.warehouse.pick_type_id
        delivery_type = self.warehouse.out_type_id

        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 1)

        picking, moveA, moveB = create_picking(pick_type, pick_type.default_location_src_id, pick_type.default_location_dest_id)
        moveA.move_line_ids.qty_done = 1
        picking.action_put_in_pack()
        moveB.move_line_ids.qty_done = 1
        picking.action_put_in_pack()
        picking.button_validate()

        picking, _, _ = create_picking(delivery_type, delivery_type.default_location_src_id, self.customer_location)
        packB = picking.package_level_ids[1]
        with Form(picking) as picking_form:
            with picking_form.package_level_ids_details.edit(0) as package_level:
                package_level.is_done = True
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
        })
        package_level = self.env['stock.package_level'].create({
            'package_id': pack.id,
            'picking_id': picking.id,
            'location_dest_id': picking.location_dest_id.id,
            'company_id': picking.company_id.id,
        })

        self.assertEqual(package_level.location_id, shelf1_location)

        picking.action_confirm()
        package_level.is_done = True
        picking.button_validate()

        self.assertEqual(package_level.location_id, shelf1_location)

    def test_2_steps_and_reservation(self):
        """ When creating a backorder in a two steps flow, the reservation should be resilient 
        to the change of quantity in any move of the chain. The test scenario is the following:
                        
                                     - move (5 units) CONFIRMED
                                   /
        move orig (10 units) DONE -
                                   \ - move sibling (5 units) DONE
                                   
        The confirmed move can be assigned because on the 10 units validated on the move 
        orig, only 5 have already been validated in the sibling move. If before the 
        reservation the move orig is unlocked and the quantity is changed from 10 to 1, the 
        confirmed move cannot reserve any quantity anymore but should be able to call 
        action_assign without any error."""

        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 20.0)
        self.env['stock.quant']._update_available_quantity(self.productA, self.pack_location, 30.0)
        ship_move_a = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.productA.id,
            'product_uom_qty': 20.0,
            'product_uom': self.productA.uom_id.id,
            'location_id': self.ship_location.id,
            'location_dest_id': self.customer_location.id,
            'warehouse_id': self.warehouse.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })
        ship_move_a._assign_picking()
        ship_move_a._action_confirm()
        pack_move_a = ship_move_a.move_orig_ids[0]
        pick_move_a = pack_move_a.move_orig_ids[0]

        pick_move_a.quantity_done = 20
        pick_move_a._action_done()

        pack_move_a.quantity_done = 10
        picking = pack_move_a.picking_id
        action_data = picking.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action_data['context'])).save()
        backorder_wizard.process()

        # change validated quantity of the first step
        pick_move_a.quantity_done = 5

        # check the backorder can still be reserved
        backorder = (pack_move_a.move_orig_ids.move_dest_ids - pack_move_a).picking_id
        backorder.action_assign()
