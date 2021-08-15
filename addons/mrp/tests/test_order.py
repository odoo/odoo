# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from datetime import datetime, timedelta

from odoo.fields import Datetime as Dt
from odoo.exceptions import UserError
from odoo.addons.mrp.tests.common import TestMrpCommon

class TestMrpOrder(TestMrpCommon):

    def test_access_rights_manager(self):
        """ Checks an MRP manager can create, confirm and cancel a manufacturing order. """
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_manager))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_access_rights_user(self):
        """ Checks an MRP user can create, confirm and cancel a manufacturing order. """
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_basic(self):
        """ Checks a basic manufacturing order: no routing (thus no workorders), no lot and
        consume strictly what's needed. """
        self.product_1.type = 'product'
        self.product_2.type = 'product'
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
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
        inventory.action_start()
        inventory.action_validate()

        test_date_planned = Dt.now() - timedelta(days=1)
        test_quantity = 3.0
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.bom_id = self.bom_1
        man_order_form.product_uom_id = self.product_4.uom_id
        man_order_form.product_qty = test_quantity
        man_order_form.date_planned_start = test_date_planned
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()

        self.assertEqual(man_order.state, 'draft', "Production order should be in draft state.")
        man_order.action_confirm()
        self.assertEqual(man_order.state, 'confirmed', "Production order should be in confirmed state.")

        # check production move
        production_move = man_order.move_finished_ids
        self.assertAlmostEqual(production_move.date, test_date_planned + timedelta(hours=1), delta=timedelta(seconds=10))
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

        # produce product
        mo_form = Form(man_order)
        mo_form.qty_producing = 2.0
        man_order = mo_form.save()

        action = man_order.button_mark_done()
        self.assertEqual(man_order.state, 'progress', "Production order should be open a backorder wizard, then not done yet.")

        quantity_issues = man_order._get_consumption_issues()
        action = man_order._action_generate_consumption_wizard(quantity_issues)
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_close_mo()
        self.assertEqual(man_order.state, 'done', "Production order should be done.")

        # check that copy handles moves correctly
        mo_copy = man_order.copy()
        self.assertEqual(mo_copy.state, 'draft', "Copied production order should be draft.")
        self.assertEqual(len(mo_copy.move_raw_ids), 2, "Incorrect number of component moves [i.e. no 0 qty moves should be copied].")
        self.assertEqual(len(mo_copy.move_finished_ids), 1, "Incorrect number of moves for products to produce [i.e. cancelled moves should not be copied")
        self.assertEqual(mo_copy.move_finished_ids.product_uom_qty, 2, "Incorrect qty of products to produce")

    def test_production_avialability(self):
        """ Checks the availability of a production order through mutliple calls to `action_assign`.
        """
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_4).unlink()
        self.bom_3.ready_to_produce = 'all_available'

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_3
        production_form.product_qty = 5.0
        production_form.product_uom_id = self.product_6.uom_id
        production_2 = production_form.save()

        production_2.action_confirm()
        production_2.action_assign()

        # check sub product availability state is waiting
        self.assertEqual(production_2.reservation_state, 'confirmed', 'Production order should be availability for waiting state')

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 2.0,
            'location_id': self.stock_location_14.id
        })

        production_2.action_assign()
        # check sub product availability state is partially available
        self.assertEqual(production_2.reservation_state, 'confirmed', 'Production order should be availability for partially available state')

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 5.0,
            'location_id': self.stock_location_14.id
        })

        production_2.action_assign()
        # check sub product availability state is assigned
        self.assertEqual(production_2.reservation_state, 'assigned', 'Production order should be availability for assigned state')

    def test_split_move_line(self):
        """ Consume more component quantity than the initial demand.
        It should create extra move and share the quantity between the two stock
        moves """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_base_1=10, qty_final=1, qty_base_2=1)
        mo.action_assign()
        # check is_quantity_done_editable
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.qty_done = 2
        details_operation_form.save()
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.qty_done = 11
        details_operation_form.save()

        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 2)
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.mapped('qty_done'), [2])
        self.assertEqual(mo.move_raw_ids[1].move_line_ids.mapped('qty_done'), [11])
        self.assertEqual(mo.move_raw_ids[0].quantity_done, 2)
        self.assertEqual(mo.move_raw_ids[1].quantity_done, 11)
        mo.button_mark_done()
        self.assertEqual(len(mo.move_raw_ids), 4)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 4)
        self.assertEqual(mo.move_raw_ids.mapped('quantity_done'), [1, 10, 1, 1])
        self.assertEqual(mo.move_raw_ids.mapped('move_line_ids.qty_done'), [1, 10, 1, 1])

    def test_update_quantity_1(self):
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
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_2)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = lot_1
            ml.qty_done = 20
        details_operation_form.save()
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 4,
        })
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity_done, 20, 'Update the produce quantity should not impact already produced quantity.')
        self.assertEqual(mo.move_finished_ids.product_uom_qty, 4)
        mo.button_mark_done()

    def test_update_quantity_2(self):
        """ Build 5 final products with different consumed lots,
        then edit the finished quantity and update the Manufacturing
        order quantity. Then check if the produced quantity do not
        change and it is possible to close the MO.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=3)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()

        mo._post_inventory()

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 5,
        })
        update_quantity_wizard.change_prod_qty()
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        mo.button_mark_done()

        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).mapped('quantity_done')), 20)
        self.assertEqual(sum(mo.move_finished_ids.mapped('quantity_done')), 5)

    def test_update_quantity_3(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ],
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ]
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 90)
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 165)

    def test_update_quantity_4(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = 'OP1'
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 40)
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 90)

    def test_qty_producing(self):
        """Qty producing should be the qty remain to produce, instead of 0"""
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.00}),
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 5
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = 'OP1'
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        production.workorder_ids[0].button_start()
        self.assertEqual(production.workorder_ids.qty_producing, 5, "Wrong quantity is suggested to produce.")

    def test_update_quantity_5(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 3}),
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        production.action_assign()
        production_form = Form(production)
        # change the quantity producing and the initial demand
        # in the same transaction
        production_form.qty_producing = 10
        with production_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty = 2
        production = production_form.save()
        production.button_mark_done()

    def test_update_plan_date(self):
        """Editing the scheduled date after planning the MO should unplan the MO, and adjust the date on the stock moves"""
        planned_date = datetime(2023, 5, 15, 9, 0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 1
        mo_form.date_planned_start = planned_date
        mo = mo_form.save()
        self.assertEqual(mo.move_finished_ids[0].date, datetime(2023, 5, 15, 10, 0))
        mo.action_confirm()
        mo.button_plan()
        with Form(mo) as frm:
            frm.date_planned_start = datetime(2024, 5, 15, 9, 0)
        self.assertEqual(mo.move_finished_ids[0].date, datetime(2024, 5, 15, 10, 0))

    def test_rounding(self):
        """ Checks we round up when bringing goods to produce and round half-up when producing.
        This implementation allows to implement an efficiency notion (see rev 347f140fe63612ee05e).
        """
        self.product_6.uom_id.rounding = 1.0
        bom_eff = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ]
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom_eff
        production_form.product_qty = 20
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        #Check the production order has the right quantities
        self.assertEqual(production.move_raw_ids[0].product_qty, 41, 'The quantity should be rounded up')
        self.assertEqual(production.move_raw_ids[1].product_qty, 84, 'The quantity should be rounded up')

        # produce product
        mo_form = Form(production)
        mo_form.qty_producing = 8
        production = mo_form.save()
        self.assertEqual(production.move_raw_ids[0].quantity_done, 16, 'Should use half-up rounding when producing')
        self.assertEqual(production.move_raw_ids[1].quantity_done, 34, 'Should use half-up rounding when producing')

    def test_product_produce_1(self):
        """ Checks the production wizard contains lines even for untracked products. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        # change the quantity done in one line
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.qty_done = 1
        details_operation_form.save()

        # change the quantity producing
        mo_form = Form(mo)
        mo_form.qty_producing = 3

        # check than all quantities are update correctly
        self.assertEqual(mo_form.move_raw_ids._records[0]['product_uom_qty'], 5, "Wrong quantity to consume")
        self.assertEqual(mo_form.move_raw_ids._records[0]['quantity_done'], 3, "Wrong quantity done")
        self.assertEqual(mo_form.move_raw_ids._records[1]['product_uom_qty'], 20, "Wrong quantity to consume")
        self.assertEqual(mo_form.move_raw_ids._records[1]['quantity_done'], 12, "Wrong quantity done")

    def test_product_produce_2(self):
        """ Checks that, for a BOM where one of the components is tracked by serial number and the
        other is not tracked, when creating a manufacturing order for two finished products and
        reserving, the produce wizards proposes the corrects lines when producing one at a time.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='serial', qty_base_1=1, qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_p1_1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })
        lot_p1_2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_2)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 3, 'You should have 3 stock move lines. One for each serial to consume and for the untracked product.')
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        # get the proposed lot
        details_operation_form = Form(mo.move_raw_ids.filtered(lambda move: move.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        self.assertEqual(len(details_operation_form.move_line_ids), 2)
        with details_operation_form.move_line_ids.edit(0) as ml:
            consumed_lots = ml.lot_id
            ml.qty_done = 1
        details_operation_form.save()

        remaining_lot = (lot_p1_1 | lot_p1_2) - consumed_lots
        remaining_lot.ensure_one()
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        # Check MO backorder
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]

        mo_form = Form(mo_backorder)
        mo_form.qty_producing = 1
        mo_backorder = mo_form.save()
        details_operation_form = Form(mo_backorder.move_raw_ids.filtered(lambda move: move.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        self.assertEqual(len(details_operation_form.move_line_ids), 1)
        with details_operation_form.move_line_ids.edit(0) as ml:
            self.assertEqual(ml.lot_id, remaining_lot)

    def test_product_produce_3(self):
        """ Checks that, for a BOM where one of the components is tracked by lot and the other is
        not tracked, when creating a manufacturing order for 1 finished product and reserving, the
        reserved lines are displayed. Then, over-consume by creating new line.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.stock_location_components

        self.stock_shelf_2 = self.stock_location_14
        mo, _, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot', qty_base_1=10, qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        first_lot_for_p1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })
        second_lot_for_p1 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })

        final_product_lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 8, lot_id=second_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo_form.lot_producing_id = final_product_lot
        mo = mo_form.save()
        # p2
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as line:
            line.qty_done = line.product_uom_qty
        with details_operation_form.move_line_ids.new() as line:
            line.qty_done = 1
        details_operation_form.save()

        # p1
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        for i in range(len(details_operation_form.move_line_ids)):
            # reservation in shelf1: 3 lot1, shelf2: 3 lot1, stock: 4 lot2
            with details_operation_form.move_line_ids.edit(i) as line:
                line.qty_done = line.product_uom_qty
        with details_operation_form.move_line_ids.new() as line:
            line.qty_done = 2
            line.lot_id = first_lot_for_p1
        with details_operation_form.move_line_ids.new() as line:
            line.qty_done = 1
            line.lot_id = second_lot_for_p1
        details_operation_form.save()

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
        # FIXME sle: how is it possible to consume before producing in the interface?
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.stock_location_components
        self.stock_shelf_2 = self.stock_location_14
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
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        m_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1)
        ml_p1 = m_p1.mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 2)
        self.assertEqual(sorted(ml_p1.mapped('qty_done')), [2.0, 3.0], 'Quantity done should be 1.0, 2.0 or 3.0')
        self.assertEqual(m_p1.quantity_done, 5.0, 'Total qty done should be 6.0')
        self.assertEqual(sum(ml_p1.mapped('product_uom_qty')), 5.0, 'Total qty reserved should be 5.0')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_6(self):
        """ Plan 5 finished products, reserve and produce 3. Post the current production.
        Simulate an unlock and edit and, on the opened moves, set the consumed quantity
        to 3. Now, try to update the quantity to mo2 to 3. It should fail since there
        are consumed quantities. Unlock and edit, remove the consumed quantities and
        update the quantity to produce to 3."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        mo = mo_form.save()

        mo._post_inventory()
        self.assertEqual(len(mo.move_raw_ids), 4)

        mo.move_raw_ids.filtered(lambda m: m.state != 'done')[0].quantity_done = 3

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 3,
        })

        mo.move_raw_ids.filtered(lambda m: m.state != 'done')[0].quantity_done = 0
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(len(mo.move_raw_ids), 2)

        mo.button_mark_done()
        self.assertTrue(all(s == 'done' for s in mo.move_raw_ids.mapped('state')))
        self.assertEqual(sum(mo.move_raw_ids.mapped('move_line_ids.product_uom_qty')), 0)

    def test_consumption_strict_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='strict', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 1
        details_operation_form.save()
        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'to_close')
        consumption_issues = mo._get_consumption_issues()
        action = mo._action_generate_consumption_wizard(consumption_issues)
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4)
        # Force the warning (as a manager)
        warning.action_confirm()
        self.assertEqual(mo.state, 'done')

    def test_consumption_warning_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='warning', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'to_close')

        consumption_issues = mo._get_consumption_issues()
        action = mo._action_generate_consumption_wizard(consumption_issues)
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4)
        # Force the warning (as a manager or employee)
        warning.action_confirm()
        self.assertEqual(mo.state, 'done')

    def test_consumption_flexible_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='flexible', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_consumption_flexible_2(self):
        """ Checks the constraints of a strict BOM only apply to the product of the BoM. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='flexible', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        add_product = self.env['product.product'].create({
            'name': 'additional',
            'type': 'product',
        })
        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = add_product
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_product_produce_9(self):
        """ Checks the production wizard contains lines even for untracked products. """
        serial = self.env['product.product'].create({
            'name': 'S1',
            'tracking': 'serial',
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        mo_form = Form(mo)

        # change the quantity done in one line
        with self.assertRaises(AssertionError):
            with mo_form.move_raw_ids.new() as move:
                move.product_id = serial
                move.quantity_done = 2
            mo_form.save()

    def test_product_produce_10(self):
        """ Produce byproduct with serial, lot and not tracked.
        byproduct1 serial 1.0
        byproduct2 lot    2.0
        byproduct3 none   1.0 dozen
        Check qty producing update and moves finished values.
        """
        dozen = self.env.ref('uom.product_uom_dozen')
        self.byproduct1 = self.env['product.product'].create({
            'name': 'Byproduct 1',
            'type': 'product',
            'tracking': 'serial'
        })
        self.serial_1 = self.env['stock.production.lot'].create({
            'product_id': self.byproduct1.id,
            'name': 'serial 1',
            'company_id': self.env.company.id,
        })
        self.serial_2 = self.env['stock.production.lot'].create({
            'product_id': self.byproduct1.id,
            'name': 'serial 2',
            'company_id': self.env.company.id,
        })

        self.byproduct2 = self.env['product.product'].create({
            'name': 'Byproduct 2',
            'type': 'product',
            'tracking': 'lot',
        })
        self.lot_1 = self.env['stock.production.lot'].create({
            'product_id': self.byproduct2.id,
            'name': 'Lot 1',
            'company_id': self.env.company.id,
        })
        self.lot_2 = self.env['stock.production.lot'].create({
            'product_id': self.byproduct2.id,
            'name': 'Lot 2',
            'company_id': self.env.company.id,
        })

        self.byproduct3 = self.env['product.product'].create({
            'name': 'Byproduct 3',
            'type': 'product',
            'tracking': 'none',
        })

        with Form(self.bom_1) as bom:
            bom.product_qty = 1.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct1
                bp.product_qty = 1.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct2
                bp.product_qty = 2.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct3
                bp.product_qty = 2.0
                bp.product_uom_id = dozen

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()

        mo.action_confirm()
        move_byproduct_1 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity_done, 0)
        self.assertEqual(len(move_byproduct_1.move_line_ids), 0)

        move_byproduct_2 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity_done, 0)
        self.assertEqual(len(move_byproduct_2.move_line_ids), 0)

        move_byproduct_3 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity_done, 0)
        self.assertEqual(move_byproduct_3.product_uom, dozen)
        self.assertEqual(len(move_byproduct_3.move_line_ids), 0)

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        move_byproduct_1 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity_done, 0)

        move_byproduct_2 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity_done, 0)

        move_byproduct_3 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity_done, 2.0)
        self.assertEqual(move_byproduct_3.product_uom, dozen)

        details_operation_form = Form(move_byproduct_1, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.serial_1
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_2, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.lot_1
            ml.qty_done = 2
        details_operation_form.save()
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo2 = mo.procurement_group_id.mrp_production_ids[-1]

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()

        move_byproduct_1 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 1.0)
        self.assertEqual(move_byproduct_1.quantity_done, 0)

        move_byproduct_2 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_2.quantity_done, 0)

        move_byproduct_3 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_3.quantity_done, 2.0)
        self.assertEqual(move_byproduct_3.product_uom, dozen)

        details_operation_form = Form(move_byproduct_1, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.serial_2
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_2, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.lot_2
            ml.qty_done = 2
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_3, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.qty_done = 3
        details_operation_form.save()

        mo2.button_mark_done()
        move_lines_byproduct_1 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1).mapped('move_line_ids')
        move_lines_byproduct_2 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2).mapped('move_line_ids')
        move_lines_byproduct_3 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3).mapped('move_line_ids')
        self.assertEqual(move_lines_byproduct_1.filtered(lambda ml: ml.lot_id == self.serial_1).qty_done, 1.0)
        self.assertEqual(move_lines_byproduct_1.filtered(lambda ml: ml.lot_id == self.serial_2).qty_done, 1.0)
        self.assertEqual(move_lines_byproduct_2.filtered(lambda ml: ml.lot_id == self.lot_1).qty_done, 2.0)
        self.assertEqual(move_lines_byproduct_2.filtered(lambda ml: ml.lot_id == self.lot_2).qty_done, 2.0)
        self.assertEqual(sum(move_lines_byproduct_3.mapped('qty_done')), 5.0)
        self.assertEqual(move_lines_byproduct_3.mapped('product_uom_id'), dozen)

    def test_product_produce_11(self):
        """ Checks that, for a BOM with two components, when creating a manufacturing order for one
        finished products and without reserving, the produce wizards proposes the corrects lines
        even if we change the quantity to produce multiple times.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1)

        mo.bom_id.consumption = 'flexible'  # Because we'll over-consume with a product not defined in the BOM
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        self.assertEqual(sum([x['quantity_done'] for x in mo_form.move_raw_ids._records]), 15, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.mapped('reserved_availability')), 5, 'Update the produce quantity should not change the components reserved quantity.')
        mo_form = Form(mo)
        mo_form.qty_producing = 4
        self.assertEqual(sum([x['quantity_done'] for x in mo_form.move_raw_ids._records]), 20, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.mapped('reserved_availability')), 5, 'Update the produce quantity should not change the components reserved quantity.')
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        self.assertEqual(sum([x['quantity_done'] for x in mo_form.move_raw_ids._records]), 5, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.mapped('reserved_availability')), 5, 'Update the produce quantity should not change the components reserved quantity.')
        # try adding another product that doesn't belong to the BoM
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.product_4
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 10
        details_operation_form.save()
        # Check that this new product is not updated by qty_producing
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        for move in mo_form.move_raw_ids._records:
            if move['product_id'] == self.product_4.id:
                self.assertEqual(move['quantity_done'], 10)
                break
        mo = mo_form.save()
        mo.button_mark_done()

    def test_product_produce_duplicate_1(self):
        """ produce a finished product tracked by serial number 2 times with the
        same SN. Check that an error is raised the second time"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=1, qty_base_1=1,)

        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        mo1.action_generate_serial()
        sn = mo1.lot_producing_id
        mo1.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        with self.assertLogs(level="WARNING"):
            mo_form.lot_producing_id = sn
        mo2 = mo_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_2(self):
        """ produce a finished product with component tracked by serial number 2
        times with the same SN. Check that an error is raised the second time"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_base_2='serial', qty_final=1, qty_base_1=1,)
        sn = self.env['stock.production.lot'].create({
            'name': 'sn used twice',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(mo1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(mo2.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_3(self):
        """ produce a finished product with by-product tracked by serial number 2
        times with the same SN. Check that an error is raised the second time"""
        finished_product = self.env['product.product'].create({'name': 'finished product'})
        byproduct = self.env['product.product'].create({'name': 'byproduct', 'tracking': 'serial'})
        component = self.env['product.product'].create({'name': 'component'})
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': finished_product.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ],
            'byproduct_ids': [
                (0, 0, {'product_id': byproduct.id, 'product_qty': 1, 'product_uom_id': byproduct.uom_id.id})
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        sn = self.env['stock.production.lot'].create({
            'name': 'sn used twice',
            'product_id': byproduct.id,
            'company_id': self.env.company.id,
        })

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        move_byproduct = mo.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id)
        details_operation_form = Form(move_byproduct, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        move_byproduct = mo2.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id)
        details_operation_form = Form(move_byproduct, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_4(self):
        """ Consuming the same serial number two times should not give an error if
        a repair order of the first production has been made before the second one"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_base_2='serial', qty_final=1, qty_base_1=1,)
        sn = self.env['stock.production.lot'].create({
            'name': 'sn used twice',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(mo1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.button_mark_done()

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.product_id = p_final
        unbuild_form.bom_id = bom
        unbuild_form.product_qty = 1
        unbuild_form.mo_id = mo1
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(mo2.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo2.button_mark_done()

    def test_product_produce_12(self):
        """ Checks that, the production is robust against deletion of finished move."""

        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        # remove the finished move from the available to be updated
        mo.move_finished_ids._action_done()
        mo.button_mark_done()

    def test_product_produce_13(self):
        """ Check that the production cannot be completed without any consumption."""
        product = self.env['product.product'].create({
            'name': 'Product no BoM',
            'type': 'product',
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo = mo_form.save()
        move = self.env['stock.move'].create({
            'name': 'mrp_move',
            'product_id': self.product_2.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'production_id': mo.id,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 0,
            'quantity_done': 0,
        })
        mo.move_raw_ids |= move
        mo.action_confirm()

        mo.qty_producing = 1
        # can't produce without any consumption (i.e. components w/ 0 consumed)
        with self.assertRaises(UserError):
            mo.button_mark_done()

        mo.move_raw_ids.quantity_done = 1
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_product_produce_uom(self):
        """ Produce a finished product tracked by serial number. Set another
        UoM on the bom. The produce wizard should keep the UoM of the product (unit)
        and quantity = 1."""
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')
        plastic_laminate = self.env['product.product'].create({
            'name': 'Plastic Laminate',
            'type': 'product',
            'uom_id': unit.id,
            'uom_po_id': unit.id,
            'tracking': 'serial',
        })
        ply_veneer = self.env['product.product'].create({
            'name': 'Ply Veneer',
            'type': 'product',
            'uom_id': unit.id,
            'uom_po_id': unit.id,
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': plastic_laminate.product_tmpl_id.id,
            'product_uom_id': unit.id,
            'sequence': 1,
            'bom_line_ids': [(0, 0, {
                'product_id': ply_veneer.id,
                'product_qty': 1,
                'product_uom_id': unit.id,
                'sequence': 1,
            })]
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = plastic_laminate
        mo_form.bom_id = bom
        mo_form.product_uom_id = dozen
        mo_form.product_qty = 1
        mo = mo_form.save()

        final_product_lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': plastic_laminate.id,
            'company_id': self.env.company.id,
        })

        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.product_qty, 12, '12 units should be reserved.')

        # produce product
        mo_form = Form(mo)
        mo_form.qty_producing = 1/12.0
        mo_form.lot_producing_id = final_product_lot
        mo = mo_form.save()

        move_line_raw = mo.move_raw_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_raw.qty_done, 1)
        self.assertEqual(move_line_raw.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

        mo._post_inventory()
        move_line_finished = mo.move_finished_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_finished.qty_done, 1)
        self.assertEqual(move_line_finished.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

    def test_product_type_service_1(self):
        # Create finished product
        finished_product = self.env['product.product'].create({
            'name': 'Geyser',
            'type': 'product',
        })

        # Create service type product
        product_raw = self.env['product.product'].create({
            'name': 'raw Geyser',
            'type': 'service',
        })

        # Create bom for finish product
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': product_raw.id})]
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.env.ref('uom.product_uom_unit')
        mo_form.product_qty = 1
        mo = mo_form.save()

        # Check Mo is created or not
        self.assertTrue(mo, "Mo is created")

    def test_immediate_validate_1(self):
        """ In a production with a single available move raw, clicking on mark as done without filling any
        quantities should open a wizard asking to process all the reservation (so, the whole move).
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        res_dict = mo.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['done', 'done'])
        self.assertEqual(mo.move_raw_ids.mapped('quantity_done'), [1, 1])
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity_done, 1)

    def test_immediate_validate_2(self):
        """ In a production with a single available move raw, clicking on mark as done after filling quantity
        for a stock move only will trigger an error as qty_producing is left to 0."""
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.qty_done = 1
        details_operation_form.save()
        with self.assertRaises(UserError):
            res_dict = mo.button_mark_done()

    def test_immediate_validate_3(self):
        """ In a production with a serial number tracked product. Check that the immediate production only creates
        one unit of finished product. Test with reservation."""
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=2, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        action = mo.button_mark_done()
        self.assertEqual(action.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        action = wizard.process()
        self.assertEqual(action.get('res_model'), 'mrp.production.backorder')
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        action = wizard.action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped('quantity_done'), [1, 1])
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped('product_uom_qty'), [1, 1])

    def test_immediate_validate_4(self):
        """ In a production with a serial number tracked product. Check that the immediate production only creates
        one unit of finished product. Test without reservation."""
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=2, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        action = mo.button_mark_done()
        self.assertEqual(action.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        action = wizard.process()
        self.assertEqual(action.get('res_model'), 'mrp.production.backorder')
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        action = wizard.action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped('quantity_done'), [1, 1])
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped('product_uom_qty'), [1, 1])

    def test_immediate_validate_5(self):
        """Validate three productions at once."""
        mo1, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo1.action_assign()
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = p_final
        mo2_form.bom_id = bom
        mo2_form.product_qty = 1
        mo2 = mo2_form.save()
        mo2.action_confirm()
        mo2.action_assign()
        mo3_form = Form(self.env['mrp.production'])
        mo3_form.product_id = p_final
        mo3_form.bom_id = bom
        mo3_form.product_qty = 1
        mo3 = mo3_form.save()
        mo3.action_confirm()
        mo3.action_assign()
        mos = mo1 | mo2 | mo3
        res_dict = mos.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(mos.move_raw_ids.mapped('state'), ['done'] * 6)
        self.assertEqual(mos.move_raw_ids.mapped('quantity_done'), [1] * 6)
        self.assertEqual(mos.move_finished_ids.mapped('state'), ['done'] * 3)
        self.assertEqual(mos.move_finished_ids.mapped('quantity_done'), [1] * 3)

    def test_immediate_validate_6(self):
        """In a production for a tracked product, clicking on mark as done without filling any quantities should
        pop up the immediate transfer wizard. Processing should choose a new lot for the finished product. """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1, tracking_final='lot')
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        res_dict = mo.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['done'] * 2)
        self.assertEqual(mo.move_raw_ids.mapped('quantity_done'), [1] * 2)
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity_done, 1)
        self.assertTrue(mo.move_finished_ids.move_line_ids.lot_id != False)

    def test_immediate_validate_uom(self):
        """In a production with a different uom than the finished product one, the
        immediate production wizard should fill the correct quantities. """
        p_final = self.env['product.product'].create({
            'name': 'final',
            'type': 'product',
        })
        component = self.env['product.product'].create({
            'name': 'component',
            'type': 'product',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': p_final.id,
            'product_tmpl_id': p_final.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1})]
        })
        self.env['stock.quant']._update_available_quantity(component, self.stock_location_components, 25.0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        res_dict = mo.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(mo.move_raw_ids.state, 'done')
        self.assertEqual(mo.move_raw_ids.quantity_done, 12)
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity_done, 1)
        self.assertEqual(component.qty_available, 13)

    def test_immediate_validate_uom_2(self):
        """The rounding precision of a component should be based on the UoM used in the MO for this component,
        not on the produced product's UoM nor the default UoM of the component"""
        uom_units = self.env['ir.model.data'].xmlid_to_object('uom.product_uom_unit')
        uom_L = self.env['ir.model.data'].xmlid_to_object('uom.product_uom_litre')
        uom_cL = self.env['uom.uom'].create({
            'name': 'cL',
            'category_id': uom_L.category_id.id,
            'uom_type': 'smaller',
            'factor': 100,
            'rounding': 1,
        })
        uom_units.rounding = 1
        uom_L.rounding = 0.01

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'uom_id': uom_units.id,
        })
        consumable_component = self.env['product.product'].create({
            'name': 'Consumable Component',
            'type': 'consu',
            'uom_id': uom_cL.id,
            'uom_po_id': uom_cL.id,
        })
        storable_component = self.env['product.product'].create({
            'name': 'Storable Component',
            'type': 'product',
            'uom_id': uom_cL.id,
            'uom_po_id': uom_cL.id,
        })
        self.env['stock.quant']._update_available_quantity(storable_component, self.env.ref('stock.stock_location_stock'), 100)

        for component in [consumable_component, storable_component]:
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': product.product_tmpl_id.id,
                'bom_line_ids': [(0, 0, {
                    'product_id': component.id,
                    'product_qty': 0.2,
                    'product_uom_id': uom_L.id,
                })],
            })

            mo_form = Form(self.env['mrp.production'])
            mo_form.bom_id = bom
            mo = mo_form.save()
            mo.action_confirm()
            action = mo.button_mark_done()
            self.assertEqual(action.get('res_model'), 'mrp.immediate.production')
            wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
            action = wizard.process()

            self.assertEqual(mo.move_raw_ids.product_uom_qty, 0.2)
            self.assertEqual(mo.move_raw_ids.quantity_done, 0.2)

    def test_copy(self):
        """ Check that copying a done production, create all the stock moves"""
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        mo_copy = mo.copy()
        self.assertTrue(mo_copy.move_raw_ids)
        self.assertTrue(mo_copy.move_finished_ids)
        mo_copy.action_confirm()
        mo_form = Form(mo_copy)
        mo_form.qty_producing = 1
        mo_copy = mo_form.save()
        mo_copy.button_mark_done()
        self.assertEqual(mo_copy.state, 'done')

    def test_product_produce_different_uom(self):
        """ Check that for products tracked by lots,
        with component product UOM different from UOM used in the BOM,
        we do not create a new move line due to extra reserved quantity
        caused by decimal rounding conversions.
        """

        # the overall decimal accuracy is set to 3 digits
        precision = self.env.ref('product.decimal_product_uom')
        precision.digits = 3

        # define L and ml, L has rounding .001 but ml has rounding .01
        # when producing e.g. 187.5ml, it will be rounded to .188L
        categ_test = self.env['uom.category'].create({'name': 'Volume Test'})

        uom_L = self.env['uom.uom'].create({
            'name': 'Test Liters',
            'category_id': categ_test.id,
            'uom_type': 'reference',
            'rounding': 0.001
        })

        uom_ml = self.env['uom.uom'].create({
            'name': 'Test ml',
            'category_id': categ_test.id,
            'uom_type': 'smaller',
            'rounding': 0.01,
            'factor_inv': 0.001,
        })

        # create a product component and the final product using the component
        product_comp = self.env['product.product'].create({
            'name': 'Product Component',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': uom_L.id,
            'uom_po_id': uom_L.id,
        })

        product_final = self.env['product.product'].create({
            'name': 'Product Final',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': uom_L.id,
            'uom_po_id': uom_L.id,
        })

        # the products are tracked by lot, so we go through _generate_consumed_move_line
        lot_final = self.env['stock.production.lot'].create({
            'name': 'Lot Final',
            'product_id': product_final.id,
            'company_id': self.env.company.id,
        })

        lot_comp = self.env['stock.production.lot'].create({
            'name': 'Lot Component',
            'product_id': product_comp.id,
            'company_id': self.env.company.id,
        })

        # update the quantity on hand for Component, in a lot
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(product_comp, self.stock_location, 1, lot_id=lot_comp)

        # create a BOM for Final, using Component
        test_bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': uom_L.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': product_comp.id,
                'product_qty': 375.00,
                'product_uom_id': uom_ml.id
            })],
        })

        # create a MO for this BOM
        mo_product_final_form = Form(self.env['mrp.production'])
        mo_product_final_form.product_id = product_final
        mo_product_final_form.product_uom_id = uom_L
        mo_product_final_form.bom_id = test_bom
        mo_product_final_form.product_qty = 0.5
        mo_product_final_form = mo_product_final_form.save()

        mo_product_final_form.action_confirm()
        mo_product_final_form.action_assign()
        self.assertEqual(mo_product_final_form.reservation_state, 'assigned')

        # produce
        res_dict = mo_product_final_form.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()

        # check that in _generate_consumed_move_line,
        # we do not create an extra move line because
        # of a conversion 187.5ml = 0.188L
        # thus creating an extra line with 'product_uom_qty': 0.5
        self.assertEqual(len(mo_product_final_form.move_raw_ids.move_line_ids), 1, 'One move line should exist for the MO.')

    def test_multi_button_plan(self):
        """ Test batch methods (confirm/validate) of the MO with the same bom """
        self.bom_2.type = "normal"  # avoid to get the operation of the kit bom

        mo_3 = Form(self.env['mrp.production'])
        mo_3.bom_id = self.bom_3
        mo_3 = mo_3.save()

        self.assertEqual(len(mo_3.workorder_ids), 2)

        mo_3.button_plan()
        self.assertEqual(mo_3.state, 'confirmed')
        self.assertEqual(mo_3.workorder_ids[0].state, 'ready')

        mo_1 = Form(self.env['mrp.production'])
        mo_1.bom_id = self.bom_3
        mo_1 = mo_1.save()

        mo_2 = Form(self.env['mrp.production'])
        mo_2.bom_id = self.bom_3
        mo_2 = mo_2.save()

        self.assertEqual(mo_1.product_id, self.product_6)
        self.assertEqual(mo_2.product_id, self.product_6)
        self.assertEqual(len(self.bom_3.operation_ids), 2)
        self.assertEqual(len(mo_1.workorder_ids), 2)
        self.assertEqual(len(mo_2.workorder_ids), 2)

        (mo_1 | mo_2).button_plan()  # Confirm and plan in the same "request"
        self.assertEqual(mo_1.state, 'confirmed')
        self.assertEqual(mo_2.state, 'confirmed')
        self.assertEqual(mo_1.workorder_ids[0].state, 'ready')
        self.assertEqual(mo_2.workorder_ids[0].state, 'ready')

        # produce
        res_dict = (mo_1 | mo_2).button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.immediate.production')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(mo_1.state, 'done')
        self.assertEqual(mo_2.state, 'done')

    def test_workcenter_timezone(self):
        # Workcenter is based in Bangkok
        # Possible working hours are Monday to Friday, from 8:00 to 12:00 and from 13:00 to 17:00 (UTC+7)
        workcenter = self.workcenter_1
        workcenter.resource_calendar_id.tz = 'Asia/Bangkok'

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_2.id,
            })],
            'operation_ids': [(0, 0, {
                'name': 'SuperOperation01',
                'workcenter_id': workcenter.id,
            }), (0, 0, {
                'name': 'SuperOperation01',
                'workcenter_id': workcenter.id,
            })],
        })

        # Next Monday at 6:00 am UTC
        date_planned = (Dt.now() + timedelta(days=7 - Dt.now().weekday())).replace(hour=6, minute=0, second=0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.date_planned_start = date_planned
        mo = mo_form.save()

        mo.workorder_ids[0].duration_expected = 240
        mo.workorder_ids[1].duration_expected = 60

        mo.action_confirm()
        mo.button_plan()

        # Asia/Bangkok is UTC+7 and the start date is on Monday at 06:00 UTC (i.e., 13:00 UTC+7).
        # So, in Bangkok, the first workorder uses the entire Monday afternoon slot 13:00 - 17:00 UTC+7 (i.e., 06:00 - 10:00 UTC)
        # The second job uses the beginning of the Tuesday morning slot: 08:00 - 09:00 UTC+7 (i.e., 01:00 - 02:00 UTC)
        self.assertEqual(mo.workorder_ids[0].date_planned_start, date_planned)
        self.assertEqual(mo.workorder_ids[0].date_planned_finished, date_planned + timedelta(hours=4))
        tuesday = date_planned + timedelta(days=1)
        self.assertEqual(mo.workorder_ids[1].date_planned_start, tuesday.replace(hour=1))
        self.assertEqual(mo.workorder_ids[1].date_planned_finished, tuesday.replace(hour=2))

    def test_products_with_variants(self):
        """Check for product with different variants with same bom"""
        product = self.env['product.template'].create({
            "attribute_line_ids": [
                [0, 0, {"attribute_id": 2, "value_ids": [[6, 0, [3, 4]]]}]
            ],
            "name": "Product with variants",
        })

        variant_1 = product.product_variant_ids[0]
        variant_2 = product.product_variant_ids[1]

        component = self.env['product.template'].create({
            "name": "Component",
        })

        self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.product_variant_id.id, 'product_qty': 1})
            ]
        })

        # First behavior to check, is changing the product (same product but another variant) after saving the MO a first time.
        mo_form_1 = Form(self.env['mrp.production'])
        mo_form_1.product_id = variant_1
        mo_1 = mo_form_1.save()
        mo_form_1 = Form(self.env['mrp.production'].browse(mo_1.id))
        mo_form_1.product_id = variant_2
        mo_1 = mo_form_1.save()
        mo_1.action_confirm()
        mo_1.action_assign()
        mo_form_1 = Form(self.env['mrp.production'].browse(mo_1.id))
        mo_form_1.qty_producing = 1
        mo_1 = mo_form_1.save()
        mo_1.button_mark_done()

        move_lines_1 = self.env['stock.move.line'].search([("reference", "=", mo_1.name)])
        move_finished_ids_1 = self.env['stock.move'].search([("production_id", "=", mo_1.id)])
        self.assertEqual(len(move_lines_1), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_1), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_1.product_id, variant_2, "Incorrect variant produced")

        # Second behavior is changing the product before saving the MO
        mo_form_2 = Form(self.env['mrp.production'])
        mo_form_2.product_id = variant_1
        mo_form_2.product_id = variant_2
        mo_2 = mo_form_2.save()
        mo_2.action_confirm()
        mo_2.action_assign()
        mo_form_2 = Form(self.env['mrp.production'].browse(mo_2.id))
        mo_form_2.qty_producing = 1
        mo_2 = mo_form_2.save()
        mo_2.button_mark_done()

        move_lines_2 = self.env['stock.move.line'].search([("reference", "=", mo_2.name)])
        move_finished_ids_2 = self.env['stock.move'].search([("production_id", "=", mo_2.id)])
        self.assertEqual(len(move_lines_2), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_2), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_2.product_id, variant_2, "Incorrect variant produced")

        # Third behavior is changing the product before saving the MO, then another time after
        mo_form_3 = Form(self.env['mrp.production'])
        mo_form_3.product_id = variant_1
        mo_form_3.product_id = variant_2
        mo_3 = mo_form_3.save()
        mo_form_3 = Form(self.env['mrp.production'].browse(mo_3.id))
        mo_form_3.product_id = variant_1
        mo_3 = mo_form_3.save()
        mo_3.action_confirm()
        mo_3.action_assign()
        mo_form_3 = Form(self.env['mrp.production'].browse(mo_3.id))
        mo_form_3.qty_producing = 1
        mo_3 = mo_form_3.save()
        mo_3.button_mark_done()

        move_lines_3 = self.env['stock.move.line'].search([("reference", "=", mo_3.name)])
        move_finished_ids_3 = self.env['stock.move'].search([("production_id", "=", mo_3.id)])
        self.assertEqual(len(move_lines_3), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_3), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_3.product_id, variant_1, "Incorrect variant produced")

    def test_manufacturing_order_with_work_orders(self):
        """Test the behavior of a manufacturing order when opening the workorder related to it,
           as well as the behavior when a backorder is created
           """
        # create a few work centers
        work_center_1 = self.env['mrp.workcenter'].create({"name": "WC1"})
        work_center_2 = self.env['mrp.workcenter'].create({"name": "WC2"})
        work_center_3 = self.env['mrp.workcenter'].create({"name": "WC3"})

        # create a product, a bom related to it with 3 components and 3 operations
        product = self.env['product.template'].create({"name": "Product"})
        component_1 = self.env['product.template'].create({"name": "Component 1", "type": "product"})
        component_2 = self.env['product.template'].create({"name": "Component 2", "type": "product"})
        component_3 = self.env['product.template'].create({"name": "Component 3", "type": "product"})

        self.env['stock.quant'].create({
            "product_id": component_1.product_variant_id.id,
            "location_id": 8,
            "inventory_quantity": 100
        })
        self.env['stock.quant'].create({
            "product_id": component_2.product_variant_id.id,
            "location_id": 8,
            "inventory_quantity": 100
        })
        self.env['stock.quant'].create({
            "product_id": component_3.product_variant_id.id,
            "location_id": 8,
            "inventory_quantity": 100
        })

        self.env['mrp.bom'].create({
            "product_tmpl_id": product.id,
            "product_id": False,
            "product_qty": 1,
            "bom_line_ids": [
                [0, 0, {"product_id": component_1.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_2.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_3.product_variant_id.id, "product_qty": 1}]
            ],
            "operation_ids": [
                [0, 0, {"name": "Operation 1", "workcenter_id": work_center_1.id}],
                [0, 0, {"name": "Operation 2", "workcenter_id": work_center_2.id}],
                [0, 0, {"name": "Operation 3", "workcenter_id": work_center_3.id}]
            ]
        })

        # create a manufacturing order with 10 product to produce
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product.product_variant_id
        mo_form.product_qty = 10
        mo = mo_form.save()

        self.assertEqual(mo.state, 'draft')
        mo.action_confirm()

        wo_1 = mo.workorder_ids[0]
        wo_2 = mo.workorder_ids[1]
        wo_3 = mo.workorder_ids[2]
        self.assertEqual(mo.state, 'confirmed')

        wo_1.button_start()
        self.assertEqual(mo.state, 'progress')
        wo_1.button_finish()

        wo_2.button_start()
        wo_2.qty_producing = 8
        wo_2.button_finish()

        wo_3.button_start()
        wo_3.qty_producing = 8
        wo_3.button_finish()

        self.assertEqual(mo.state, 'to_close')
        mo.button_mark_done()

        bo = self.env['mrp.production.backorder'].create({
            "mrp_production_backorder_line_ids": [
                [0, 0, {"mrp_production_id": mo.id, "to_backorder": True}]
            ]
        })
        bo.action_backorder()

        self.assertEqual(mo.state, 'done')

        mo_2 = self.env['mrp.production'].browse(mo.id + 1)
        self.assertEqual(mo_2.state, 'progress')
        wo_4, wo_5, wo_6 = mo_2.workorder_ids
        self.assertEqual(wo_4.state, 'cancel')

        wo_5.button_start()
        self.assertEqual(mo_2.state, 'progress')
        wo_5.button_finish()

        wo_6.button_start()
        wo_6.button_finish()
        self.assertEqual(mo_2.state, 'to_close')
        mo_2.button_mark_done()
        self.assertEqual(mo_2.state, 'done')

    def test_move_finished_onchanges(self):
        """ Test that move_finished_ids (i.e. produced products) are still correct even after
        multiple onchanges have changed the the moves
        """

        product1 = self.env['product.product'].create({
            'name': 'Oatmeal Cookie',
        })
        product2 = self.env['product.product'].create({
            'name': 'Chocolate Chip Cookie',
        })

        # ===== product_id onchange checks ===== #
        # check product_id onchange without saving
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_id = product2
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product2, 'Wrong product to produce in finished product move')
        # check product_id onchange after saving
        mo_form = Form(self.env['mrp.production'].browse(mo.id))
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')
        # check product_id onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo.id))
        mo_form.product_id = product2
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')

        # ===== product_qty onchange checks ===== #
        # check product_qty onchange without saving
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_qty = 5
        mo_form.product_qty = 10
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 10, 'Wrong qty to produce for the finished product move')

        # check product_qty onchange after saving
        mo_form = Form(self.env['mrp.production'].browse(mo2.id))
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 5, 'Wrong qty to produce for the finished product move')

        # check product_qty onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo2.id))
        mo_form.product_qty = 10
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 5, 'Wrong qty to produce for the finished product move')

        # ===== product_uom_id onchange checks ===== #
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_qty = 1
        mo_form.product_uom_id = self.env['uom.uom'].browse(self.ref('uom.product_uom_dozen'))
        mo3 = mo_form.save()
        self.assertEqual(len(mo3.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo3.move_finished_ids.product_qty, 12, 'Wrong qty to produce for the finished product move')

        # ===== bom_id onchange checks ===== #
        component = self.env['product.product'].create({
            "name": "Sugar",
        })

        bom1 = self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product1.product_tmpl_id.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1})
            ]
        })

        bom2 = self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product1.product_tmpl_id.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 10})
            ]
        })
        # check bom_id onchange before product change
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo_form.product_id = product2
        mo4 = mo_form.save()
        self.assertFalse(mo4.bom_id, 'BoM should have been removed')
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product2, 'Wrong product to produce in finished product move')
        # check bom_id onchange after product change
        mo_form = Form(self.env['mrp.production'].browse(mo4.id))
        mo_form.product_id = product1
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo4 = mo_form.save()
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')
        # check product_id onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo4.id))
        mo_form.bom_id = bom2
        mo_form.bom_id = bom1
        mo4 = mo_form.save()
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')
