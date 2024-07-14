# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests.common import Form


class TestMrpReportEmployeeCost(TestMrpCommon):
    @freeze_time("2022-05-28")
    def test_mrp_report_no_operations(self):
        """
        Check that the operation cost is 0 when we don't have any operations.

        - Final product Bom structure:
            - product_4: qty: 2, cost: $20
            - product_3: qty: 3, cost: $50

        MO:
            - qty to produce: 10 units
            - work_order duration: 0
            unit_component_cost = ((20 * 2) + (50 * 3)) = 190
            unit_duration = 0
            unit_operation_cost = 0
            unit_cost = 190
        """

        # Make some stock and reserve
        for product in self.bom_2.bom_line_ids.product_id:
            self.env["stock.quant"].with_context(inventory_mode=True).create(
                {
                    "product_id": product.id,
                    "inventory_quantity": 1000,
                    "location_id": self.stock_location_components.id,
                }
            )._apply_inventory()

        # Remove operations
        self.bom_2.operation_ids = [Command.clear()]

        # MO
        self.product_4.standard_price = 20
        self.product_3.standard_price = 50
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_2
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
        self.assertEqual(report["unit_component_cost"], 190)
        self.assertEqual(report["unit_cost"], 190)
