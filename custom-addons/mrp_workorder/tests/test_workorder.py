# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mrp_workorder.tests.common import TestMrpWorkorderCommon
from odoo.addons.base.tests.common import HttpCase
from odoo.tests import Form, tagged
from odoo.tools import mute_logger
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class TestWorkOrder(TestMrpWorkorderCommon):
    @classmethod
    def setUpClass(cls):
        super(TestWorkOrder, cls).setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [
            (4, cls.env.ref('mrp.group_mrp_routings').id),
            (4, cls.env.ref('stock.group_production_lot').id)
        ]})
        # Products and lots
        cls.submarine_pod = cls.env['product.product'].create({
            'name': 'Submarine pod',
            'type': 'product',
            'tracking': 'serial'})
        cls.sp1 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp1',
            'company_id': cls.env.company.id,
        })
        cls.sp2 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp2',
            'company_id': cls.env.company.id,
        })
        cls.sp3 = cls.env['stock.lot'].create({
            'product_id': cls.submarine_pod.id,
            'name': 'sp3',
            'company_id': cls.env.company.id,
        })
        cls.elon_musk = cls.env['product.product'].create({
            'name': 'Elon Musk',
            'type': 'product',
            'tracking': 'serial'})
        cls.elon1 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon1',
            'company_id': cls.env.company.id,
        })
        cls.elon2 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon2',
            'company_id': cls.env.company.id,
        })
        cls.elon3 = cls.env['stock.lot'].create({
            'product_id': cls.elon_musk.id,
            'name': 'elon3',
            'company_id': cls.env.company.id,
        })
        cls.metal_cylinder = cls.env['product.product'].create({
            'name': 'Metal cylinder',
            'type': 'product',
            'tracking': 'lot'})
        cls.mc1 = cls.env['stock.lot'].create({
            'product_id': cls.metal_cylinder.id,
            'name': 'mc1',
            'company_id': cls.env.company.id,
        })
        cls.trapped_child = cls.env['product.product'].create({
            'name': 'Trapped child',
            'type': 'product',
            'tracking': 'none'})
        # Bill of material
        cls.bom_submarine = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.submarine_pod.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'Weld Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ]})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.elon_musk.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_submarine.id,
            'operation_id': cls.bom_submarine.operation_ids[1].id})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.trapped_child.id,
            'product_qty': 12.0,
            'bom_id': cls.bom_submarine.id})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.metal_cylinder.id,
            'product_qty': 2.0,
            'bom_id': cls.bom_submarine.id,
            'operation_id': cls.bom_submarine.operation_ids[0].id})
        cls.operation_4 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Rescue operation',
            'workcenter_id': cls.workcenter_1.id,
            'bom_id': cls.bom_submarine.id,
            'time_cycle': 13,
            'sequence': 2})
        #cls.mrp_routing_0 = cls.env['mrp.routing'].create({
        #    'name': 'Primary Assembly',
        #})
        #cls.mrp_routing_1 = cls.env['mrp.routing'].create({
        #    'name': 'Secondary Assembly',
        #})
        cls.mrp_workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Drill Station 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        # --------------
        # .mrp_routing_0
        # --------------
#        cls.mrp_routing_workcenter_0 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_0.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Manual Assembly',
#            'time_cycle': 60,
#        })
#
#        # -------------
#        # mpr_routing_1
#        # -------------
#        cls.mrp_routing_workcenter_1 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Long time assembly',
#            'time_cycle': 180,
#            'sequence': 15,
#        })
#        cls.mrp_routing_workcenter_3 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_3.id,
#            'name': 'Testing',
#            'time_cycle': 60,
#            'sequence': 10,
#        })
#        cls.mrp_routing_workcenter_4 = cls.env['mrp.routing.workcenter'].create({
#            #'routing_id': cls.mrp_routing_1.id,
#            'workcenter_id': cls.mrp_workcenter_1.id,
#            'name': 'Packing',
#            'time_cycle': 30,
#            'sequence': 5,
#        })

        # Update quantities
        cls.location_1 = cls.env.ref('stock.stock_location_stock')
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon1)
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon2)
        Quant._update_available_quantity(cls.elon_musk, cls.location_1, 1.0, lot_id=cls.elon3)
        Quant._update_available_quantity(cls.metal_cylinder, cls.location_1, 6.0, lot_id=cls.mc1)
        Quant._update_available_quantity(cls.trapped_child, cls.location_1, 36.0)

    def test_assign_1(self):
        unit = self.ref("uom.product_uom_unit")
        self.stock_location = self.env.ref('stock.stock_location_stock')
        custom_laptop = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
        })
        custom_laptop.tracking = 'none'
        product_charger = self.env['product.product'].create({
            'name': 'Charger',
            'type': 'product',
            'tracking': 'lot',
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
            #'routing_id': self.mrp_routing_0.id,
            # inlined mrp_routing0
            'bom_line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_qty': 1,
                'product_uom_id': unit
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_qty': 1,
                'product_uom_id': unit
            })],
            'operation_ids': [(0, 0, {
                'workcenter_id': self.mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = custom_laptop
        production_form.bom_id = bom_custom_laptop
        production_form.product_qty = 2
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        workorder = production.workorder_ids
        self.assertTrue(workorder)

        self.env['stock.quant']._update_available_quantity(product_charger, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(product_keybord, self.stock_location, 5)

        production.action_assign()

    def test_flexible_consumption_2(self):
        """ Production with a flexible consumption
        Check that consuming different quantities than planned doensn't trigger
        any error"""
        self.bom_submarine.consumption = 'flexible'

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.bom_id = self.bom_submarine
        mo_form.product_qty = 1
        mo = mo_form.save()

        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        sorted_workorder_ids = mo.workorder_ids.sorted()
        wo = sorted_workorder_ids[0]
        wo.button_start()
        wo.finished_lot_id = self.sp1
        self.assertEqual(wo.move_raw_ids.move_line_ids[0].lot_id, self.mc1, 'The suggested lot is wrong')
        wo.move_raw_ids.move_line_ids[0].quantity = 1
        wo.do_finish()

        wo = sorted_workorder_ids[1]
        wo.button_start()
        self.assertEqual(wo.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        self.assertEqual(wo.move_raw_ids.move_line_ids[0].lot_id, self.elon1, 'The suggested lot is wrong')
        wo.move_raw_ids.move_line_ids[0].quantity = 1
        wo.move_raw_ids.move_line_ids[0].copy({'lot_id': self.elon2.id, 'quantity': 1})
        wo.do_finish()

        wo = sorted_workorder_ids[2]
        wo.button_start()
        self.assertEqual(wo.finished_lot_id, self.sp1, 'The suggested final product is wrong')
        wo.do_finish()

        mo.move_raw_ids.filtered(lambda m: not m.operation_id).picked = True
        mo.button_mark_done()
        move_1 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.metal_cylinder and move.state == 'done')
        self.assertEqual(sum(move_1.mapped('quantity')), 1, 'Only one cylinder was consumed')
        move_2 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.elon_musk and move.state == 'done')
        self.assertEqual(sum(move_2.mapped('quantity')), 2, '2 Elon Musk was consumed')
        move_3 = mo.move_raw_ids.filtered(lambda move: move.product_id == self.trapped_child and move.state == 'done')
        self.assertEqual(sum(move_3.mapped('quantity')), 12, '12 child was consumed')
        self.assertEqual(mo.state, 'done', 'Final state of the MO should be "done"')

    def test_workorder_1(self):
        # get the computer sc234 demo data
        prod = self.submarine_pod
        bom = self.bom_submarine

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        # plan the work orders
        production.button_plan()

    def test_suggested_lot_in_multi_step(self):
        """Suggest the assigned lot in multi step system."""
        self.warehouse = self.env.ref('stock.warehouse0')
        self.env['quality.point'].create({
            'product_ids': [(4, self.submarine_pod.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_submarine.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.elon_musk.id,
        })
        self.warehouse.manufacture_steps = 'pbm'
        self.submarine_pod.tracking = 'none'
        self.bom_submarine.bom_line_ids.filtered(lambda l: l.product_id.id != self.elon_musk.id).unlink()
        self.bom_submarine.operation_ids[1:].unlink()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.submarine_pod
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()
        production.action_confirm()
        production.button_plan()

        production.picking_ids.action_assign()
        production.picking_ids.move_line_ids.lot_id = self.elon2
        production.picking_ids.button_validate()

        wo = production.workorder_ids
        wo.button_start()
        self.assertEqual(production.move_raw_ids.move_line_ids.lot_id, self.elon2, "Lot should be assigned.")
        self.assertEqual(wo.lot_id, self.elon2, "Lot should be set in the step")

    def test_step_by_product_variant(self):
        who_attr = self.env['product.attribute'].create({'name': 'Who?'})
        a1 = self.env['product.attribute.value'].create({'name': 'V0hFCg==', 'attribute_id': who_attr.id})
        a2 = self.env['product.attribute.value'].create({'name': 'QVJN', 'attribute_id': who_attr.id})
        a3 = self.env['product.attribute.value'].create({'name': 'UllW', 'attribute_id': who_attr.id})
        product_who = self.env['product.template'].create({
            'name': 'Odoo staff',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': who_attr.id,
                'value_ids': [(6, 0, [a1.id, a2.id, a3.id])],
            })]
        })
        product_a1 = product_who.product_variant_ids.filtered(lambda v: a1 in v.product_template_attribute_value_ids.product_attribute_value_id)
        product_a2 = product_who.product_variant_ids.filtered(lambda v: a2 in v.product_template_attribute_value_ids.product_attribute_value_id)
        product_a3 = product_who.product_variant_ids.filtered(lambda v: a3 in v.product_template_attribute_value_ids.product_attribute_value_id)

        bom_who = self.env['mrp.bom'].create({
            'code': 'To be ready',
            'product_tmpl_id': product_who.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.trapped_child.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'name': 'Be ready', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 60, 'sequence': 1}),
            ]
        })

        p1 = self.env['quality.point'].create({
            'product_ids': [(4, product_a1.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': bom_who.operation_ids[0].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'note': 'Installing VIM (pcs xi ipzth adi du ixbt)',
        })
        p2 = self.env['quality.point'].create({
            'product_ids': [(4, product_a2.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': bom_who.operation_ids[0].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'note': 'Taking lot of coffee with UElN',
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a1
        production_a1 = mrp_order_form.save()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a2
        production_a2 = mrp_order_form.save()

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = product_a3
        production_a3 = mrp_order_form.save()

        self.assertEqual(production_a1.bom_id, bom_who)
        self.assertEqual(production_a2.bom_id, bom_who)
        self.assertEqual(production_a3.bom_id, bom_who)

        production_a1.action_confirm()
        (production_a2 | production_a3).action_confirm()

        self.assertEqual(len(production_a1.workorder_ids.check_ids), 1)
        self.assertEqual(production_a1.workorder_ids.check_ids.point_id, p1)
        self.assertEqual(len(production_a2.workorder_ids.check_ids), 1)
        self.assertEqual(production_a2.workorder_ids.check_ids.point_id, p2)
        self.assertEqual(len(production_a3.workorder_ids.check_ids), 0)

    def test_add_workorder_into_a_backorder(self):
        """ Checks a new workorder can be created and processed into a backorder."""
        (self.submarine_pod | self.elon_musk | self.metal_cylinder).tracking = 'none'
        self.bom_submarine.consumption = 'flexible'

        def process_workorder(workorders, qty, next_and_finish=False):
            for wo in workorders:
                wo.button_start()
                wo_form = Form(wo, view='mrp_workorder.mrp_workorder_view_form_tablet')
                wo_form.qty_producing = qty
                wo = wo_form.save()
                if next_and_finish:
                    if wo.current_quality_check_id:
                        wo.current_quality_check_id._next()
                    wo.do_finish()
                elif wo.current_quality_check_id:
                    wo.current_quality_check_id.action_continue()

        # Creates a MO with 2 WO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.submarine_pod
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        # Processes partially the workorders.
        process_workorder(mo.workorder_ids.sorted(), 2)

        # Marks the MO as done and creates a backorder.
        action = mo.button_mark_done()
        backorder_form = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder_form.save().action_backorder()

        backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo.state, 'done')
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(len(backorder.workorder_ids), 3)
        self.assertEqual(backorder.workorder_ids.mapped('qty_production'), [8.0, 8.0, 8.0])

        # Adds a new WO in the backorder.
        mo_form = Form(backorder)
        with mo_form.workorder_ids.new() as wo_line:
            wo_line.name = "OP-SP"
            wo_line.workcenter_id = self.workcenter_1
        mo_form.save()

        # Again, processes partially the workorders.
        process_workorder(backorder.workorder_ids.sorted(), 5, True)

    def test_backorder_with_reserved_qty_in_sublocation(self):
        """
        Let's produce a MO based on a BoM with a storable component C and a
        workorder. There are some C available in a sublocation SL. The user
        reserves the needed quantities, then processes a part of the MO and
        creates a backorder. On the backorder, the production should be
        pre-completed: the qty_producing should be set and the consumed quantity
        of C should come from SL
        """
        location = self.location_1.child_ids[0]
        compo = self.bom_4.bom_line_ids.product_id
        compo.type = 'product'

        self.env['stock.quant']._update_available_quantity(compo, location, 3)

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo_form.product_qty = 3
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, 3)
        self.assertEqual(mo.move_raw_ids.move_line_ids.location_id, location)

        with Form(mo) as mo_form:
            mo_form.qty_producing = 1

        action = mo.button_mark_done()
        backorder_form = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder_form.save().action_backorder()
        backorder = mo.procurement_group_id.mrp_production_ids[1]

        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, 1)
        self.assertEqual(mo.move_raw_ids.move_line_ids.location_id, location)
        self.assertEqual(backorder.move_raw_ids.move_line_ids.quantity, 2)
        self.assertEqual(backorder.move_raw_ids.move_line_ids.location_id, location)

        with Form(backorder) as bo_form:
            bo_form.qty_producing = 2
        self.assertEqual(backorder.move_raw_ids.move_line_ids.quantity, 2)
        self.assertEqual(backorder.move_raw_ids.move_line_ids.location_id, location)

        backorder.button_mark_done()

        self.assertEqual(backorder.state, 'done')
        self.assertEqual(backorder.move_raw_ids.state, 'done')
        self.assertEqual(backorder.move_raw_ids.move_line_ids.quantity, 2)
        self.assertEqual(backorder.move_raw_ids.move_line_ids.location_id, location)

    def test_split_mo_finished_wo_transition(self):
        """ Check that if WOs are done out of order, then backordered/split WOs are not
        started when they should not be started
        """
        simple_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'OP1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'OP2', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 12, 'sequence': 1}),
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.bom_id = simple_bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()

        action = mo.action_split()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.counter = 2
        action = wizard.save().action_split()
        # Should have 2 mos w/ 2 wos each
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        mo2 = mo.procurement_group_id.mrp_production_ids[1]
        self.assertEqual(len(mo.workorder_ids), 2)
        self.assertEqual(len(mo2.workorder_ids), 2)
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(mo2.state, 'confirmed')
        wo1_1, wo1_2 = mo.workorder_ids.sorted()
        wo2_1, wo2_2 = mo2.workorder_ids.sorted()
        self.assertEqual(wo1_1.state, 'ready')
        self.assertEqual(wo1_2.state, 'pending')
        self.assertEqual(wo2_1.state, 'ready')
        self.assertEqual(wo2_2.state, 'pending')

        wo1_1.qty_producing = 1
        wo1_1.do_finish()
        self.assertEqual(wo1_1.state, 'done')
        self.assertEqual(wo1_2.state, 'ready')
        self.assertEqual(wo2_1.state, 'progress', "Completion of first MO's WOs should auto-started second MO's first WO")
        self.assertEqual(wo2_2.state, 'pending')
        wo1_2.do_finish()
        self.assertEqual(wo1_1.state, 'done')
        self.assertEqual(wo1_2.state, 'done')
        self.assertEqual(wo2_1.state, 'progress')
        self.assertEqual(wo2_2.state, 'pending', "Completion of first MO's WOs should not affect backordered pending WO")
        self.assertEqual(mo.state, 'to_close')

    def test_workorder_tracked_final_product(self):
        """
        Suppose that you have an MO for a prodcut tracked by SN with two operations.
        Check that you can mark the operations as done without registering an SN.
        """
        tracked_product = self.env['product.product'].create({
            'name': 'Final product',
            'type': 'product',
            'tracking': 'serial',
        })
        comp_1, comp_2 = self.product_1, self.product_2
        (comp_1 | comp_2).type = 'product'
        self.env['stock.quant']._update_available_quantity(comp_1, self.env.ref("stock.warehouse0").lot_stock_id, 5)
        self.env['stock.quant']._update_available_quantity(comp_2, self.env.ref("stock.warehouse0").lot_stock_id, 5)
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': tracked_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({'name': 'OP1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                Command.create({'name': 'OP2', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 12, 'sequence': 1}),
            ],
            'bom_line_ids': [
                Command.create({'product_id': comp_1.id, 'product_qty': 1}),
                Command.create({'product_id': comp_2.id, 'product_qty': 1}),
            ],
        })
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0]
        bom.bom_line_ids[1].operation_id = bom.operation_ids[1]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        # Operation 1 & 2: consume components and mark as done
        raw_move_1, raw_move_2 = mo.move_raw_ids
        operation_1, operation_2 = mo.workorder_ids
        operation_1.button_start()
        operation_1.qty_producing = 1.0
        raw_move_1.move_line_ids[0].quantity = 1.0
        operation_1.do_finish()
        self.assertRecordValues(operation_1, [{'qty_produced': 1.0, 'finished_lot_id': False, 'state': 'done'}])
        operation_2.button_start()
        operation_2.qty_producing = 1.0
        raw_move_2.move_line_ids[0].quantity = 1.0
        operation_2.do_finish()
        self.assertRecordValues(operation_2, [{'qty_produced': 1.0, 'finished_lot_id': False, 'state': 'done'}])
        self.assertEqual(mo.state, 'to_close')
        # Try to finish the production without assigning an SN
        mo.move_raw_ids.filtered(lambda m: not m.operation_id).picked = True
        with self.assertRaises(UserError):
            mo.button_mark_done()
        # Assign an SN and mark the production as done
        mo.action_generate_serial()
        self.assertEqual(operation_1.finished_lot_id, mo.lot_producing_id)
        self.assertEqual(operation_2.finished_lot_id, mo.lot_producing_id)
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')


@tagged("post_install", "-at_install")
class TestShopFloor(HttpCase, TestMrpWorkorderCommon):

    def test_access_shop_floor_with_multicomany(self):
        """
            test the flow when we have multicompany situation and
            we want to access shop floor from a company after switching
            from the other one.
        """
        company1 = self.env['res.company'].create({'name': 'Test Company'})
        user_admin = self.env.ref('base.user_admin')
        user_admin.write({
            'company_ids': [(4, company1.id)],
            'groups_id': [(4, self.env.ref('mrp.group_mrp_routings').id)],
        })
        submarine_pod = self.env['product.product'].with_company(company1).with_user(user_admin).create({
            'name': 'Submarine pod',
            'type': 'product',
            'tracking': 'serial'})
        workcenter_2 = self.env['mrp.workcenter'].with_company(company1).with_user(user_admin).create({
            'name': 'Nuclear Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        bom_submarine = self.env['mrp.bom'].with_company(company1).with_user(user_admin).create({
            'product_tmpl_id': submarine_pod.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': workcenter_2.id,
                 'time_cycle': 12, 'sequence': 1}),
            ]})
        mo_form = Form(self.env['mrp.production'].with_company(
            company1).with_user(user_admin))
        mo_form.product_id = submarine_pod
        mo_form.bom_id = bom_submarine
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()
        self.start_tour(
            "/", 'test_access_shop_floor_with_multicomany', login="admin")
