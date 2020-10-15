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
        test_quantity = 2.0
        self.bom_1.routing_id = False
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

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': man_order.id,
            'active_ids': [man_order.id],
        }))
        produce_form.qty_producing = 1.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        man_order.button_mark_done()
        self.assertEqual(man_order.state, 'done', "Production order should be in done state.")

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
            'location_id': self.ref('stock.stock_location_14')
        })

        production_2.action_assign()
        # check sub product availability state is partially available
        self.assertEqual(production_2.reservation_state, 'confirmed', 'Production order should be availability for partially available state')

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 5.0,
            'location_id': self.ref('stock.stock_location_14')
        })

        production_2.action_assign()
        # check sub product availability state is assigned
        self.assertEqual(production_2.reservation_state, 'assigned', 'Production order should be availability for assigned state')

    def test_empty_routing(self):
        """ Check what happens when you work with an empty routing"""
        routing = self.env['mrp.routing'].create({'name': 'Routing without operations'})
        self.bom_3.routing_id = routing.id
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production = production_form.save()
        self.assertEqual(production.routing_id.id, False, 'The routing field should be empty on the mo')

    def test_split_move_line(self):
        """ Consume more component quantity than the initial demand.
        It should create extra move and share the quantity between the two stock
        moves """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_base_1=10, qty_final=1, qty_base_2=1)
        bom.consumption = 'flexible'
        mo.action_assign()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        for i in range(len(produce_form.raw_workorder_line_ids)):
            with produce_form.raw_workorder_line_ids.edit(i) as line:
                line.qty_done += 1
        product_produce = produce_form.save()
        product_produce.do_produce()
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
        self.env['mrp.bom'].create({
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
        quant_before = custom_laptop.qty_available
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
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
        inventory.action_start()
        inventory.action_validate()

        # create a mo for this bom
        mo_custom_laptop_form = Form(self.env['mrp.production'])
        mo_custom_laptop_form.product_id = custom_laptop
        mo_custom_laptop_form.product_qty = 2
        mo_custom_laptop = mo_custom_laptop_form.save()
        mo_custom_laptop.action_confirm()
        mo_custom_laptop.action_assign()
        self.assertEqual(mo_custom_laptop.reservation_state, 'assigned')

        # produce one item, call `post_inventory`
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.qty_producing = 1.00
        custom_laptop_produce = produce_form.save()
        custom_laptop_produce.do_produce()
        mo_custom_laptop.post_inventory()

        # check the consumed quants of the produced quant
        first_move = mo_custom_laptop.move_finished_ids.filtered(lambda mo: mo.state == 'done')
        quant_after1 = custom_laptop.qty_available
        self.assertEqual(first_move.quantity_done, 1, "Order already produce 1 product")
        self.assertEqual(quant_after1 - quant_before, 1, "1 product available after production")
        second_move = mo_custom_laptop.move_finished_ids.filtered(lambda mo: mo.state == 'confirmed')
        self.assertEqual(second_move.quantity_done, 0, "There is still one product to pruduce")

        # produce the second item, call `post_inventory`
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.qty_producing = 1.00
        custom_laptop_produce = produce_form.save()
        custom_laptop_produce.do_produce()
        mo_custom_laptop.post_inventory()
        self.assertEqual(second_move.quantity_done, 1, "Order produce the second product")
        quant_after2 = custom_laptop.qty_available
        self.assertEqual(quant_after2 - quant_before, 2, "2 products available after production")

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

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.move_finished_ids.move_line_ids.qty_done -= 1
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

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 2
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.post_inventory()
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 5,
        })
        update_quantity_wizard.change_prod_qty()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        mo.button_mark_done()

        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).mapped('quantity_done')), 20)
        self.assertEqual(sum(mo.move_finished_ids.mapped('quantity_done')), 5)

    def test_update_quantity_3(self):
        """ Build 1 final products then update the Manufacturing
        order quantity. Check the remaining quantity to produce
        take care of the first quantity produced."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 3,
        })
        update_quantity_wizard.change_prod_qty()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        mo.button_mark_done()
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).mapped('quantity_done')), 12)
        self.assertEqual(sum(mo.move_finished_ids.mapped('quantity_done')), 3)

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
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production.id,
            'active_ids': [production.id],
        }))
        produce_form.qty_producing = 8
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
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

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        # change the quantity done in one line
        produce_form.raw_workorder_line_ids._records[0]['qty_done'] = 1

        # change the quantity producing
        produce_form.qty_producing = 3

        # check than all quantities are update correctly
        line1 = produce_form.raw_workorder_line_ids._records[0]
        line2 = produce_form.raw_workorder_line_ids._records[1]
        self.assertEqual(line1['qty_to_consume'], 3, "Wrong quantity to consume")
        self.assertEqual(line1['qty_done'], 3, "Wrong quantity done")
        self.assertEqual(line2['qty_to_consume'], 12, "Wrong quantity to consume")
        self.assertEqual(line2['qty_done'], 12, "Wrong quantity done")
        
        product_produce = produce_form.save()
        self.assertEqual(len(product_produce.raw_workorder_line_ids), 2, 'You should have produce lines even the consumed products are not tracked.')
        product_produce.do_produce()

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
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))

        self.assertEqual(len(produce_form.raw_workorder_line_ids), 3, 'You should have 3 produce lines. One for each serial to consume and for the untracked product.')
        produce_form.qty_producing = 1

        # get the proposed lot
        consumed_lots = self.env['stock.production.lot']
        for workorder_line in produce_form.raw_workorder_line_ids._records:
            if workorder_line['product_id'] == p1.id:
                consumed_lots |= self.env['stock.production.lot'].browse(workorder_line['lot_id'])
        consumed_lots.ensure_one()
        product_produce = produce_form.save()
        product_produce.do_produce()

        remaining_lot = (lot_p1_1 | lot_p1_2) - consumed_lots
        remaining_lot.ensure_one()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = produce_form.save()
        self.assertEqual(len(product_produce.raw_workorder_line_ids), 2, 'You should have 2 produce lines left.')
        for line in product_produce.raw_workorder_line_ids.filtered(lambda x: x.lot_id):
            self.assertEqual(line.lot_id, remaining_lot, 'Wrong lot proposed.')

    def test_product_produce_3(self):
        """ Checks that, for a BOM where one of the components is tracked by lot and the other is
        not tracked, when creating a manufacturing order for 1 finished product and reserving, the
        produce wizard proposes the corrects lines. Then, checks the generated move lines when over
        consuming.
        """
        # FIXME: some asserts on the quants after overproducing would be nice
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.env.ref('stock.stock_location_components')
        self.stock_shelf_2 = self.env.ref('stock.stock_location_14')
        mo, _, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot', qty_base_1=10, qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        mo.bom_id.consumption = 'flexible'  # Because we will over consume.
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
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1.0
        for i in range(len(produce_form.raw_workorder_line_ids)):
            with produce_form.raw_workorder_line_ids.edit(i) as line:
                line.qty_done += 1
        product_produce = produce_form.save()
        product_produce.finished_lot_id = final_product_lot.id
        # product 1 lot 1 shelf1
        # product 1 lot 1 shelf2
        # product 1 lot 2
        self.assertEqual(len(product_produce.raw_workorder_line_ids), 4, 'You should have 4 produce lines. lot 1 shelf_1, lot 1 shelf_2, lot2 and for product which have tracking None')

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
        # FIXME sle: how is it possible to consume before producing in the interface?
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
        product_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = product_form.save()
        product_produce.do_produce()

        m_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1)
        ml_p1 = m_p1.mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 3)
        self.assertEqual(sorted(ml_p1.mapped('qty_done')), [1.0, 2.0, 3.0], 'Quantity done should be 1.0, 2.0 or 3.0')
        self.assertEqual(m_p1.quantity_done, 6.0, 'Total qty done should be 6.0')
        self.assertEqual(sum(ml_p1.mapped('product_uom_qty')), 5.0, 'Total qty reserved should be 5.0')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_6(self):
        """ Plan 5 finished products, reserve and produce 3. Post the current production.
        Simulate an unlock and edit and, on the opened moves, set the consumed quantity
        to 3. Now, try to update the quantity to produce to 3. It should fail since there
        are consumed quantities. Unlock and edit, remove the consumed quantities and
        update the quantity to produce to 3."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 3
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.post_inventory()
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

    def test_product_produce_7(self):
        """ Add components in 2 different sub location. Do not reserve the MO
        and checks that the move line created takes stock from location that
        contains needed raw materials.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.env.ref('stock.stock_location_components')
        self.stock_shelf_2 = self.env.ref('stock.stock_location_14')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 3)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 2)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_shelf_1, 1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_shelf_2, 1)

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1
        produce_wizard = produce_form.save()

        self.assertEqual(len(produce_wizard.raw_workorder_line_ids), 2)
        produce_wizard.do_produce()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1

        produce_wizard = produce_form.save()

        self.assertEqual(len(produce_wizard.raw_workorder_line_ids), 2)
        produce_wizard.do_produce()

        mo.button_mark_done()
        mo_move_line_p1 = mo.move_raw_ids[1].move_line_ids
        self.assertEqual(sum(mo_move_line_p1.filtered(lambda ml: ml.location_id == self.stock_location).mapped('qty_done')), 3)
        self.assertEqual(sum(mo_move_line_p1.filtered(lambda ml: ml.location_id == self.stock_shelf_1).mapped('qty_done')), 3)
        self.assertEqual(sum(mo_move_line_p1.filtered(lambda ml: ml.location_id == self.stock_shelf_2).mapped('qty_done')), 2)
        self.assertEqual(sum(mo.move_finished_ids.move_line_ids.mapped('qty_done')), 2)

        self.assertEqual(self.env['stock.quant']._gather(p1, self.stock_location, strict=True).quantity, 0)
        self.assertEqual(self.env['stock.quant']._gather(p1, self.stock_shelf_1, strict=True).quantity, 0)
        self.assertEqual(self.env['stock.quant']._gather(p1, self.stock_shelf_2, strict=True).quantity, 0)

        self.assertEqual(self.env['stock.quant']._gather(p2, self.stock_shelf_1, strict=True).quantity, 0)
        self.assertEqual(self.env['stock.quant']._gather(p2, self.stock_shelf_2, strict=True).quantity, 0)
        self.assertEqual(self.env['stock.quant']._gather(p_final, self.stock_location, strict=True).quantity, 2)

    def test_product_produce_8(self):
        """ Produce more than reserved and planned. Check that produce wizard
        only propose one line for product not reserved.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.stock_location = self.env.ref('stock.stock_location_stock')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 2)

        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1
        produce_wizard = produce_form.save()
        self.assertEqual(len(produce_wizard.raw_workorder_line_ids), 2)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1).qty_reserved, 4)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p2).qty_reserved, 1)
        produce_wizard.do_produce()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1
        produce_wizard = produce_form.save()
        # p1 1 1 1
        # p1 3 0 3
        # p2 1 1 1
        self.assertEqual(len(produce_wizard.raw_workorder_line_ids), 3)
        self.assertEqual(sum(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1).mapped('qty_reserved')), 1)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1 and l.qty_reserved).qty_to_consume, 1)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1 and not l.qty_reserved).qty_to_consume, 3)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p2).qty_reserved, 1)

        with Form(produce_wizard) as produce_form:
            produce_form.qty_producing = 2
        # p1 1 1 1
        # p1 7 0 7
        # p2 1 1 1
        # p2 1 0 1
        self.assertEqual(len(produce_wizard.raw_workorder_line_ids), 4)
        self.assertEqual(sum(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1).mapped('qty_reserved')), 1)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1 and l.qty_reserved).qty_to_consume, 1)
        self.assertEqual(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p1 and not l.qty_reserved).qty_to_consume, 7)
        self.assertEqual(sum(produce_wizard.raw_workorder_line_ids.filtered(lambda l: l.product_id == p2).mapped('qty_reserved')), 1)

        produce_wizard.do_produce()

        mo.button_mark_done()

        self.assertEqual(self.env['stock.quant']._gather(p1, self.stock_location, strict=True).quantity, -7)
        self.assertEqual(self.env['stock.quant']._gather(p2, self.stock_location, strict=True).quantity, -1)
        self.assertEqual(self.env['stock.quant']._gather(p_final, self.stock_location, strict=True).quantity, 3)

    def test_product_produce_9(self):
        """ Checks the constraints of a strict BOM without tracking when playing around in the
        produce wizard.
        """
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

        with self.assertRaises(UserError):
            # try adding another line for a bom product to increase the quantity
            produce_form.qty_producing = 1
            with produce_form.raw_workorder_line_ids.new() as line:
                line.product_id = p1
                line.qty_done = 1
            product_produce = produce_form.save()
            product_produce.do_produce()

        with self.assertRaises(UserError):
            # Try updating qty_done
            product_produce = produce_form.save()
            product_produce.raw_workorder_line_ids[0].qty_done += 1
            product_produce.do_produce()

        with self.assertRaises(UserError):
            # try adding another product
            produce_form = Form(self.env['mrp.product.produce'].with_context({
                'active_id': mo.id,
                'active_ids': [mo.id],
            }))
            produce_form.qty_producing = 1
            with produce_form.raw_workorder_line_ids.new() as line:
                line.product_id = self.product_4
                line.qty_done = 1
            product_produce = produce_form.save()
            product_produce.do_produce()

        # try adding another line for a bom product but the total quantity is good
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1

        with produce_form.raw_workorder_line_ids.new() as line:
            line.product_id = p1
            line.qty_done = 1
        product_produce = produce_form.save()
        product_produce.raw_workorder_line_ids[1].qty_done -= 1
        product_produce.do_produce()

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

        self.bom_1.routing_id = False

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()

        mo.action_confirm()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        self.assertEqual(len(produce_form.finished_workorder_line_ids), 4)
        produce_wizard = produce_form.save()
        wokorder_lines_byproduct_1 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(wokorder_lines_byproduct_1), 2)
        self.assertEqual(wokorder_lines_byproduct_1.mapped('qty_to_consume'), [1.0, 1.0])
        self.assertEqual(wokorder_lines_byproduct_1.mapped('qty_done'), [1.0, 1.0])
        wokorder_lines_byproduct_2 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(wokorder_lines_byproduct_2), 1)
        self.assertEqual(wokorder_lines_byproduct_2.qty_to_consume, 4.0)
        self.assertEqual(wokorder_lines_byproduct_2.qty_done, 4.0)

        wokorder_lines_byproduct_3 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(wokorder_lines_byproduct_3.qty_to_consume, 4.0)
        self.assertEqual(wokorder_lines_byproduct_3.qty_done, 4.0)
        self.assertEqual(wokorder_lines_byproduct_3.product_uom_id, dozen)

        produce_form = Form(produce_wizard)
        produce_form.qty_producing = 1.0
        self.assertEqual(len(produce_form.finished_workorder_line_ids), 3)
        produce_wizard = produce_form.save()
        wokorder_lines_byproduct_1 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(wokorder_lines_byproduct_1), 1)
        self.assertEqual(wokorder_lines_byproduct_1.qty_to_consume, 1.0)
        self.assertEqual(wokorder_lines_byproduct_1.qty_done, 1.0)
        wokorder_lines_byproduct_2 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(wokorder_lines_byproduct_2), 1)
        self.assertEqual(wokorder_lines_byproduct_2.qty_to_consume, 2.0)
        self.assertEqual(wokorder_lines_byproduct_2.qty_done, 2.0)

        wokorder_lines_byproduct_3 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(wokorder_lines_byproduct_3.qty_to_consume, 2.0)
        self.assertEqual(wokorder_lines_byproduct_3.qty_done, 2.0)
        self.assertEqual(wokorder_lines_byproduct_3.product_uom_id, dozen)

        produce_form = Form(produce_wizard)
        wokorder_lines_byproduct_1.lot_id = self.serial_1
        wokorder_lines_byproduct_2.lot_id = self.lot_1
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        self.assertEqual(produce_form.qty_producing, 1.0)
        self.assertEqual(len(produce_form.finished_workorder_line_ids), 3)
        produce_wizard = produce_form.save()

        wokorder_lines_byproduct_1 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(wokorder_lines_byproduct_1), 1)
        self.assertEqual(wokorder_lines_byproduct_1.qty_to_consume, 1.0)
        self.assertEqual(wokorder_lines_byproduct_1.qty_done, 1.0)
        wokorder_lines_byproduct_2 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(wokorder_lines_byproduct_2), 1)
        self.assertEqual(wokorder_lines_byproduct_2.qty_to_consume, 2.0)
        self.assertEqual(wokorder_lines_byproduct_2.qty_done, 2.0)

        wokorder_lines_byproduct_3 = produce_wizard.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(wokorder_lines_byproduct_3.qty_to_consume, 2.0)
        self.assertEqual(wokorder_lines_byproduct_3.qty_done, 2.0)
        self.assertEqual(wokorder_lines_byproduct_3.product_uom_id, dozen)

        produce_form = Form(produce_wizard)
        wokorder_lines_byproduct_1.lot_id = self.serial_2
        wokorder_lines_byproduct_2.lot_id = self.lot_2
        wokorder_lines_byproduct_3.qty_done = 3.0
        produce_wizard = produce_form.save()

        produce_wizard.do_produce()

        mo.button_mark_done()
        move_lines_byproduct_1 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1).mapped('move_line_ids')
        move_lines_byproduct_2 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2).mapped('move_line_ids')
        move_lines_byproduct_3 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3).mapped('move_line_ids')
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

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 3
        self.assertEqual(len(produce_form.raw_workorder_line_ids._records), 4, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_done'] for x in produce_form.raw_workorder_line_ids._records]), 15, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_reserved'] for x in produce_form.raw_workorder_line_ids._records]), 5, 'Update the produce quantity should not change the components reserved quantity.')
        produce_form.qty_producing = 4
        self.assertEqual(len(produce_form.raw_workorder_line_ids._records), 4, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_done'] for x in produce_form.raw_workorder_line_ids._records]), 20, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_reserved'] for x in produce_form.raw_workorder_line_ids._records]), 5, 'Update the produce quantity should not change the components reserved quantity.')

        produce_form.qty_producing = 1
        self.assertEqual(len(produce_form.raw_workorder_line_ids._records), 2, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_done'] for x in produce_form.raw_workorder_line_ids._records]), 5, 'Update the produce quantity should change the components quantity.')
        self.assertEqual(sum([x['qty_reserved'] for x in produce_form.raw_workorder_line_ids._records]), 5, 'Update the produce quantity should not change the components reserved quantity.')
        # try adding another product that doesn't belong to the BoM
        with produce_form.raw_workorder_line_ids.new() as line:
            line.product_id = self.product_4
            line.qty_done = 1
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

    def test_product_produce_12(self):
        """ Checks that, the production is robust against deletion of finished move."""

        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1
        produce_wizard = produce_form.save()
        # remove the finished move from the available to be updated
        mo.move_finished_ids._action_done()
        produce_wizard.do_produce()

    def test_product_produce_uom(self):
        """ Produce a finished product tracked by serial number. Set another
        UoM on the bom. The produce wizard should keep the UoM of the product (unit)
        and quantity = 1."""

        plastic_laminate = self.env.ref('mrp.product_product_plastic_laminate')
        bom = self.env.ref('mrp.mrp_bom_plastic_laminate')
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')

        plastic_laminate.tracking = 'serial'

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
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.finished_lot_id = final_product_lot
        product_produce = produce_form.save()
        self.assertEqual(product_produce.qty_producing, 1)
        self.assertEqual(product_produce.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')
        product_produce.finished_lot_id = final_product_lot.id

        product_produce.do_produce()
        move_line_raw = mo.move_raw_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_raw.qty_done, 1)
        self.assertEqual(move_line_raw.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

        move_line_finished = mo.move_finished_ids.mapped('move_line_ids').filtered(lambda m: m.qty_done)
        self.assertEqual(move_line_finished.qty_done, 1)
        self.assertEqual(move_line_finished.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

    def test_product_produce_uom_2(self):
        """ Create a bom with a serial tracked component and a pair UoM (2 x unit).
        The produce wizard should create 2 line with quantity = 1 and UoM = unit for
        this component. """

        unit = self.env.ref("uom.product_uom_unit")
        categ_unit_id = self.env.ref('uom.product_uom_categ_unit')
        paire = self.env['uom.uom'].create({
            'name': 'Paire',
            'factor_inv': 2,
            'uom_type': 'bigger',
            'rounding': 0.001,
            'category_id': categ_unit_id.id
        })
        binocular = self.env['product.product'].create({
            'name': 'Binocular',
            'type': 'product',
            'uom_id': unit.id,
            'uom_po_id': unit.id
        })
        nocular = self.env['product.product'].create({
            'name': 'Nocular',
            'type': 'product',
            'tracking': 'serial',
            'uom_id': unit.id,
            'uom_po_id': unit.id
        })
        bom_binocular = self.env['mrp.bom'].create({
            'product_tmpl_id': binocular.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit.id,
            'bom_line_ids': [(0, 0, {
                'product_id': nocular.id,
                'product_qty': 1,
                'product_uom_id': paire.id
            })]
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = binocular
        mo_form.bom_id = bom_binocular
        mo_form.product_uom_id = unit
        mo_form.product_qty = 1
        mo = mo_form.save()

        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 1, 'Quantity should be 1.')
        self.assertEqual(mo.move_raw_ids.product_uom, paire, 'Move UoM should be "Paire".')

        # produce product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        product_produce = produce_form.save()
        self.assertEqual(product_produce.qty_producing, 1)
        self.assertEqual(len(product_produce.raw_workorder_line_ids), 2, 'Should be 2 lines since the component tracking is serial and quantity 2.')
        self.assertEqual(product_produce.raw_workorder_line_ids[0].qty_to_consume, 1, 'Should be 1 unit since the tracking is serial and quantity 2.')
        self.assertEqual(product_produce.raw_workorder_line_ids[0].product_uom_id, unit, 'Should be the product uom so "unit"')
        self.assertEqual(product_produce.raw_workorder_line_ids[1].qty_to_consume, 1, 'Should be 1 unit since the tracking is serial and quantity 2.')
        self.assertEqual(product_produce.raw_workorder_line_ids[1].product_uom_id, unit, 'should be the product uom so "unit"')

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
