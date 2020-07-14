# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestSaleStockReports(TestReportsCommon):
    def test_report_forecast_1_mo_count(self):
        """ Creates and configures a product who could be produce and could be a component.
        Plans some producing and consumming MO and check the report values.
        """
        # Create a variant attribute.
        product_chocolate = self.env['product.product'].create({
            'name': 'Chocolate',
            'type': 'consu',
        })
        product_chococake = self.env['product.product'].create({
            'name': 'Choco Cake',
            'type': 'product',
        })
        product_double_chococake = self.env['product.product'].create({
            'name': 'Double Choco Cake',
            'type': 'product',
        })

        # Creates two BOM: one creating a regular slime, one using regular slimes.
        bom_chococake = self.env['mrp.bom'].create({
            'product_id': product_chococake.id,
            'product_tmpl_id': product_chococake.product_tmpl_id.id,
            'product_uom_id': product_chococake.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_chocolate.id, 'product_qty': 4}),
            ],
        })
        bom_double_chococake = self.env['mrp.bom'].create({
            'product_id': product_double_chococake.id,
            'product_tmpl_id': product_double_chococake.product_tmpl_id.id,
            'product_uom_id': product_double_chococake.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_chococake.id, 'product_qty': 2}),
            ],
        })

        # Creates two MO: one for each BOM.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_chococake
        mo_form.bom_id = bom_chococake
        mo_form.product_qty = 10
        mo_1 = mo_form.save()
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_double_chococake
        mo_form.bom_id = bom_double_chococake
        mo_form.product_qty = 2
        mo_2 = mo_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_chococake.product_tmpl_id.ids)
        draft_picking_qty = docs['draft_picking_qty']
        draft_production_qty = docs['draft_production_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(draft_production_qty['in'], 10)
        self.assertEqual(draft_production_qty['out'], 4)

        # Confirms the MO and checks the report lines.
        mo_1.action_confirm()
        mo_2.action_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_chococake.product_tmpl_id.ids)
        draft_picking_qty = docs['draft_picking_qty']
        draft_production_qty = docs['draft_production_qty']
        self.assertEqual(len(lines), 2, "Must have two line.")
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['document_in'].id, mo_1.id)
        self.assertEqual(line_1['quantity'], 4)
        self.assertEqual(line_1['document_out'].id, mo_2.id)
        self.assertEqual(line_2['document_in'].id, mo_1.id)
        self.assertEqual(line_2['quantity'], 6)
        self.assertEqual(line_2['document_out'], False)
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(draft_production_qty['in'], 0)
        self.assertEqual(draft_production_qty['out'], 0)

    def test_report_forecast_2_production_backorder(self):
        """ Creates a manufacturing order and produces half the quantity.
        Then creates a backorder and checks the report.
        """
        # Configures the warehouse.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.manufacture_steps = 'pbm_sam'
        # Configures a product.
        product_apple_pie = self.env['product.product'].create({
            'name': 'Apple Pie',
            'type': 'product',
        })
        product_apple = self.env['product.product'].create({
            'name': 'Apple',
            'type': 'consu',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': product_apple_pie.id,
            'product_tmpl_id': product_apple_pie.product_tmpl_id.id,
            'product_uom_id': product_apple_pie.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_apple.id, 'product_qty': 5}),
            ],
        })
        # Creates a MO and validates the pick components.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_apple_pie
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo_1 = mo_form.save()
        mo_1.action_confirm()
        pick = mo_1.move_raw_ids.move_orig_ids.picking_id
        pick_form = Form(pick)
        with pick_form.move_line_ids_without_package.edit(0) as move_line:
            move_line.qty_done = 20
        pick = pick_form.save()
        pick.button_validate()
        # Produces 3 products then creates a backorder for the remaining product.
        mo_form = Form(mo_1)
        mo_form.qty_producing = 3
        mo_1 = mo_form.save()
        action = mo_1.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder = backorder_form.save()
        backorder.action_backorder()

        mo_2 = (mo_1.procurement_group_id.mrp_production_ids - mo_1)
        # Checks the forecast report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1, "Must have only one line about the backorder")
        self.assertEqual(lines[0]['document_in'].id, mo_2.id)
        self.assertEqual(lines[0]['quantity'], 1)
        self.assertEqual(lines[0]['document_out'], False)

        # Produces the last unit.
        mo_form = Form(mo_2)
        mo_form.qty_producing = 1
        mo_2 = mo_form.save()
        mo_2.button_mark_done()
        # Checks the forecast report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 0, "Must have no line")
