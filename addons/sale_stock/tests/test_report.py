# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form
from odoo.addons.sale.tests.common import TestSaleCommon

from odoo.tools import html2plaintext


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
        usn01 = self.env['stock.production.lot'].create({
            'name': 'USN0001',
            'product_id': self.product_by_usn.id,
            'company_id': self.env.company.id,
        })
        usn02 = self.env['stock.production.lot'].create({
            'name': 'USN0002',
            'product_id': self.product_by_usn.id,
            'company_id': self.env.company.id,
        })
        self.usn01 = usn01
        self.usn02 = usn02
        self.env['stock.quant']._update_available_quantity(self.product_by_lot, self.stock_location, 10, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=usn01)
        self.env['stock.quant']._update_available_quantity(self.product_by_usn, self.stock_location, 1, lot_id=usn02)

    def test_invoice_less_than_delivered(self):
        """
        Suppose the lots are printed on the invoices.
        A user invoice a tracked product with a smaller quantity than delivered.
        On the invoice, the quantity of the used lot should be the invoiced one.
        """
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=[invoice01.id]).create({
            'refund_method': 'cancel',
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])

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
        display_lots = self.env.ref('sale_stock.group_lot_on_invoice')
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
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=[invoice01.id]).create({
            'refund_method': 'modify',
        })
        invoice02 = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])
        invoice02.action_post()

        # new draft invoice
        html = report._render_qweb_html(invoice02.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By USN\n1.00\nUnits\nUSN0001', "There should be a line that specifies 1 x USN0001")
