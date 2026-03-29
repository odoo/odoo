# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form
from odoo.addons.mail.tests.common import mail_new_test_user
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

    def test_report_forecast_3_report_line_corresponding_to_po_line_highlighted(self):
        """ When accessing the report from a PO line, checks if the correct PO line is highlighted in the report
        """
        # We create 2 identical PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 5
        po1 = po_form.save()
        po1.button_confirm()
        po2 = po1.copy()
        po2.button_confirm()

        # Check for both PO if the highlight (is_matched) corresponds to the correct PO
        for po in [po1, po2]:
            context = po.order_line[0].action_product_forecast_report()['context']
            _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids, context=context)
            for line in lines:
                if line['document_in'] == po:
                    self.assertTrue(line['is_matched'], "The corresponding PO line should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the PO shoud not be matched.")

    def test_approval_and_forecasted_qty(self):
        """
        When a PO is waiting for an approval, its quantities should be included
        in the draft quantity count
        """
        self.env.company.po_double_validation = 'two_step'
        self.env.company.po_double_validation_amount = 0

        basic_purchase_user = mail_new_test_user(
            self.env,
            login='basic_purchase_user',
            groups='base.group_user,purchase.group_purchase_user',
        )

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 50
        po_form.save()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 100
        po = po_form.save()
        po.with_user(basic_purchase_user).button_confirm()

        docs = self.get_report_forecast(product_template_ids=self.product_template.ids)[1]
        self.assertEqual(docs['draft_purchase_qty'], 150)

    def test_vendor_delay_report_with_uom(self):
        """
        PO 12 units x P
        Receive 1 dozen x P
        -> 100% received
        """
        uom_12 = self.env.ref('uom.product_uom_dozen')

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 12
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt_move = receipt.move_lines
        receipt_move.move_line_ids.unlink()
        receipt_move.move_line_ids = [(0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': receipt_move.location_dest_id.id,
            'product_id': self.product.id,
            'product_uom_id': uom_12.id,
            'qty_done': 1,
            'picking_id': receipt.id,
        })]
        receipt.button_validate()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 12)
        self.assertEqual(data['qty_total'], 12)
        self.assertEqual(data['on_time_rate'], 100)

    def test_vendor_delay_report_with_multi_location(self):
        """
        PO 10 units x P
        Receive
            - 6 x P in Child Location 01
            - 4 x P in Child Location 02
        -> 100% received
        """
        if not self.stock_location.child_ids:
            self.env['stock.location'].create([{
                'name': 'Shelf 1',
                'location_id': self.stock_location.id,
            }, {
                'name': 'Shelf 2',
                'location_id': self.stock_location.id,
            }])

        child_loc_01, child_loc_02 = self.stock_location.child_ids

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt_move = receipt.move_lines
        receipt_move.move_line_ids.unlink()
        receipt_move.move_line_ids = [(0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': child_loc_01.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 6,
            'picking_id': receipt.id,
        }), (0, 0, {
            'location_id': receipt_move.location_id.id,
            'location_dest_id': child_loc_02.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'qty_done': 4,
            'picking_id': receipt.id,
        })]
        receipt.button_validate()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 10)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 100)

    def test_vendor_delay_report_with_backorder(self):
        """
        PO 10 units x P
        Receive 6 x P with backorder
        -> 60% received
        Process the backorder
        -> 100% received
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01_move = receipt01.move_lines
        receipt01_move.quantity_done = 6
        action = receipt01.button_validate()
        Form(self.env[action['res_model']].with_context(action['context'])).save().process()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 6)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 60)

        receipt02 = receipt01.backorder_ids
        receipt02.move_lines.quantity_done = 4
        receipt02.button_validate()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 10)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 100)

    def test_vendor_delay_report_without_backorder(self):
        """
        PO 10 units x P
        Receive 6 x P without backorder
        -> 60% received
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner
        with po_form.order_line.new() as line:
            line.product_id = self.product
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01_move = receipt01.move_lines
        receipt01_move.quantity_done = 6
        action = receipt01.button_validate()
        Form(self.env[action['res_model']].with_context(action['context'])).save().process_cancel_backorder()

        data = self.env['vendor.delay.report'].read_group(
            [('partner_id', '=', self.partner.id)],
            ['product_id', 'on_time_rate', 'qty_on_time', 'qty_total'],
            ['product_id'],
        )[0]
        self.assertEqual(data['qty_on_time'], 6)
        self.assertEqual(data['qty_total'], 10)
        self.assertEqual(data['on_time_rate'], 60)
