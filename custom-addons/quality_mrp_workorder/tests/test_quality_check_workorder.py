# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import Form, HttpCase, tagged, loaded_demo_data
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.mrp_workorder.tests import test_tablet_client_action
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TestQualityCheckWorkorder(TestMrpCommon):

    def test_01_quality_check_with_component_consumed_in_operation(self):
        """ Test quality check on a production with a component consumed in one operation
        """

        picking_type_id = self.env.ref('stock.warehouse0').manu_type_id.id
        component = self.env['product.product'].create({
            'name': 'consumable component',
            'type': 'consu',
        })
        bom = self.bom_2.copy()
        bom.bom_line_ids[0].product_id = component

        # Registering the first component in the operation of the BoM
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0]

        # Create Quality Point for the product consumed in the operation of the BoM
        self.env['quality.point'].create({
            'product_ids': [bom.bom_line_ids[0].product_id.id],
            'picking_type_ids': [picking_type_id],
            'measure_on': 'move_line',
        })
        # Create Quality Point for all products (that should not apply on components)
        self.env['quality.point'].create({
            'product_ids': [],
            'picking_type_ids': [picking_type_id],
            'measure_on': 'move_line',
        })

        # Create Production of Painted Boat to produce 5.0 Unit.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = bom.product_id
        production_form.bom_id = bom
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()
        production.qty_producing = 3.0

        # Check that the Quality Check were created and has correct values
        self.assertEqual(len(production.move_raw_ids[0].move_line_ids.check_ids), 1)
        self.assertEqual(len(production.move_raw_ids[1].move_line_ids.check_ids), 0)
        self.assertEqual(len(production.check_ids.filtered(lambda qc: qc.product_id == production.product_id)), 1)
        self.assertEqual(len(production.check_ids), 2)

    def test_register_consumed_materials(self):
        """
        Process a MO based on a BoM with one operation. That operation has one
        step: register the used component. Both finished product and component
        are tracked by serial. The auto-completion of the serial numbers should
        be correct
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        finished = self.bom_4.product_id
        component = self.bom_4.bom_line_ids.product_id
        (finished | component).write({
            'type': 'product',
            'tracking': 'serial',
        })

        finished_sn, component_sn = self.env['stock.lot'].create([{
            'name': p.name,
            'product_id': p.id,
            'company_id': self.env.company.id,
        } for p in (finished, component)])
        self.env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, 1, lot_id=component_sn)

        type_register_materials = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
        operation = self.env['mrp.routing.workcenter'].create({
            'name': 'Super Operation',
            'bom_id': self.bom_4.id,
            'workcenter_id': self.workcenter_2.id,
            'quality_point_ids': [(0, 0, {
                'product_ids': [(4, finished.id)],
                'picking_type_ids': [(4, warehouse.manu_type_id.id)],
                'test_type_id': type_register_materials.id,
                'component_id': component.id,
                'bom_id': self.bom_4.id,
                'measure_on': 'operation',
            })]
        })
        self.bom_4.operation_ids = [(6, 0, operation.ids)]

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()

        mo_form = Form(mo)
        mo_form.lot_producing_id = finished_sn
        mo = mo_form.save()

        self.assertEqual(mo.workorder_ids.finished_lot_id, finished_sn)
        self.assertEqual(mo.workorder_ids.lot_id, component_sn)

        mo.workorder_ids.current_quality_check_id.action_next()
        mo.workorder_ids.do_finish()
        mo.button_mark_done()

        self.assertRecordValues(mo.move_raw_ids.move_line_ids + mo.move_finished_ids.move_line_ids, [
            {'quantity': 1, 'lot_id': component_sn.id},
            {'quantity': 1, 'lot_id': finished_sn.id},
        ])

    def test_backorder_cancelled_workorder_quality_check(self):
        """ Create an MO based on a bom with 2 operations, when processing workorders,
            process one workorder fully and the other partially, then confirm and create backorder
            the fully finished workorder copy should be cancelled without any checks to do, and the other
            should ready, we should be able to pass the checks and produce the backorder
        """
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'operation_ids': [
                (0, 0, {'name': 'Cut', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'Weld', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ],
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_3.id, 'product_qty': 2}),
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 3}),
            ]
        })
        operation_ids = bom.operation_ids
        self.env['stock.quant'].create([
            {
                'product_id': self.product_3.id,
                'product_uom_id': self.uom_unit.id,
                'location_id': self.location_1.id,
                'quantity': 4,
            },
            {
                'product_id': self.product_2.id,
                'product_uom_id': self.uom_unit.id,
                'location_id': self.location_1.id,
                'quantity': 6,
            },
        ])
        self.env['quality.point'].create([
            {
                'title': 'test QP1',
                'product_ids': [(4, self.product_6.id, 0)],
                'operation_id': operation_ids[0].id,
                'note': 'Cut',
            },
            {
                'title': 'test QP2',
                'product_ids': [(4, self.product_6.id, 0)],
                'operation_id': operation_ids[1].id,
                'note': 'Weld',
            }
        ])
        mo = self.env['mrp.production'].create({
            'product_id': self.product_6.id,
            'product_qty': 2,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.workorder_ids), 2)
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        # 1 work order will produce the full 2 qty, the other will only produce 1
        full_workorder = mo.workorder_ids[0]
        full_workorder.qty_producing = 2
        full_workorder.check_ids.action_pass_and_next()
        full_workorder.button_finish()
        self.assertEqual(full_workorder.state, 'done')
        partial_workorder = mo.workorder_ids[1]
        partial_workorder.qty_producing = 1
        partial_workorder.check_ids.action_pass_and_next()
        partial_workorder.button_finish()
        self.assertEqual(partial_workorder.state, 'done')
        # MO qty_producing should become 1 since only 1 qty was fully produced
        self.assertEqual(mo.qty_producing, 1)
        action = mo.button_mark_done()
        backorder_form = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder_form.save().action_backorder()
        backorder = mo.procurement_group_id.mrp_production_ids[1]
        # the backorder has 1 qty to produce and the full workorder done from before should be cancelled (its a copy)
        # and should not have any quality check to perform
        self.assertEqual(backorder.product_qty, 1)
        self.assertEqual(len(backorder.workorder_ids), 2)
        self.assertEqual(backorder.workorder_ids[0].state, 'cancel')
        self.assertEqual(len(backorder.workorder_ids[0].check_ids), 0)
        backorder.workorder_ids[1].qty_producing = 1
        backorder.workorder_ids[1].check_ids.action_pass_and_next()
        backorder.workorder_ids[1].button_finish()
        backorder.button_mark_done()
        self.assertEqual(backorder.state, 'done')


@tagged('post_install', '-at_install')
class TestPickingWorkorderClientActionQuality(test_tablet_client_action.TestWorkorderClientActionCommon, HttpCase):

    def test_measure_quality_check(self):
        self.env['quality.point'].create({
            'title': 'Measure Wand Step',
            'product_ids': [(4, self.potion.id)],
            'picking_type_ids': [(4, self.picking_type_manufacturing.id)],
            'operation_id': self.wizard_op_1.id,
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'norm': 15,
            'tolerance_min': 14,
            'tolerance_max': 16,
            'sequence': 0,
            'note': '<p>Make sure your wand is the correct size for the "magic" to happen</p>',
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_potion
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = mo.product_qty

        self.assertEqual(mo.workorder_ids.check_ids.filtered(lambda x: x.test_type == 'measure').quality_state, 'none')

        res_action = mo.workorder_ids.check_ids.filtered(lambda x: x.test_type == 'measure').do_measure()

        self.assertEqual(mo.workorder_ids.check_ids.filtered(lambda x: x.test_type == 'measure').quality_state, 'fail', 'The measure quality check should have failed')
        self.assertEqual(res_action.get('res_model'), 'quality.check.wizard', 'The action should return a wizard when failing')

    def test_quantity_control_point_with_production(self):
        """Test that it's not possible to create a Quantity quality check type with a manufacturing operation type."""
        with self.assertRaises(UserError):
            self.qality_point_test1 = self.env['quality.point'].create({
                'picking_type_ids': [(4, self.picking_type_manufacturing.id)],
                'operation_id': self.wizard_op_1.id,
                'measure_on': 'move_line',
            })
