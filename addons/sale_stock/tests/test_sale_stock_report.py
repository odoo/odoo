# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo.tools import html2plaintext

from odoo.tests.common import Form, tagged
from odoo.addons.stock.tests.test_report import TestReportsCommon
from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleStockReports(TestReportsCommon):
    def test_report_forecast_1_sale_order_replenishment(self):
        """ Create and confirm two sale orders: one for the next week and one
        for tomorrow. Then check in the report it's the most urgent who is
        linked to the qty. on stock.
        """
        # make sure first picking doesn't auto-assign
        self.picking_type_out.reservation_method = 'manual'

        today = datetime.today()
        # Put some quantity in stock.
        quant_vals = {
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'quantity': 5,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(quant_vals)
        # Create a first SO for the next week.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=7)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_1 = so_form.save()
        so_1.action_confirm()
        so_1.picking_ids.scheduled_date = today + timedelta(days=7)

        # Create a second SO for tomorrow.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=1)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_2 = so_form.save()
        so_2.action_confirm()
        so_2.picking_ids.scheduled_date = today + timedelta(days=1)

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 2)
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['quantity'], 5)
        self.assertTrue(line_1['replenishment_filled'])
        self.assertEqual(line_1['document_out'].id, so_2.id)
        self.assertEqual(line_2['quantity'], 5)
        self.assertEqual(line_2['replenishment_filled'], False)
        self.assertEqual(line_2['document_out'].id, so_1.id)

    def test_report_forecast_2_report_line_corresponding_to_so_line_highlighted(self):
        """ When accessing the report from a SO line, checks if the correct SO line is highlighted in the report
        """
        # We create 2 identical SO
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        with so_form.order_line.new() as line:
            line.product_id = self.product
            line.product_uom_qty = 5
        so1 = so_form.save()
        so1.action_confirm()
        so2 = so1.copy()
        so2.action_confirm()

        # Check for both SO if the highlight (is_matched) corresponds to the correct SO
        for so in [so1, so2]:
            context = {"move_to_match_ids": so.order_line.move_ids.ids}
            _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids, context=context)
            for line in lines:
                if line['document_out'] == so:
                    self.assertTrue(line['is_matched'], "The corresponding SO line should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the SO shoud not be matched.")


@tagged('post_install', '-at_install')
class TestSaleStockInvoices(TestSaleCommon):

    def setUp(self):
        super(TestSaleStockInvoices, self).setUp()

        self.product_by_lot = self.env['product.product'].create({
            'name': 'Product By Lot',
            'type': 'product',
            'tracking': 'lot',
        })
        self.product_by_usn = self.env['product.product'].create({
            'name': 'Product By USN',
            'type': 'product',
            'tracking': 'serial',
        })
        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.stock_location = self.warehouse.lot_stock_id
        lot = self.env['stock.production.lot'].create({
            'name': 'LOT0001',
            'product_id': self.product_by_lot.id,
            'company_id': self.env.company.id,
        })
        self.usn01 = self.env['stock.production.lot'].create({
            'name': 'USN0001',
            'product_id': self.product_by_usn.id,
            'company_id': self.env.company.id,
        })
        self.usn02 = self.env['stock.production.lot'].create({
            'name': 'USN0002',
            'product_id': self.product_by_usn.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 10, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=self.usn01)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=self.usn02)

    def test_invoice_less_than_delivered(self):
        """
        Suppose the lots are printed on the invoices.
        A user invoice a tracked product with a smaller quantity than delivered.
        On the invoice, the quantity of the used lot should be the invoiced one.
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 5}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_lines.quantity_done = 5
        picking.button_validate()

        invoice = so._create_invoices()
        with Form(invoice) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 2
        invoice.action_post()

        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        html = report._render_qweb_html(invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n2.00\nUnits\nLOT0001', "There should be a line that specifies 2 x LOT0001")

    def test_invoice_before_delivery(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells a tracked product, its invoicing policy is "Ordered quantities"
        A user invoice a tracked product with a smaller quantity than delivered.
        On the invoice, the quantity of the used lot should be the invoiced one.
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        self.product_by_lot.invoice_policy = "order"

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 4}),
            ],
        })
        so.action_confirm()

        invoice = so._create_invoices()
        invoice.action_post()

        picking = so.picking_ids
        picking.move_lines.quantity_done = 4
        picking.button_validate()

        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        html = report._render_qweb_html(invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n4.00\nUnits\nLOT0001', "There should be a line that specifies 4 x LOT0001")

    def test_backorder_and_several_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 2 tracked-by-usn products, he delivers 1 product and invoices it
        Then, he delivers the other one and invoices it too. Each invoice should have the
        correct USN
        """
        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 2}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_lines.move_line_ids[0].qty_done = 1
        picking.button_validate()
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        invoice01 = so._create_invoices()
        with Form(invoice01) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        invoice01.action_post()

        backorder = picking.backorder_ids
        backorder.move_lines.move_line_ids.qty_done = 1
        backorder.button_validate()

        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)

        invoice02 = so._create_invoices()
        invoice02.action_post()
        html = report._render_qweb_html(invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0002', "There should be a line that specifies 1 x USN0002")
        self.assertNotIn('USN0001', text)

        # Posting the second invoice shouldn't change the result of the first one
        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should still be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)

        # Resetting and posting again the first invoice shouldn't change the results
        invoice01.button_draft()
        invoice01.action_post()
        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should still be a line that specifies 1 x USN0001")
        self.assertNotIn('USN0002', text)
        html = report._render_qweb_html(invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0002', "There should be a line that specifies 1 x USN0002")
        self.assertNotIn('USN0001', text)

    def test_invoice_with_several_returns(self):
        """
        Mix of returns and partial invoice
        - Product P tracked by lot
        - SO with 10 x P
        - Deliver 10 x Lot01
        - Return 10 x Lot01
        - Deliver 03 x Lot02
        - Invoice 02 x P
        - Deliver 05 x Lot02 + 02 x Lot03
        - Invoice 08 x P
        """
        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        lot01 = self.env['stock.production.lot'].search([('name', '=', 'LOT0001')])
        lot02, lot03 = self.env['stock.production.lot'].create([{
            'name': name,
            'product_id': self.product_by_lot.id,
            'company_id': self.env.company.id,
        } for name in ['LOT0002', 'LOT0003']])
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 8, lot_id=lot02)
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 2, lot_id=lot03)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_lot.name, 'product_id': self.product_by_lot.id, 'product_uom_qty': 10}),
            ],
        })
        so.action_confirm()

        # Deliver 10 x LOT0001
        delivery01 = so.picking_ids
        delivery01.move_lines.quantity_done = 10
        delivery01.button_validate()
        self.assertEqual(delivery01.move_line_ids.lot_id.name, 'LOT0001')

        # Return delivery01 (-> 10 x LOT0001)
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=[delivery01.id], active_id=delivery01.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        action = return_wizard.create_returns()
        pick_return = self.env['stock.picking'].browse(action['res_id'])

        move_form = Form(pick_return.move_lines, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = lot01
            line.qty_done = 10
        move_form.save()
        pick_return.button_validate()

        # Return pick_return
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=[pick_return.id], active_id=pick_return.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        action = return_wizard.create_returns()
        delivery02 = self.env['stock.picking'].browse(action['res_id'])

        # Deliver 3 x LOT0002
        delivery02.do_unreserve()
        move_form = Form(delivery02.move_lines, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = lot02
            line.qty_done = 3
        move_form.save()
        action = delivery02.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        # Invoice 2 x P
        invoice01 = so._create_invoices()
        with Form(invoice01) as form:
            with form.invoice_line_ids.edit(0) as line:
                line.quantity = 2
        invoice01.action_post()

        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n2.00\nUnits\nLOT0002', "There should be a line that specifies 2 x LOT0002")
        self.assertNotIn('LOT0001', text)

        # Deliver 5 x LOT0002 + 2 x LOT0003
        delivery03 = delivery02.backorder_ids
        delivery03.do_unreserve()
        move_form = Form(delivery03.move_lines, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = lot02
            line.qty_done = 5
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = lot03
            line.qty_done = 2
        move_form.save()
        delivery03.button_validate()

        # Invoice 8 x P
        invoice02 = so._create_invoices()
        invoice02.action_post()

        html = report._render_qweb_html(invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n6.00\nUnits\nLOT0002', "There should be a line that specifies 6 x LOT0002")
        self.assertRegex(text, r'Product By Lot\n2.00\nUnits\nLOT0003', "There should be a line that specifies 2 x LOT0003")
        self.assertNotIn('LOT0001', text)

    def test_refund_cancel_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 2 tracked-by-usn products, he delivers 2 products and invoices them
        Then he adds credit notes and issues a full refund. Receive the products.
        The reversed invoice should also have correct USN
        """
        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 2}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_lines.move_line_ids[0].qty_done = 1
        picking.move_lines.move_line_ids[1].qty_done = 1
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0002', "There should be a line that specifies 1 x USN0002")

        # Refund the invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'refund_method': 'cancel',
            'journal_id': invoice01.journal_id.id,
        })
        res = refund_wizard.reverse_moves()
        refund_invoice = self.env['account.move'].browse(res['res_id'])

        # recieve the returned product
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(active_ids=picking.ids, active_id=picking.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        res = return_wiz.create_returns()
        pick_return = self.env['stock.picking'].browse(res['res_id'])

        move_form = Form(pick_return.move_lines, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = self.usn01
            line.qty_done = 1
        with move_form.move_line_nosuggest_ids.new() as line:
            line.lot_id = self.usn02
            line.qty_done = 1
        move_form.save()
        pick_return.button_validate()

        # reversed invoice
        html = report._render_qweb_html(refund_invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0002', "There should be a line that specifies 1 x USN0002")

    def test_refund_modify_invoices(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells 1 tracked-by-usn products, he delivers 1 and invoices it
        Then he adds credit notes and issues full refund and new draft invoice.
        The new draft invoice should have correct USN
        """

        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_by_usn.name, 'product_id': self.product_by_usn.id, 'product_uom_qty': 1}),
            ],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_lines.move_line_ids[0].qty_done = 1
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        html = report._render_qweb_html(invoice01.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")

        # Refund the invoice with full refund and new draft invoice
        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'refund_method': 'modify',
            'journal_id': invoice01.journal_id.id,
        })
        res = refund_wizard.reverse_moves()
        invoice02 = self.env['account.move'].browse(res['res_id'])
        invoice02.action_post()

        # new draft invoice
        html = report._render_qweb_html(invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")
