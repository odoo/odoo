# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestMrpProductionBackorder(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        warehouse_form = Form(cls.env['stock.warehouse'])
        warehouse_form.name = 'Test Warehouse'
        warehouse_form.code = 'TWH'
        cls.warehouse = warehouse_form.save()

    def test_no_tracking_1(self):
        """Create a MO for 4 product. Produce 4. The backorder button should
        not appear and hitting mark as done should not open the backorder wizard.
        The name of the MO should be MO/001.
        """
        mo = self.generate_mo(qty_final=4)[0]

        mo_form = Form(mo)
        mo_form.qty_producing = 4
        mo = mo_form.save()

        # No backorder is proposed
        self.assertTrue(mo.button_mark_done())
        self.assertEqual(mo._get_quantity_to_backorder(), 0)
        self.assertTrue("-001" not in mo.name)

    def test_no_tracking_2(self):
        """Create a MO for 4 product. Produce 1. The backorder button should
        appear and hitting mark as done should open the backorder wizard. In the backorder
        wizard, choose to do the backorder. A new MO for 3 self.untracked_bom should be
        created.
        The sequence of the first MO should be MO/001-01, the sequence of the second MO
        should be MO/001-02.
        Check that all MO are reachable through the procurement group.
        """
        production, _, _, product_to_use_1, _ = self.generate_mo(qty_final=4, qty_base_1=3)
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, True)

        # Make some stock and reserve
        for product in production.move_raw_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': production.location_src_id.id,
            })._apply_inventory()
        production.action_assign()
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, False)

        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()

        action = production.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        # Two related MO to the procurement group
        self.assertEqual(len(production.procurement_group_id.mrp_production_ids), 2)

        # Check MO backorder
        mo_backorder = production.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_id.id, production.product_id.id)
        self.assertEqual(mo_backorder.product_qty, 3)
        self.assertEqual(sum(mo_backorder.move_raw_ids.filtered(lambda m: m.product_id.id == product_to_use_1.id).mapped("product_uom_qty")), 9)
        self.assertEqual(mo_backorder.reserve_visible, False)  # the reservation is retrigger depending on the picking type

    def test_no_tracking_pbm_1(self):
        """Create a MO for 4 product. Produce 1. The backorder button should
        appear and hitting mark as done should open the backorder wizard. In the backorder
        wizard, choose to do the backorder. A new MO for 3 self.untracked_bom should be
        created.
        The sequence of the first MO should be MO/001-01, the sequence of the second MO
        should be MO/001-02.
        Check that all MO are reachable through the procurement group.
        """
        # Required for `manufacture_steps` to be visible in the view
        self.env.user.groups_id += self.env.ref("stock.group_adv_location")
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm'

        production, _, product_to_build, product_to_use_1, product_to_use_2 = self.generate_mo(qty_base_1=4, qty_final=4, picking_type_id=self.warehouse.manu_type_id)

        move_raw_ids = production.move_raw_ids
        self.assertEqual(len(move_raw_ids), 2)
        self.assertEqual(set(move_raw_ids.mapped("product_id")), {product_to_use_1, product_to_use_2})

        pbm_move = move_raw_ids.move_orig_ids
        self.assertEqual(len(pbm_move), 2)
        self.assertEqual(set(pbm_move.mapped("product_id")), {product_to_use_1, product_to_use_2})
        self.assertFalse(pbm_move.move_orig_ids)

        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_1.id).mapped("product_qty")), 16)
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_2.id).mapped("product_qty")), 4)

        action = production.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        mo_backorder = production.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.delivery_count, 1)

        pbm_move |= mo_backorder.move_raw_ids.move_orig_ids
        # Check that quantity is correct
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_1.id).mapped("product_qty")), 16)
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_2.id).mapped("product_qty")), 4)

        self.assertFalse(pbm_move.move_orig_ids)

    def test_no_tracking_pbm_sam_1(self):
        """Create a MO for 4 product. Produce 1. The backorder button should
        appear and hitting mark as done should open the backorder wizard. In the backorder
        wizard, choose to do the backorder. A new MO for 3 self.untracked_bom should be
        created.
        The sequence of the first MO should be MO/001-01, the sequence of the second MO
        should be MO/001-02.
        Check that all MO are reachable through the procurement group.
        """
        # Required for `manufacture_steps` to be visible in the view
        self.env.user.groups_id += self.env.ref("stock.group_adv_location")
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        production, _, product_to_build, product_to_use_1, product_to_use_2 = self.generate_mo(qty_base_1=4, qty_final=4, picking_type_id=self.warehouse.manu_type_id)

        move_raw_ids = production.move_raw_ids
        self.assertEqual(len(move_raw_ids), 2)
        self.assertEqual(set(move_raw_ids.mapped("product_id")), {product_to_use_1, product_to_use_2})

        pbm_move = move_raw_ids.move_orig_ids
        self.assertEqual(len(pbm_move), 2)
        self.assertEqual(set(pbm_move.mapped("product_id")), {product_to_use_1, product_to_use_2})
        self.assertFalse(pbm_move.move_orig_ids)
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_1.id).mapped("product_qty")), 16)
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_2.id).mapped("product_qty")), 4)

        mo_form = Form(production)
        mo_form.qty_producing = 1
        production = mo_form.save()

        action = production.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        sam_move = production.move_finished_ids.move_dest_ids
        self.assertEqual(len(sam_move), 1)
        self.assertEqual(sam_move.product_id.id, product_to_build.id)
        self.assertEqual(sum(sam_move.mapped("product_qty")), 1)

        mo_backorder = production.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.delivery_count, 2)

        pbm_move |= mo_backorder.move_raw_ids.move_orig_ids
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_1.id).mapped("product_qty")), 16)
        self.assertEqual(sum(pbm_move.filtered(lambda m: m.product_id.id == product_to_use_2.id).mapped("product_qty")), 4)

        sam_move |= mo_backorder.move_finished_ids.move_orig_ids
        self.assertEqual(sum(sam_move.mapped("product_qty")), 1)

        mo_backorder.button_mark_done()
        self.assertEqual(len(sam_move), 1.0)
        self.assertEqual(sam_move.product_qty, 4.0)

    def test_tracking_backorder_series_lot_1(self):
        """ Create a MO of 4 tracked products. all component is tracked by lots
        Produce one by one with one bakorder for each until end.
        """
        nb_product_todo = 4
        production, _, p_final, p1, p2 = self.generate_mo(qty_final=nb_product_todo, tracking_final='lot', tracking_base_1='lot', tracking_base_2='lot')
        lot_final = self.env['stock.lot'].create({
            'name': 'lot_final',
            'product_id': p_final.id,
        })
        lot_1 = self.env['stock.lot'].create({
            'name': 'lot_consumed_1',
            'product_id': p1.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': 'lot_consumed_2',
            'product_id': p2.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, nb_product_todo*4, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, nb_product_todo, lot_id=lot_2)

        active_production = production
        for i in range(nb_product_todo):
            active_production.action_assign()

            details_operation_form = Form(active_production.move_raw_ids.filtered(lambda m: m.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 4
                ml.lot_id = lot_1
            details_operation_form.save()
            details_operation_form = Form(active_production.move_raw_ids.filtered(lambda m: m.product_id == p2), view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 1
                ml.lot_id = lot_2
            details_operation_form.save()

            production_form = Form(active_production)
            production_form.qty_producing = 1
            production_form.lot_producing_id = lot_final
            active_production = production_form.save()

            active_production.move_raw_ids.picked = True
            active_production.button_mark_done()
            if i + 1 != nb_product_todo:  # If last MO, don't make a backorder
                action = active_production.button_mark_done()
                backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
                backorder.save().action_backorder()
            active_production = active_production.procurement_group_id.mrp_production_ids[-1]

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), nb_product_todo, f'You should have the {nb_product_todo} final product in stock')
        self.assertEqual(len(production.procurement_group_id.mrp_production_ids), nb_product_todo)

    def test_tracking_backorder_series_lot_2(self):
        """
        Create a MO with component tracked by lots. Produce a part of the demand
        by using some specific lots (not the ones suggested by the onchange).
        The components' reservation of the backorder should consider which lots
        have been consumed in the initial MO
        """
        production, _, _, p1, p2 = self.generate_mo(tracking_base_2='lot')
        lot1, lot2 = self.env['stock.lot'].create([{
            'name': f'lot_consumed_{i}',
            'product_id': p2.id,
        } for i in range(2)])
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 3, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 2, lot_id=lot2)

        production.action_assign()

        production_form = Form(production)
        production_form.qty_producing = 3

        details_operation_form = Form(production.move_raw_ids.filtered(lambda m: m.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 4 * 3
        details_operation_form.save()

        # Consume 1 Product from lot1 and 2 from lot 2
        p2_smls = production.move_raw_ids.filtered(lambda m: m.product_id == p2).move_line_ids
        self.assertEqual(len(p2_smls), 2, 'One for each lot')
        details_operation_form = Form(production.move_raw_ids.filtered(lambda m: m.product_id == p2), view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 1
            ml.lot_id = lot1
        with details_operation_form.move_line_ids.edit(1) as ml:
            ml.quantity = 2
            ml.lot_id = lot2
        details_operation_form.save()

        production = production_form.save()
        action = production.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        p2_bo_mls = production.procurement_group_id.mrp_production_ids[-1].move_raw_ids.filtered(lambda m: m.product_id == p2).move_line_ids
        self.assertEqual(len(p2_bo_mls), 1)
        self.assertEqual(p2_bo_mls.lot_id, lot1)
        self.assertEqual(p2_bo_mls.quantity_product_uom, 2)

    def test_uom_backorder(self):
        """
            test backorder component UoM different from the bom's UoM
        """
        product_finished = self.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'consu',
            'is_storable': True,
        })
        product_component = self.env['product.product'].create({
            'name': 'Botox',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_finished
        mo_form.bom_id = self.env['mrp.bom'].create({
            'product_id': product_finished.id,
            'product_tmpl_id': product_finished.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {
                'product_id': product_component.id,
                'product_qty': 1,
                'product_uom_id':self.env.ref('uom.product_uom_gram').id,
            }),]
        })
        mo_form.product_qty = 1000
        mo = mo_form.save()
        mo.action_confirm()

        self.env['stock.quant']._update_available_quantity(product_component, self.stock_location, 1000)
        mo.action_assign()

        production_form = Form(mo)
        production_form.qty_producing = 300
        mo = production_form.save()

        action = mo.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        # 300 Grams consumed and 700 reserved
        self.assertAlmostEqual(self.env['stock.quant']._gather(product_component, self.stock_location).reserved_quantity, 0.7)

    def test_rounding_backorder(self):
        """test backorder component rounding doesn't introduce reservation issues"""
        production, _, _, p1, p2 = self.generate_mo(qty_final=5, qty_base_1=1, qty_base_2=1)

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 100)

        production.action_assign()

        production_form = Form(production)
        production_form.qty_producing = 3.1
        production = production_form.save()

        details_operation_form = Form(production.move_raw_ids.filtered(lambda m: m.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 3.09

        details_operation_form.save()

        action = production.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        backorder = production.procurement_group_id.mrp_production_ids[-1]
        # 3.09 consumed and 1.9 reserved
        self.assertAlmostEqual(self.env['stock.quant']._gather(p1, self.stock_location).reserved_quantity, 1.9)
        self.assertAlmostEqual(backorder.move_raw_ids.filtered(lambda m: m.product_id == p1).move_line_ids.quantity, 1.9)

        # Make sure we don't have an unreserve errors
        backorder.do_unreserve()

    def test_tracking_backorder_series_serial_1(self):
        """ Create a MO of 4 tracked products (serial) with pbm_sam.
        all component is tracked by serial
        Produce one by one with one bakorder for each until end.
        """
        nb_product_todo = 4
        production, _, p_final, p1, p2 = self.generate_mo(qty_final=nb_product_todo, tracking_final='serial', tracking_base_1='serial', tracking_base_2='serial', qty_base_1=1)
        serials_final, serials_p1, serials_p2 = [], [], []
        for i in range(nb_product_todo):
            serials_final.append(self.env['stock.lot'].create({
                'name': f'lot_final_{i}',
                'product_id': p_final.id,
            }))
            serials_p1.append(self.env['stock.lot'].create({
                'name': f'lot_consumed_1_{i}',
                'product_id': p1.id,
            }))
            serials_p2.append(self.env['stock.lot'].create({
                'name': f'lot_consumed_2_{i}',
                'product_id': p2.id,
            }))
            self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=serials_p1[-1])
            self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1, lot_id=serials_p2[-1])

        production.action_assign()
        active_production = production
        for i in range(nb_product_todo):
            production_form = Form(active_production)
            production_form.qty_producing = 1
            production_form.lot_producing_id = serials_final[i]
            active_production = production_form.save()
            details_operation_form = Form(active_production.move_raw_ids.filtered(lambda m: m.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 1
                ml.lot_id = serials_p1[i]
            details_operation_form.save()
            details_operation_form = Form(active_production.move_raw_ids.filtered(lambda m: m.product_id == p2), view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 1
                ml.lot_id = serials_p2[i]
            details_operation_form.save()
            active_production.button_mark_done()
            if i + 1 != nb_product_todo:  # If last MO, don't make a backorder
                action = active_production.button_mark_done()
                backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
                backorder.save().action_backorder()
            active_production = active_production.procurement_group_id.mrp_production_ids[-1]

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), nb_product_todo, f'You should have the {nb_product_todo} final product in stock')
        self.assertEqual(len(production.procurement_group_id.mrp_production_ids), nb_product_todo)

    def test_tracking_backorder_immediate_production_serial_1(self):
        """ Create a MO to build 2 of a SN tracked product.
        Build both the starting MO and its backorder as immediate productions
        (i.e. Mark As Done without setting SN/filling any quantities)
        """
        mo, _, p_final, p1, p2 = self.generate_mo(qty_final=2, tracking_final='serial', qty_base_1=2, qty_base_2=2)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 2.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 2.0)
        mo.action_assign()
        mo.action_generate_serial()
        res_dict = mo.button_mark_done()
        self.assertEqual(res_dict.get('res_model'), 'mrp.production.backorder')
        backorder_wizard = Form.from_action(self.env, res_dict)

        # backorder should automatically open
        action = backorder_wizard.save().action_backorder()
        self.assertEqual(action.get('res_model'), 'mrp.production')
        backorder_mo = Form.from_action(self.env, action).save()
        backorder_mo.button_mark_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 2, "Incorrect number of final product produced.")
        self.assertEqual(len(self.env['stock.lot'].search([('product_id', '=', p_final.id)])), 2, "Serial Numbers were not correctly produced.")

    def test_backorder_name(self):
        def produce_one(mo):
            mo_form = Form(mo)
            mo_form.qty_producing = 1
            mo = mo_form.save()
            action = mo.button_mark_done()
            backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
            backorder.save().action_backorder()
            return mo.procurement_group_id.mrp_production_ids[-1]

        default_picking_type_id = self.env['mrp.production']._get_default_picking_type_id(self.env.company.id)
        default_picking_type = self.env['stock.picking.type'].browse(default_picking_type_id)
        mo_sequence = default_picking_type.sequence_id
        mo_sequence.prefix = "WH-MO-"
        initial_mo_name = mo_sequence.prefix + str(mo_sequence.number_next_actual).zfill(mo_sequence.padding)
        production = self.generate_mo(qty_final=5)[0]
        self.assertEqual(production.name, initial_mo_name)

        backorder = produce_one(production)
        self.assertEqual(production.name, initial_mo_name + "-001")
        self.assertEqual(backorder.name, initial_mo_name + "-002")

        backorder.backorder_sequence = 998
        for seq in [998, 999, 1000]:
            new_backorder = produce_one(backorder)
            self.assertEqual(backorder.name, initial_mo_name + "-" + str(seq))
            self.assertEqual(new_backorder.name, initial_mo_name + "-" + str(seq + 1))
            backorder = new_backorder

    def test_backorder_name_without_procurement_group(self):
        production = self.generate_mo(qty_final=5)[0]
        mo_form = Form(production)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        # Remove pg to trigger fallback on backorder name
        mo.procurement_group_id = False
        action = mo.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()

        # The pg is back
        self.assertTrue(production.procurement_group_id)
        backorder_ids = production.procurement_group_id.mrp_production_ids[1]
        self.assertEqual(production.name.split('-')[0], backorder_ids.name.split('-')[0])
        self.assertEqual(int(production.name.split('-')[1]) + 1, int(backorder_ids.name.split('-')[1]))

    def test_split_draft(self):
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.bom_1.product_id
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()
        self.assertEqual(mo.state, 'draft')

        action = mo.action_split()
        wizard = Form.from_action(self.env, action)
        wizard.counter = 2
        wizard.save().action_split()
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)

        mo1 = mo.procurement_group_id.mrp_production_ids[0]
        mo2 = mo.procurement_group_id.mrp_production_ids[1]
        self.assertEqual(mo1.move_raw_ids.mapped('state'), ['draft', 'draft'])
        self.assertEqual(mo2.move_raw_ids.mapped('state'), ['draft', 'draft'])

    def test_split_merge(self):
        # Change 'Units' rounding to 1 (integer only quantities)
        self.uom_unit.rounding = 1
        # Create a mo for 10 products
        mo, _, _, p1, p2 = self.generate_mo(qty_final=10)
        # Split in 3 parts
        action = mo.action_split()
        wizard = Form.from_action(self.env, action)
        wizard.counter = 3
        action = wizard.save().action_split()
        # Should have 3 mos
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 3)
        mo1 = mo.procurement_group_id.mrp_production_ids[0]
        mo2 = mo.procurement_group_id.mrp_production_ids[1]
        mo3 = mo.procurement_group_id.mrp_production_ids[2]
        # Check quantities
        self.assertEqual(mo1.product_qty, 3)
        self.assertEqual(mo2.product_qty, 3)
        self.assertEqual(mo3.product_qty, 4)
        # Check raw movew quantities
        self.assertEqual(mo1.move_raw_ids.filtered(lambda m: m.product_id == p1).product_qty, 12)
        self.assertEqual(mo2.move_raw_ids.filtered(lambda m: m.product_id == p1).product_qty, 12)
        self.assertEqual(mo3.move_raw_ids.filtered(lambda m: m.product_id == p1).product_qty, 16)
        self.assertEqual(mo1.move_raw_ids.filtered(lambda m: m.product_id == p2).product_qty, 3)
        self.assertEqual(mo2.move_raw_ids.filtered(lambda m: m.product_id == p2).product_qty, 3)
        self.assertEqual(mo3.move_raw_ids.filtered(lambda m: m.product_id == p2).product_qty, 4)

        # Merge them back
        expected_origin = ",".join([mo1.name, mo2.name, mo3.name])
        action = (mo1 + mo2 + mo3).action_merge()
        mo = self.env[action['res_model']].browse(action['res_id'])
        # Check origin & initial quantity
        self.assertEqual(mo.origin, expected_origin)
        self.assertEqual(mo.product_qty, 10)

    def test_reservation_method_w_mo(self):
        """ Create a MO for 2 units, Produce 1 and create a backorder.
        The MO and the backorder should be assigned according to the reservation method
        defined in the default manufacturing operation type
        """
        def create_mo(date_start=False):
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.bom_1.product_id
            mo_form.bom_id = self.bom_1
            mo_form.product_qty = 2
            if date_start:
                mo_form.date_start = date_start
            mo = mo_form.save()
            mo.action_confirm()
            return mo

        def produce_one(mo):
            mo_form = Form(mo)
            mo_form.qty_producing = 1
            mo = mo_form.save()
            action = mo.button_mark_done()
            backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
            backorder.save().action_backorder()
            return mo.procurement_group_id.mrp_production_ids[-1]

        # Make some stock and reserve
        for product in self.bom_1.bom_line_ids.product_id:
            product.is_storable = True
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': self.stock_location.id,
            })._apply_inventory()

        default_picking_type_id = self.env['mrp.production']._get_default_picking_type_id(self.env.company.id)
        default_picking_type = self.env['stock.picking.type'].browse(default_picking_type_id)

        # make sure generated MO will auto-assign
        default_picking_type.reservation_method = 'at_confirm'
        production = create_mo()
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, False)
        # check whether the backorder follows the same scenario as the original MO
        backorder = produce_one(production)
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(backorder.reserve_visible, False)

        # make sure generated MO will does not auto-assign
        default_picking_type.reservation_method = 'manual'
        production = create_mo()
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, True)
        backorder = produce_one(production)
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(backorder.reserve_visible, True)

        # make sure generated MO auto-assigns according to scheduled date
        default_picking_type.reservation_method = 'by_date'
        default_picking_type.reservation_days_before = 2
        # too early for scheduled date => don't auto-assign
        production = create_mo(datetime.now() + timedelta(days=10))
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, True)
        backorder = produce_one(production)
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(backorder.reserve_visible, True)

        # within scheduled date + reservation days before => auto-assign
        production = create_mo()
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reserve_visible, False)
        backorder = produce_one(production)
        self.assertEqual(backorder.state, 'confirmed')
        # The backorder is re reserved depending on the picking type
        self.assertEqual(backorder.reserve_visible, False)

    def test_split_mo(self):
        """
        Test that an MO is split correctly.
        BoM: 1 finished product = 0.5 comp1 + 1 comp2
        """
        mo = self.env['mrp.production'].create({
            'product_qty': 10,
            'bom_id': self.bom_1.id,
        })
        self.assertEqual(mo.move_raw_ids.mapped('product_uom_qty'), [5, 10])
        self.assertEqual(mo.state, 'draft')
        action = mo.action_split()
        wizard = Form.from_action(self.env, action)
        wizard.counter = 10
        action = wizard.save().action_split()
        # check that the MO is split in 10 and the components are split accordingly
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 10)
        self.assertEqual(mo.product_qty, 1)
        self.assertEqual(mo.move_raw_ids.mapped('product_uom_qty'), [0.5, 1])

    def test_split_mo_partially_available(self):
        """
        Test that an MO components availability is correct after split.
        - Create MO with BoM requiring 2 components 1:1
        - Change components quantity to 10 and 9
        - Split the MO and make sure that one of the MO's is not available post-split
        """
        mo, _, _, product_to_use_1, product_to_use_2 = self.generate_mo(qty_base_1=1, qty_final=10)

        inventory_wizard_1 = self.env['stock.change.product.qty'].create({
            'product_id': product_to_use_1.id,
            'product_tmpl_id': product_to_use_1.product_tmpl_id.id,
            'new_quantity': 10,
        })
        inventory_wizard_2 = self.env['stock.change.product.qty'].create({
            'product_id': product_to_use_2.id,
            'product_tmpl_id': product_to_use_2.product_tmpl_id.id,
            'new_quantity': 9,
        })
        inventory_wizard_1.change_product_qty()
        inventory_wizard_2.change_product_qty()

        self.assertEqual(mo.state, 'confirmed')
        mo.action_assign()
        action = mo.action_split()
        wizard = Form.from_action(self.env, action)
        wizard.counter = 10
        action = wizard.save().action_split()
        # check that the MO is split in 10 and exactly one of the components is not available
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 10)
        last_move = mo.procurement_group_id.mrp_production_ids[-1].move_raw_ids.filtered(lambda m: m.product_id == product_to_use_2)
        self.assertFalse(last_move.quantity)

    def test_auto_generate_backorder(self):
        """
        Test that when the create_backorder is set to "always", the backorder
        is automatically created. Due to the complexity of how backorders work,
        check that "priority" is correctly disabled as part of the expected
        "done" values that are written to the original MO.
        """
        mo = self.env['mrp.production'].create({
            'product_qty': 10,
            'bom_id': self.bom_1.id,
            'priority': '1',
        })
        mo.picking_type_id.create_backorder = "always"
        mo.action_confirm()
        with Form(mo) as mo_form:
            mo_form.qty_producing = 3.0
        mo = mo_form.save()
        self.assertEqual(mo.priority, '1')
        mo.button_mark_done()
        self.assertRecordValues(mo, [{'state': 'done', 'qty_produced': 3.0, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        backorder = mo.procurement_group_id.mrp_production_ids - mo
        self.assertEqual(backorder.product_qty, 7.0)

        with Form(backorder) as backorder_form:
            backorder_form.qty_producing = 7.0
        backorder = backorder_form.save()
        backorder.button_mark_done()
        self.assertRecordValues(backorder, [{'state': 'done', 'qty_produced': 7.0, 'mrp_production_backorder_count': 2}])

    def test_generate_backorder_multi_type(self):
        """
        Test that when there are 2 MOs with different manufacture operation types
        with different create_backorder values, then marking both as done at the
        same time works as expected:
        - Always + Ask (backorder=yes) => both are correctly backordered
        - Always + Never => only the always is backordered without wizard popping up
        - Ask (backorder=yes) + Never => only the ask is backordered
        - Always + Ask (backorder=no) => only the always is backordered
        - Ask (backorder=no) + Never => neither is backordered
        In every case, we also include a MO Produce All (i.e. `qty_producing` untouched, so all produced)
        and a fully produced (i.e. `qty_producing`=`product_qty`) to ensure they are always correctly passed
        as MOs that are done, but not backordered (i.e. their priority should be removed when done)
        """
        product_qty = 10.0  # for MOs with no backorder, qty_produced = product_qty
        qty_produced = 3.0  # for MOs where qty_produced < product_qty

        def create_mo(picking_type_id=False):
            return self.env['mrp.production'].create({
            'product_qty': product_qty,
            'bom_id': self.bom_1.id,
            'priority': '1',
            'picking_type_id': picking_type_id or self.warehouse.manu_type_id.id,
        })
        picking_type_always = self.warehouse.manu_type_id.copy({'name': "Always BO", 'sequence_code': "always", 'create_backorder': "always"})
        picking_type_ask = self.warehouse.manu_type_id.copy({'name': "Ask BO", 'sequence_code': "ask", 'create_backorder': "ask"})
        picking_type_never = self.warehouse.manu_type_id.copy({'name': "Never BO", 'sequence_code': "never", 'create_backorder': "never"})

        # always + ask (backorder=yes) => both are backordered in the end
        mo_produce_all = create_mo()
        mo_all_produced = create_mo()
        mo_always = create_mo(picking_type_always.id)
        mo_ask = create_mo(picking_type_ask.id)
        mos = (mo_produce_all | mo_all_produced | mo_always | mo_ask)
        mos.action_confirm()

        with Form(mo_all_produced) as mo_form:
            mo_all_produced.qty_producing = product_qty
        mo_form.save()
        with Form(mo_always) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()
        with Form(mo_ask) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()

        self.assertTrue(all(p == '1' for p in mos.mapped("priority")))
        action = mos.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        self.assertRecordValues(mo_produce_all, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_all_produced, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_always, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        self.assertRecordValues(mo_ask, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        bo = mo_always.procurement_group_id.mrp_production_ids - mo_always
        bo2 = mo_ask.procurement_group_id.mrp_production_ids - mo_ask
        self.assertEqual(bo.product_qty, product_qty - qty_produced)
        self.assertEqual(bo2.product_qty, product_qty - qty_produced)

        # always + never => only 1 backordered
        mo_produce_all = create_mo()
        mo_all_produced = create_mo()
        mo_always = create_mo(picking_type_always.id)
        mo_never = create_mo(picking_type_never.id)
        mos = (mo_produce_all | mo_all_produced | mo_always | mo_never)
        mos.action_confirm()

        with Form(mo_all_produced) as mo_form:
            mo_all_produced.qty_producing = product_qty
        mo_form.save()
        with Form(mo_always) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()
        with Form(mo_never) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()

        self.assertTrue(all(p == '1' for p in mos.mapped("priority")))
        action = mos.button_mark_done()
        self.assertRecordValues(mo_produce_all, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_all_produced, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_always, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        self.assertRecordValues(mo_never, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        bo = mo_always.procurement_group_id.mrp_production_ids - mo_always
        self.assertEqual(bo.product_qty, product_qty - qty_produced)

        # ask (backorder=yes) + never => only 1 backordered
        mo_produce_all = create_mo()
        mo_all_produced = create_mo()
        mo_ask = create_mo(picking_type_ask.id)
        mo_never = create_mo(picking_type_never.id)
        mos = (mo_produce_all | mo_all_produced | mo_ask | mo_never)
        mos.action_confirm()

        with Form(mo_all_produced) as mo_form:
            mo_all_produced.qty_producing = product_qty
        mo_form.save()
        with Form(mo_ask) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_ask = mo_form.save()
        with Form(mo_never) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_never = mo_form.save()

        self.assertTrue(all(p == '1' for p in mos.mapped("priority")))
        action = mos.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        self.assertRecordValues(mo_produce_all, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_all_produced, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_ask, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        self.assertRecordValues(mo_never, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        bo = mo_ask.procurement_group_id.mrp_production_ids - mo_ask
        self.assertEqual(bo.product_qty, product_qty - qty_produced)

        # always + ask (backorder=no) => only 1 backordered
        mo_produce_all = create_mo()
        mo_all_produced = create_mo()
        mo_always = create_mo(picking_type_always.id)
        mo_ask = create_mo(picking_type_ask.id)
        mos = (mo_produce_all | mo_all_produced | mo_always | mo_ask)
        mos.action_confirm()

        with Form(mo_all_produced) as mo_form:
            mo_all_produced.qty_producing = product_qty
        mo_form.save()
        with Form(mo_always) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()
        with Form(mo_ask) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()

        self.assertTrue(all(p == '1' for p in mos.mapped("priority")))
        action = mos.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_close_mo()
        self.assertRecordValues(mo_produce_all, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_all_produced, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_always, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 2, 'priority': '0'}])
        self.assertRecordValues(mo_ask, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        bo = mo_always.procurement_group_id.mrp_production_ids - mo_always
        self.assertEqual(bo.product_qty, product_qty - qty_produced)

        # ask (backorder=no) + never => neither is backordered
        mo_produce_all = create_mo()
        mo_all_produced = create_mo()
        mo_ask = create_mo(picking_type_ask.id)
        mo_never = create_mo(picking_type_never.id)
        mos = (mo_produce_all | mo_all_produced | mo_ask | mo_never)
        mos.action_confirm()

        with Form(mo_all_produced) as mo_form:
            mo_all_produced.qty_producing = product_qty
        mo_form.save()
        with Form(mo_ask) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()
        with Form(mo_never) as mo_form:
            mo_form.qty_producing = qty_produced
        mo_form.save()

        self.assertTrue(all(p == '1' for p in mos.mapped("priority")))
        action = mos.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_close_mo()
        self.assertRecordValues(mo_produce_all, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_all_produced, [{'state': 'done', 'qty_produced': product_qty, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_ask, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 1, 'priority': '0'}])
        self.assertRecordValues(mo_never, [{'state': 'done', 'qty_produced': qty_produced, 'mrp_production_backorder_count': 1, 'priority': '0'}])


class TestMrpWorkorderBackorder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestMrpWorkorderBackorder, cls).setUpClass()
        cls.uom_unit = cls.env['uom.uom'].search([
            ('category_id', '=', cls.env.ref('uom.product_uom_categ_unit').id),
            ('uom_type', '=', 'reference')
        ], limit=1)
        cls.finished1 = cls.env['product.product'].create({
            'name': 'finished1',
            'type': 'consu',
            'is_storable': True,
        })
        cls.compfinished1 = cls.env['product.product'].create({
            'name': 'compfinished1',
            'type': 'consu',
            'is_storable': True,
        })
        cls.compfinished2 = cls.env['product.product'].create({
            'name': 'compfinished2',
            'type': 'consu',
            'is_storable': True,
        })
        cls.workcenter1 = cls.env['mrp.workcenter'].create({
            'name': 'workcenter1',
        })
        cls.workcenter2 = cls.env['mrp.workcenter'].create({
            'name': 'workcenter2',
        })

        cls.bom_finished1 = cls.env['mrp.bom'].create({
            'product_id': cls.finished1.id,
            'product_tmpl_id': cls.finished1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.compfinished1.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.compfinished2.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'sequence': 1, 'name': 'finished operation 1', 'workcenter_id': cls.workcenter1.id}),
                (0, 0, {'sequence': 2, 'name': 'finished operation 2', 'workcenter_id': cls.workcenter2.id}),
            ],
        })
        cls.bom_finished1.bom_line_ids[0].operation_id = cls.bom_finished1.operation_ids[0].id
        cls.bom_finished1.bom_line_ids[1].operation_id = cls.bom_finished1.operation_ids[1].id

    def test_mrp_backorder_operations(self):
        """
        Checks that the operations'data are correclty set on a backorder:
            - Create a MO for 10 units, validate the op 1 completely and op 2 partially
            - Create a backorder and validate op 2 partially
            - Create a backorder and validate it completely
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        op_1, op_2 = mo.workorder_ids
        with Form(mo) as fmo:
            fmo.qty_producing = 10
        op_1.button_start()
        op_1.button_finish()
        with Form(mo) as fmo:
            fmo.qty_producing = 4
        op_2.button_start()
        op_2.button_finish()
        action = mo.button_mark_done()
        backorder_1 = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_1.save().action_backorder()
        bo_1 = mo.procurement_group_id.mrp_production_ids - mo
        self.assertRecordValues(bo_1.workorder_ids, [
            {'state': 'cancel', 'qty_remaining': 0.0, 'workcenter_id': op_1.workcenter_id.id},
            {'state': 'waiting', 'qty_remaining': 6.0, 'workcenter_id': op_2.workcenter_id.id},
        ])
        with Form(bo_1) as form_bo_1:
            form_bo_1.qty_producing = 2
        op_4 = bo_1.workorder_ids.filtered(lambda wo: wo.state != 'cancel')
        op_4.button_start()
        op_4.button_finish()
        action = bo_1.button_mark_done()
        self.assertRecordValues(op_4, [{'state': 'done', 'qty_remaining': 4.0}])
        backorder_2 = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_2.save().action_backorder()
        bo_2 = mo.procurement_group_id.mrp_production_ids - mo - bo_1
        self.assertRecordValues(bo_2.workorder_ids, [
            {'state': 'cancel', 'qty_remaining': 0.0, 'workcenter_id': op_1.workcenter_id.id},
            {'state': 'waiting', 'qty_remaining': 4.0, 'workcenter_id': op_2.workcenter_id.id},
        ])
        op_6 = bo_2.workorder_ids.filtered(lambda wo: wo.state != 'cancel')
        with Form(bo_2) as form_bo_2:
            form_bo_2.qty_producing = 4
        op_6.button_start()
        op_6.button_finish()
        bo_2.button_mark_done()
        self.assertRecordValues(op_6, [{'state': 'done', 'qty_remaining': 0.0}])

    def test_kit_bom_order_splitting(self):
        water_bottle_kit_product = self.env["product.product"].create({
                "name": "Water Bottle Kit",
                "is_storable": True,
            })
        water_bottle_kit = self.env['mrp.bom'].create({
            'product_id': water_bottle_kit_product.id,
            'product_tmpl_id': water_bottle_kit_product.product_tmpl_id.id,
            "type": "phantom",  # Kit
            'operation_ids': [
                Command.create({
                    'name': "Test Operation",
                    'workcenter_id': self.workcenter1.id,
                }),
            ],
        })
        water_bottle = self.env["product.product"].create({
            "name": "Water Bottle",
            "is_storable": True,
        })
        water_bottle_bom = self.env['mrp.bom'].create({
            'product_id': water_bottle.id,
            'product_tmpl_id': water_bottle.product_tmpl_id.id,
            'bom_line_ids': [
                Command.create({
                    'product_id': water_bottle_kit.product_id.id,
                    'product_qty': 1,
                }),
            ],
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = water_bottle
        mo_form.bom_id = water_bottle_bom
        mo_form.product_qty = 10
        mo = mo_form.save()
        self.assertEqual(mo.state, 'draft')
        action = mo.action_split()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.counter = 10
        wizard.save().action_split()
