# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from datetime import datetime, timedelta

from odoo.fields import Datetime as Dt
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpOrder(TestMrpCommon):

    def test_access_rights_manager(self):
        man_order = self.env['mrp.production'].sudo(self.user_mrp_manager).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': 5.0,
            'bom_id': self.bom_1.id,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_access_rights_user(self):
        man_order = self.env['mrp.production'].sudo(self.user_mrp_user).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': 5.0,
            'bom_id': self.bom_1.id,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_basic(self):
        """ Basic order test: no routing (thus no workorders), no lot """
        self.product_1.type = 'product'
        self.product_2.type = 'product'
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            }), (0, 0, {
                'product_id': self.product_2.id,
                'product_uom_id': self.product_2.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_validate()

        test_date_planned = Dt.now() - timedelta(days=1)
        test_quantity = 2.0
        self.bom_1.routing_id = False
        man_order = self.env['mrp.production'].sudo(self.user_mrp_user).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': test_quantity,
            'bom_id': self.bom_1.id,
            'date_planned_start': test_date_planned,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        self.assertEqual(man_order.state, 'confirmed', "Production order should be in confirmed state.")

        # check production move
        production_move = man_order.move_finished_ids
        self.assertEqual(production_move.date, test_date_planned)
        self.assertEqual(production_move.product_id, self.product_4)
        self.assertEqual(production_move.product_uom, man_order.product_uom_id)
        self.assertEqual(production_move.product_qty, man_order.product_qty)
        self.assertEqual(production_move.location_id, self.product_4.property_stock_production)
        self.assertEqual(production_move.location_dest_id, man_order.location_dest_id)

        # check consumption moves
        for move in man_order.move_raw_ids:
            self.assertEqual(move.date, test_date_planned)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_2)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 2)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_1)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 4)

        # waste some material, create a scrap
        # scrap = self.env['stock.scrap'].with_context(
        #     active_model='mrp.production', active_id=man_order.id
        # ).create({})
        # scrap = self.env['stock.scrap'].create({
        #     'production_id': man_order.id,
        #     'product_id': first_move.product_id.id,
        #     'product_uom_id': first_move.product_uom.id,
        #     'scrap_qty': 5.0,
        # })
        # check created scrap


        # procurements = self.env['procurement.order'].search([('move_dest_id', 'in', man_order.move_raw_ids.ids)])
        # print procurements
        # procurements = self.env['procurement.order'].search([('production_id', '=', man_order.id)])
        # print procurements
        # for proc in self.env['procurement.order'].browse(procurements):
        #     date_planned = self.mrp_production_test1.date_planned
        #     if proc.product_id.type not in ('product', 'consu'):
        #         continue
        #     if proc.product_id.id == order_line.product_id.id:
        #         self.assertEqual(proc.date_planned, date_planned, "Planned date does not correspond")
        #       # procurement state should be `confirmed` at this stage, except if procurement_jit is installed, in which
        #       # case it could already be in `running` or `exception` state (not enough stock)
        #         expected_states = ('confirmed', 'running', 'exception')
        #         self.assertEqual(proc.state in expected_states, 'Procurement state is `%s` for %s, expected one of %s' % (proc.state, proc.product_id.name, expected_states))

        # Change production quantity
        qty_wizard = self.env['change.production.qty'].create({
            'mo_id': man_order.id,
            'product_qty': 3.0,
        })
        # qty_wizard.change_prod_qty()

        # # I check qty after changed in production order.
        # #self.assertEqual(self.mrp_production_test1.product_qty, 3, "Qty is not changed in order.")
        # move = self.mrp_production_test1.move_finished_ids[0]
        # self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty is not changed in move line.")

        # # I run scheduler.
        # self.env['procurement.order'].run_scheduler()

        # # The production order is Waiting Goods, will force production which should set consume lines as available
        # self.mrp_production_test1.button_plan()
        # # I check that production order in ready state after forcing production.

        # #self.assertEqual(self.mrp_production_test1.availability, 'assigned', 'Production order availability should be set as available')

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': man_order.id,
            'active_ids': [man_order.id],
        }))
        produce_form.product_qty = 1.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        # man_order.button_mark_done()
        man_order.button_mark_done()
        self.assertEqual(man_order.state, 'done', "Production order should be in done state.")

    def test_explode_from_order(self):
        #
        # bom3 produces 2 Dozen of Doors (p6), aka 24
        # To produce 24 Units of Doors (p6)
        # - 2 Units of Tools (p5) -> need 4
        # - 8 Dozen of Sticks (p4) -> need 16
        # - 12 Units of Wood (p2) -> need 24
        # bom2 produces 1 Unit of Sticks (p4)
        # To produce 1 Unit of Sticks (p4)
        # - 2 Dozen of Sticks (p4) -> need 8
        # - 3 Dozen of Stones (p3) -> need 12

        # Update capacity, start time, stop time, and time efficiency.
        # ------------------------------------------------------------
        self.workcenter_1.write({'capacity': 1, 'time_start': 0, 'time_stop': 0, 'time_efficiency': 100})

        # Set manual time cycle 20 and 10.
        # --------------------------------
        self.operation_1.write({'time_cycle_manual': 20})
        (self.operation_2 | self.operation_3).write({'time_cycle_manual': 10})

        man_order = self.env['mrp.production'].create({
            'name': 'MO-Test',
            'product_id': self.product_6.id,
            'product_uom_id': self.product_6.uom_id.id,
            'product_qty': 48,
            'bom_id': self.bom_3.id,
        })

        # reset quantities
        self.product_1.type = "product"
        self.env['stock.change.product.qty'].create({
            'product_id': self.product_1.id,
            'new_quantity': 0.0,
            'location_id': self.warehouse_1.lot_stock_id.id,
        }).change_product_qty()

        (self.product_2 | self.product_4).write({
            'tracking': 'none',
        })
        # assign consume material
        man_order.action_assign()
        self.assertEqual(man_order.availability, 'waiting', "Production order should be in waiting state.")

        # check consume materials of manufacturing order
        self.assertEqual(len(man_order.move_raw_ids), 4, "Consume material lines are not generated proper.")
        product_2_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_2)
        product_3_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_3)
        product_4_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_4)
        product_5_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_5)
        consume_qty_2 = product_2_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_2, 24.0, "Consume material quantity of Wood should be 24 instead of %s" % str(consume_qty_2))
        consume_qty_3 = product_3_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_3, 12.0, "Consume material quantity of Stone should be 12 instead of %s" % str(consume_qty_3))
        self.assertEqual(len(product_4_consume_moves), 2, "Consume move are not generated proper.")
        for consume_moves in product_4_consume_moves:
            consume_qty_4 = consume_moves.product_uom_qty
            self.assertIn(consume_qty_4, [8.0, 16.0], "Consume material quantity of Stick should be 8 or 16 instead of %s" % str(consume_qty_4))
        self.assertFalse(product_5_consume_moves, "Move should not create for phantom bom")

        # create required lots
        lot_product_2 = self.env['stock.production.lot'].create({'product_id': self.product_2.id})
        lot_product_4 = self.env['stock.production.lot'].create({'product_id': self.product_4.id})

        # refuel stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory For Product C',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_2.id,
                'product_uom_id': self.product_2.uom_id.id,
                'product_qty': 30,
                'prod_lot_id': lot_product_2.id,
                'location_id': self.ref('stock.stock_location_14')
            }), (0, 0, {
                'product_id': self.product_3.id,
                'product_uom_id': self.product_3.uom_id.id,
                'product_qty': 60,
                'location_id': self.ref('stock.stock_location_14')
            }), (0, 0, {
                'product_id': self.product_4.id,
                'product_uom_id': self.product_4.uom_id.id,
                'product_qty': 60,
                'prod_lot_id': lot_product_4.id,
                'location_id': self.ref('stock.stock_location_14')
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # re-assign consume material
        man_order.action_assign()

        # Check production order status after assign.
        self.assertEqual(man_order.availability, 'assigned', "Production order should be in assigned state.")
        # Plan production order.
        man_order.button_plan()

        # check workorders
        # - main bom: Door: 2 operations
        #   operation 1: Cutting
        #   operation 2: Welding, waiting for the previous one
        # - kit bom: Stone Tool: 1 operation
        #   operation 1: Gift Wrapping
        workorders = man_order.workorder_ids
        kit_wo = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_1)
        door_wo_1 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_2)
        door_wo_2 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_3)
        for workorder in workorders:
            self.assertEqual(workorder.workcenter_id, self.workcenter_1, "Workcenter does not match.")
        self.assertEqual(kit_wo.state, 'ready', "Workorder should be in ready state.")
        self.assertEqual(door_wo_1.state, 'ready', "Workorder should be in ready state.")
        self.assertEqual(door_wo_2.state, 'pending', "Workorder should be in pending state.")
        self.assertEqual(kit_wo.duration_expected, 80, "Workorder duration should be 80 instead of %s." % str(kit_wo.duration_expected))
        self.assertEqual(door_wo_1.duration_expected, 20, "Workorder duration should be 20 instead of %s." % str(door_wo_1.duration_expected))
        self.assertEqual(door_wo_2.duration_expected, 20, "Workorder duration should be 20 instead of %s." % str(door_wo_2.duration_expected))

        # subbom: kit for stone tools
        kit_wo.button_start()
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id})
        kit_wo.write({
            'final_lot_id': finished_lot.id,
            'qty_producing': 48
        })

        kit_wo.record_production()

        self.assertEqual(kit_wo.state, 'done', "Workorder should be in done state.")

        # first operation of main bom
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id})
        door_wo_1.write({
            'final_lot_id': finished_lot.id,
            'qty_producing': 48
        })
        door_wo_1.record_production()
        self.assertEqual(door_wo_1.state, 'done', "Workorder should be in done state.")

        # second operation of main bom
        self.assertEqual(door_wo_2.state, 'ready', "Workorder should be in ready state.")
        door_wo_2.record_production()
        self.assertEqual(door_wo_2.state, 'done', "Workorder should be in done state.")

    def test_production_avialability(self):
        """
            Test availability of production order.
        """
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_4).unlink()

        production_2 = self.env['mrp.production'].create({
            'name': 'MO-Test001',
            'product_id': self.product_6.id,
            'product_qty': 5.0,
            'bom_id': self.bom_3.id,
            'product_uom_id': self.product_6.uom_id.id,
        })
        production_2.action_assign()

        # check sub product availability state is waiting
        self.assertEqual(production_2.availability, 'waiting', 'Production order should be availability for waiting state')

        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 2.0,
        })
        inventory_wizard.change_product_qty()

        production_2.action_assign()
        # check sub product availability state is partially available
        self.assertEqual(production_2.availability, 'partially_available', 'Production order should be availability for partially available state')

        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 5.0,
        })
        inventory_wizard.change_product_qty()

        production_2.action_assign()
        # check sub product availability state is assigned
        self.assertEqual(production_2.availability, 'assigned', 'Production order should be availability for assigned state')

    def test_empty_routing(self):
        """ Check what happens when you work with an empty routing"""
        routing = self.env['mrp.routing'].create({'name': 'Routing without operations',
                                        'location_id': self.warehouse_1.wh_input_stock_loc_id.id,})
        self.bom_3.routing_id = routing.id
        production = self.env['mrp.production'].create({'name': 'MO test',
                                           'product_id': self.product_6.id,
                                           'product_qty': 3,
                                           'bom_id': self.bom_3.id,
                                           'product_uom_id': self.product_6.uom_id.id,})
        self.assertEqual(production.routing_id.id, False, 'The routing field should be empty on the mo')
        self.assertEqual(production.move_raw_ids[0].location_id.id, self.warehouse_1.wh_input_stock_loc_id.id, 'Raw moves start location should have altered.')

    def test_multiple_post_inventory(self):
        """ Check the consumed quants of the produced quants when intermediate calls to `post_inventory` during a MO."""

        # create a bom for `custom_laptop` with components that aren't tracked
        unit = self.ref("uom.product_uom_unit")
        custom_laptop = self.env.ref("product.product_product_27")
        custom_laptop.tracking = 'none'
        product_charger = self.env['product.product'].create({
            'name': 'Charger',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit})
        product_keybord = self.env['product.product'].create({
            'name': 'Usb Keybord',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit})
        bom_custom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': custom_laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit,
            'bom_line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_qty': 1,
                'product_uom_id': unit
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_qty': 1,
                'product_uom_id': unit
            })]
        })

        # put the needed products in stock
        source_location_id = self.ref('stock.stock_location_14')
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_uom_id': product_charger.uom_id.id,
                'product_qty': 2,
                'location_id': source_location_id
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_uom_id': product_keybord.uom_id.id,
                'product_qty': 2,
                'location_id': source_location_id
            })]
        })
        inventory.action_validate()

        # create a mo for this bom
        mo_custom_laptop = self.env['mrp.production'].create({
            'product_id': custom_laptop.id,
            'product_qty': 2,
            'product_uom_id': unit,
            'bom_id': bom_custom_laptop.id
        })
        mo_custom_laptop.action_assign()
        self.assertEqual(mo_custom_laptop.availability, 'assigned')

        # produce one item, call `post_inventory`
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.product_qty = 1.00
        custom_laptop_produce = produce_form.save()
        custom_laptop_produce.do_produce()
        mo_custom_laptop.post_inventory()

        # check the consumed quants of the produced quant
        first_move = mo_custom_laptop.move_finished_ids.filtered(lambda mo: mo.state == 'done')

        second_move = mo_custom_laptop.move_finished_ids.filtered(lambda mo: mo.state == 'confirmed')

        # produce the second item, call `post_inventory`
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.product_qty = 1.00
        custom_laptop_produce = produce_form.save()
        custom_laptop_produce.do_produce()
        mo_custom_laptop.post_inventory()

    def test_rounding(self):
        """ In previous versions we had rounding and efficiency fields.  We check if we can still do the same, but with only the rounding on the UoM"""
        self.product_6.uom_id.rounding = 1.0
        bom_eff = self.env['mrp.bom'].create({'product_id': self.product_6.id,
                                    'product_tmpl_id': self.product_6.product_tmpl_id.id,
                                    'product_qty': 1,
                                    'product_uom_id': self.product_6.uom_id.id,
                                    'type': 'normal',
                                    'bom_line_ids': [
                                        (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                                        (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
                                        ]})
        production = self.env['mrp.production'].create({'name': 'MO efficiency test',
                                           'product_id': self.product_6.id,
                                           'product_qty': 20,
                                           'bom_id': bom_eff.id,
                                           'product_uom_id': self.product_6.uom_id.id,})
        #Check the production order has the right quantities
        self.assertEqual(production.move_raw_ids[0].product_qty, 41, 'The quantity should be rounded up')
        self.assertEqual(production.move_raw_ids[1].product_qty, 84, 'The quantity should be rounded up')

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production.id,
            'active_ids': [production.id],
        }))
        produce_form.product_qty = 8
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        self.assertEqual(production.move_raw_ids[0].quantity_done, 16, 'Should use half-up rounding when producing')
        self.assertEqual(production.move_raw_ids[1].quantity_done, 34, 'Should use half-up rounding when producing')

    def test_product_produce_1(self):
        """ Check that no produce line are created when the consumed products are not tracked """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = produce_form.save()
        product_produce.do_produce()

        self.assertEqual(len(product_produce.produce_line_ids), 2, 'You should have produce lines even the consumed products are not tracked.')

    def test_product_produce_2(self):
        """ Check that line are created when the consumed products are
        tracked by serial and the lot proposed are correct. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='serial', qty_base_1=1, qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_p1_1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        lot_p1_2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_2)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = produce_form.save()

        self.assertEqual(len(product_produce.produce_line_ids), 3, 'You should have 3 produce lines. One for each serial to consume')
        product_produce.product_qty = 1
        produce_line_1 = product_produce.produce_line_ids[0]
        produce_line_1.qty_done = 1
        remaining_lot = (lot_p1_1 | lot_p1_2) - produce_line_1.lot_id
        product_produce.do_produce()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = produce_form.save()
        self.assertEqual(len(product_produce.produce_line_ids), 2, 'You should have 2 produce lines since one has already be consumed.')
        for line in product_produce.produce_line_ids.filtered(lambda x: x.lot_id):
            self.assertEqual(line.lot_id, remaining_lot, 'Wrong lot proposed.')

    def test_product_produce_3(self):
        """ Check that line are created when the consumed products are
        tracked by serial and the lot proposed are correct. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.env.ref('stock.stock_location_components')
        self.stock_shelf_2 = self.env.ref('stock.stock_location_14')
        mo, _, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot', qty_base_1=10, qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        first_lot_for_p1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        second_lot_for_p1 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        final_product_lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 8, lot_id=second_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.product_qty = 1.0
        product_produce = produce_form.save()
        product_produce.lot_id = final_product_lot.id
        # product 1 lot 1 shelf1
        # product 1 lot 1 shelf2
        # product 1 lot 2
        self.assertEqual(len(product_produce.produce_line_ids), 4, 'You should have 4 produce lines. lot 1 shelf_1, lot 1 shelf_2, lot2 and for product which have tracking None')

        for produce_line in product_produce.produce_line_ids:
            produce_line.qty_done = produce_line.qty_to_consume + 1
        product_produce.do_produce()

        move_1 = mo.move_raw_ids.filtered(lambda m: m.product_id == p1)
        # qty_done/product_uom_qty lot
        # 3/3 lot 1 shelf 1
        # 1/1 lot 1 shelf 2
        # 2/2 lot 1 shelf 2
        # 2/0 lot 1 other
        # 5/4 lot 2
        ml_to_shelf_1 = move_1.move_line_ids.filtered(lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.stock_shelf_1)
        ml_to_shelf_2 = move_1.move_line_ids.filtered(lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.stock_shelf_2)

        self.assertEqual(sum(ml_to_shelf_1.mapped('qty_done')), 3.0, '3 units should be took from shelf1 as reserved.')
        self.assertEqual(sum(ml_to_shelf_2.mapped('qty_done')), 3.0, '3 units should be took from shelf2 as reserved.')
        self.assertEqual(move_1.quantity_done, 13, 'You should have used the tem units.')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_4(self):
        """ Possibility to produce with a given raw material in multiple locations. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.env.ref('stock.stock_location_components')
        self.stock_shelf_2 = self.env.ref('stock.stock_location_14')
        mo, _, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=5)

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 2)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 3)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1)

        mo.action_assign()
        ml_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1).mapped('move_line_ids')
        ml_p2 = mo.move_raw_ids.filtered(lambda x: x.product_id == p2).mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 2)
        self.assertEqual(len(ml_p2), 1)

        # Add some quantity already done to force an extra move line to be created
        ml_p1[0].qty_done = 1.0

        # Produce baby!
        product_produce = self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }).create({
            'product_qty': 1.0,
        })
        product_produce._onchange_product_qty()
        product_produce.do_produce()

        ml_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1).mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 4)
        for ml in ml_p1:
            self.assertIn(ml.qty_done, [1.0, 2.0], 'Quantity done should be 1.0, 2.0 or 3.0')
        self.assertEqual(sum(ml_p1.mapped('qty_done')), 6.0, 'Total qty consumed should be 6.0')
        self.assertEqual(sum(ml_p1.mapped('product_uom_qty')), 5.0, 'Total qty reserved should be 5.0')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_5(self):
        """ Build 5 final products with different consumed lots,
        then edit the finished quantity and update the Manufacturing
        order quantity. Then check if the produced quantity do not
        change and it is possible to close the MO.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        lot_2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_2)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        produce_wizard = self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }).create({
            'product_qty': 5.0,
        })

        for produce_line in produce_wizard.produce_line_ids:
            produce_line.qty_done = produce_line.qty_to_consume
        produce_wizard.do_produce()

        mo.move_finished_ids.move_line_ids.qty_done -= 1
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 4,
        })
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity_done, 20, 'Update the produce quantity should not impact already produced quantity.')
        mo.button_mark_done()

    def test_product_produce_uom(self):
        plastic_laminate = self.env.ref('mrp.product_product_plastic_laminate')
        bom = self.env.ref('mrp.mrp_bom_plastic_laminate')
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')

        plastic_laminate.tracking = 'serial'

        mo = self.env['mrp.production'].create({
            'name': 'Dozen Plastic Laminate',
            'product_id': plastic_laminate.id,
            'product_uom_id': dozen.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })

        final_product_lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': plastic_laminate.id,
        })

        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.product_qty, 12, '12 units should be reserved.')

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.lot_id = final_product_lot
        product_produce = produce_form.save()
        self.assertEqual(product_produce.product_qty, 1)
        self.assertEqual(product_produce.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')
        product_produce.lot_id = final_product_lot.id

        product_produce.do_produce()
        move_line_raw = mo.move_raw_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_raw.qty_done, 1)
        self.assertEqual(move_line_raw.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

        move_line_finished = mo.move_finished_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_finished.qty_done, 1)
        self.assertEqual(move_line_finished.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')
