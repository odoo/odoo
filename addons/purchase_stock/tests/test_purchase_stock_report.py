# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestPurchaseStockReports(TestReportsCommon):
    def test_report_forecast_1_purchase_order_multi_receipt(self):
        """ Create a PO for 5 product, receive them then increase the quantity to 10.
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 5
        po = po_form.save()

        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0, "Must have 0 line for now.")
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 5)
        self.assertEqual(pending_qty_in, 5)

        # Confirms the PO and checks the report again.
        po.button_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['quantity'], 5)
        self.assertEqual(lines[0]['document_out'], False)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Receives 5 products.
        receipt = po.picking_ids
        res_dict = receipt.button_validate()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Increase the PO quantity to 10, so must create a second receipt.
        po_form = Form(po)
        with po_form.order_line.edit(0) as line:
            line.product_qty = 10
        po = po_form.save()
        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1, "Must have 1 line for now.")
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['quantity'], 5)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

    def test_report_forecast_2_purchase_order_three_step_receipt(self):
        """ Create a PO for 4 product, receive them then increase the quantity
        to 10, but use three steps receipt.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        # Configure warehouse.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'three_steps'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 4
        po = po_form.save()

        # Checks the report -> Must be empty for now, just display some pending qty.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0, "Must have 0 line for now.")
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 4)
        self.assertEqual(pending_qty_in, 4)

        # Confirms the PO and checks the report again.
        po.button_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['quantity'], 4)
        self.assertEqual(lines[0]['document_out'], False)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)
        # Get back the different transfers.
        receipt = po.picking_ids

        # Receives 4 products.
        res_dict = receipt.button_validate()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)

        # Increase the PO quantity to 10, so must create a second receipt.
        po_form = Form(po)
        with po_form.order_line.edit(0) as line:
            line.product_qty = 10
        po = po_form.save()
        # Checks the report.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty_in = docs['draft_picking_qty']['in']
        draft_purchase_qty = docs['draft_purchase_qty']
        pending_qty_in = docs['qty']['in']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['quantity'], 6)
        self.assertEqual(draft_picking_qty_in, 0)
        self.assertEqual(draft_purchase_qty, 0)
        self.assertEqual(pending_qty_in, 0)
