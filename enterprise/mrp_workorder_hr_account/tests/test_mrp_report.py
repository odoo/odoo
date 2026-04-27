# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form


class TestMrpReportEmployeeCost(TestMrpCommon):
    @freeze_time("2022-05-28")
    def test_mrp_report_no_operations(self):
        """
        Check that the operation cost is 0 when we don't have any operations.

        - Final product Bom structure:
            - product_1: qty: 1, cost: $20

        MO:
            - qty to produce: 10 units
            - work_order duration: 0
            unit_component_cost = $20
            unit_duration = 0
            unit_operation_cost = 0
            unit_cost = 180
        """


        # Remove operations
        self.bom_4.operation_ids = [Command.clear()]

        # MO
        self.product_1.standard_price = 20
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production_form.product_qty = 10
        mo = production_form.save()
        mo.action_confirm()

        mo_form = Form(mo)
        mo_form.qty_producing = 10
        mo = mo_form.save()
        mo.button_mark_done()

        # must flush else SQL request in report is not accurate
        self.env.flush_all()

        report = self.env["mrp.report"].search([("production_id", "=", mo.id)])

        self.assertEqual(report["unit_operation_cost"], 0)
        self.assertEqual(report["unit_duration"], 0)
        self.assertEqual(report["unit_component_cost"], 20)
        self.assertEqual(report["unit_cost"], 20)

    def test_mrp_report_expected_cost_fields(self):
        self.workcenter_2.write({
            'default_capacity': 2,
            'costs_hour': 20,
            'employee_costs_hour': 30,
        })
        comp_product = self.product_1
        comp_product.standard_price = 100
        bom_1_comp = self.bom_4
        bom_2_comp = self.bom_4.copy()
        bom_2_comp.product_qty = 2
        bom_2_comp.bom_line_ids.product_qty = 2

        mo_1 = self.env['mrp.production'].create({
            'product_qty': 1,
            'bom_id': bom_1_comp.id,
        })
        mo_1.action_assign()
        mo_1.button_plan()
        wo = mo_1.workorder_ids[0]
        wo.button_start()
        wo.record_production()
        mo_1.move_raw_ids.quantity = 1
        mo_1.move_raw_ids.picked = True
        mo_1.button_mark_done()
        mo_2 = self.env['mrp.production'].create({
            'product_qty': 2,
            'bom_id': bom_2_comp.id,
        })
        mo_2.action_assign()
        mo_2.button_plan()
        wo = mo_2.workorder_ids[0]
        wo.button_start()
        wo.record_production()
        mo_2.move_raw_ids.quantity = 2
        mo_2.move_raw_ids.picked = True
        mo_2.button_mark_done()
        self.env.flush_all() # second report record not created without flush
        self.assertRecordValues(
            self.env['mrp.report'].search([('production_id', 'in', (mo_1.id, mo_2.id))]),
            [{
                'expected_component_cost_unit':   100.0,
                'expected_employee_cost_unit':    30.0,
                'expected_operation_cost_unit':   20.0,
                'expected_total_cost_unit':       150.0
            } for _ in range(2)]
        )
