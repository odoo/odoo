# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestMrpStockReports(TestReportsCommon):
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
        byproduct = self.env['product.product'].create({
            'name': 'by-product',
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
            'byproduct_ids':
                [(0, 0, {'product_id': byproduct.id, 'product_qty': 2})],
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
        self.assertEqual(line_1['document_in']['id'], mo_1.id)
        self.assertEqual(line_1['quantity'], 4)
        self.assertEqual(line_1['document_out']['id'], mo_2.id)
        self.assertEqual(line_2['document_in']['id'], mo_1.id)
        self.assertEqual(line_2['quantity'], 6)
        self.assertEqual(line_2['document_out'], False)
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(draft_production_qty['in'], 0)
        self.assertEqual(draft_production_qty['out'], 0)

        mo_form = Form(mo_1)
        mo_form.qty_producing = 10
        mo_form.save()
        mo_1.move_byproduct_ids.quantity = 18
        mo_1.button_mark_done()

        self.env.flush_all()  # flush to correctly build report
        report_values = self.env['report.mrp.report_mo_overview']._get_report_data(mo_1.id)['byproducts']['details'][0]
        self.assertEqual(report_values['name'], byproduct.name)
        self.assertEqual(report_values['quantity'], 18)

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
        pick.picking_type_id.show_operations = True  # Could be false without demo data, as the lot group is disabled
        pick_form = Form(pick)
        with Form(pick.move_ids_without_package, view='stock.view_stock_move_operations') as form:
            with form.move_line_ids.edit(0) as move_line:
                move_line.quantity = 20
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
        self.assertEqual(lines[0]['document_in']['id'], mo_2.id)
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

    def test_report_forecast_3_report_line_corresponding_to_mo_highlighted(self):
        """ When accessing the report from a MO, checks if the correct MO is highlighted in the report
        """
        product_banana = self.env['product.product'].create({
            'name': 'Banana',
            'type': 'product',
        })
        product_chocolate = self.env['product.product'].create({
            'name': 'Chocolate',
            'type': 'consu',
        })

        # We create 2 identical MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_banana
        mo_form.product_qty = 10
        with mo_form.move_raw_ids.new() as move:
            move.product_id = product_chocolate

        mo_1 = mo_form.save()
        mo_2 = mo_1.copy()
        (mo_1 | mo_2).action_confirm()

        # Check for both MO if the highlight (is_matched) corresponds to the correct MO
        for mo in [mo_1, mo_2]:
            context = mo.action_product_forecast_report()['context']
            _, _, lines = self.get_report_forecast(product_template_ids=product_banana.product_tmpl_id.ids, context=context)
            for line in lines:
                if line['document_in']['id'] == mo.id:
                    self.assertTrue(line['is_matched'], "The corresponding MO line should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the MO shoud not be matched.")

    def test_kit_packaging_delivery_slip(self):
        superkit = self.env['product.product'].create({
            'name': 'Super Kit',
            'type': 'consu',
            'packaging_ids': [(0, 0, {
                'name': '6-pack',
                'qty': 6,
            })],
        })

        compo01, compo02 = self.env['product.product'].create([{
            'name': n,
            'type': 'product',
            'uom_id': self.env.ref('uom.product_uom_meter').id,
            'uom_po_id': self.env.ref('uom.product_uom_meter').id,
        } for n in ['Compo 01', 'Compo 02']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': superkit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1}),
            ],
        })

        for back_order, expected_vals in [('never', [12, 12, 2, 2]), ('always', [24, 12, 4, 2])]:
            picking_form = Form(self.env['stock.picking'])
            picking_form.picking_type_id = self.picking_type_in
            picking_form.partner_id = self.partner
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = superkit
                move.product_uom = self.env.ref('uom.product_uom_dozen')
                move.product_uom_qty = 2
            picking = picking_form.save()
            picking.move_ids.product_packaging_id = superkit.packaging_ids
            picking.action_confirm()

            picking.move_ids.write({'quantity': 12, 'picked': True})
            picking.picking_type_id.create_backorder = back_order
            picking.button_validate()
            non_kit_aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
            self.assertFalse(non_kit_aggregate_values)
            aggregate_values = picking.move_line_ids._get_aggregated_product_quantities(kit_name=superkit.display_name)
            for line in aggregate_values.values():
                self.assertItemsEqual([line[val] for val in ['qty_ordered', 'quantity', 'packaging_qty', 'packaging_quantity']], expected_vals)

            html_report = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', picking.ids)[0]
            self.assertTrue(html_report, "report generated successfully")

    def test_subkit_in_delivery_slip(self):
        """
        Suppose this structure:
        Super Kit --|- Compo 01 x1
                    |- Sub Kit x1 --|- Compo 02 x1
                    |               |- Compo 03 x1

        This test ensures that, when delivering one Super Kit, one Sub Kit, one Compo 01 and one Compo 02,
        and when putting in pack the third component of the Super Kit, the delivery report is correct.
        """
        compo01, compo02, compo03, subkit, superkit = self.env['product.product'].create([{
            'name': n,
            'type': 'consu',
        } for n in ['Compo 01', 'Compo 02', 'Compo 03', 'Sub Kit', 'Super Kit']])

        self.env['mrp.bom'].create([{
            'product_tmpl_id': subkit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo02.id, 'product_qty': 1}),
                (0, 0, {'product_id': compo03.id, 'product_qty': 1}),
            ],
        }, {
            'product_tmpl_id': superkit.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1}),
                (0, 0, {'product_id': subkit.id, 'product_qty': 1}),
            ],
        }])

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        picking_form.partner_id = self.partner
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = superkit
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = subkit
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = compo01
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = compo02
            move.product_uom_qty = 1
        picking = picking_form.save()
        picking.action_confirm()

        picking.move_ids.write({'quantity': 1, 'picked': True})
        move = picking.move_ids.filtered(lambda m: m.name == "Super Kit" and m.product_id == compo03)
        move.move_line_ids.result_package_id = self.env['stock.quant.package'].create({'name': 'Package0001'})
        picking.button_validate()

        html_report = self.env['ir.actions.report']._render_qweb_html(
            'stock.report_deliveryslip', picking.ids)[0].decode('utf-8').split('\n')
        keys = [
            "Package0001", "Compo 03",
            "Products with no package assigned", "Compo 01", "Compo 02",
            "Super Kit", "Compo 01",
            "Sub Kit", "Compo 02", "Compo 03",
        ]
        for line in html_report:
            if not keys:
                break
            if keys[0] in line:
                keys = keys[1:]


        self.assertFalse(keys, "All keys should be in the report with the defined order")

    def test_mo_overview(self):
        """ Test that the overview does not traceback when the final produced qty is 0
        """
        product_chocolate = self.env['product.product'].create({
            'name': 'Chocolate',
            'type': 'consu',
        })
        product_chococake = self.env['product.product'].create({
            'name': 'Choco Cake',
            'type': 'product',
        })
        self.env['mrp.bom'].create({
            'product_id': product_chococake.id,
            'product_tmpl_id': product_chococake.product_tmpl_id.id,
            'product_uom_id': product_chococake.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_chocolate.id, 'product_qty': 4}),
            ],
        })
        mo = self.env['mrp.production'].create({
            'name': 'MO',
            'product_qty': 1.0,
            'product_id': product_chococake.id,
        })

        mo.action_confirm()
        mo.button_mark_done()
        mo.qty_produced = 0.

        overview_values = self.env['report.mrp.report_mo_overview'].get_report_values(mo.id)
        self.assertEqual(overview_values['data']['id'], mo.id, "computing overview value should work")

    def test_multi_step_component_forecast_availability(self):
        """
        Test that the component availability is correcly forecasted
        in multi step manufacturing
        """
        # Configures the warehouse.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.manufacture_steps = 'pbm_sam'
        final_product, component = self.product, self.product1
        bom = self.env['mrp.bom'].create({
            'product_id': final_product.id,
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_uom_id': final_product.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 10}),
            ],
        })
        # Creates a MO without any component in stock
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.components_availability, 'Not Available')
        self.assertEqual(mo.move_raw_ids.forecast_availability, -20.0)
        self.env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, 100)
        # change the qty_producing to force a recompute of the availability
        with Form(mo) as mo_form:
            mo_form.qty_producing = 2.0
        self.assertEqual(mo.components_availability, 'Available')
