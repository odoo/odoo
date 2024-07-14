# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo import Command


class TestQuality(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})

        cls.product_1 = cls.env['product.product'].create({'name': 'Table'})
        cls.product_2 = cls.env['product.product'].create({'name': 'Table top'})
        cls.product_3 = cls.env['product.product'].create({'name': 'Table leg'})
        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_1.id,
            'product_tmpl_id': cls.product_1.product_tmpl_id.id,
            'product_uom_id': cls.product_1.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'name': 'Assembly', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.product_3.id, 'product_qty': 4})
            ]
        })

    def test_quality_point_onchange(self):
        quality_point_form = Form(self.env['quality.point'].with_context(default_product_ids=[self.product_2.id]))
        # Form should keep the default products set
        self.assertEqual(len(quality_point_form.product_ids), 1)
        self.assertEqual(quality_point_form.product_ids[0].id, self.product_2.id)
        # <field name="operation_id" invisible="not is_workorder_step"/>
        # @api.depends('operation_id', 'picking_type_ids')
        # def _compute_is_workorder_step(self):
        #     for quality_point in self:
        #         quality_point.is_workorder_step = quality_point.operation_id or quality_point.picking_type_ids and\
        #             all(pt.code == 'mrp_operation' for pt in quality_point.picking_type_ids)
        quality_point_form.picking_type_ids.add(
            self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        )
        # Select a workorder operation
        quality_point_form.operation_id = self.bom.operation_ids[0]
        # Product should be replaced by the product linked to the bom
        self.assertEqual(len(quality_point_form.product_ids), 1)
        self.assertEqual(quality_point_form.product_ids[0].id, self.bom.product_id.id)

    def test_quality_check_action_next_when_no_move_line(self):
        """
        Process a MO based on a BoM with one operation. That operation has two steps
        step1: Call action_continue method to  create a quality check with no move line
        step2: Call action_next method to create a new move line if no move line
        """
        self.env['quality.point'].create({
            'title': 'Qp1',
            'product_ids': [(4, self.product_1.id, 0)],
            'operation_id': self.bom.operation_ids.id,
            'component_id': self.product_2.id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id
            })
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom
        mo = mo_form.save()
        mo.action_confirm()

        mo.workorder_ids.current_quality_check_id.action_continue()
        self.assertEqual(len(mo.workorder_ids.check_ids), 2)
        # Check the current quality check has no move line
        self.assertEqual(len(mo.workorder_ids.check_ids[1].move_line_id), 0)
        mo.workorder_ids.current_quality_check_id.write({'qty_done': 5})
        mo.workorder_ids.current_quality_check_id.action_next()
        # check a new move line is created or not for the above quality check record
        self.assertEqual(len(mo.workorder_ids.check_ids[1].move_line_id), 1)

    def test_delete_move_linked_to_quality_check(self):
        """
        Test that a quality check is deleted when its linked move is deleted.
        """
        self.bom.bom_line_ids.product_id.tracking = 'lot'
        self.bom.bom_line_ids.product_id.type = 'product'
        self.bom.operation_ids[0].quality_point_ids = [Command.create({
            'product_ids': [(4, self.product_1.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.product_2.id,
        })]
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom
        mo = mo_form.save()
        mo.action_confirm()
        qc = self.env['quality.check'].search([('product_id', '=', self.bom.product_id.id)])[-1]
        move = qc.move_id
        self.assertEqual(len(qc), 1)
        self.assertFalse(move.move_line_ids)
        move.state = 'draft'
        move.unlink()
        self.assertFalse(move.exists())
        self.assertFalse(qc.exists())
