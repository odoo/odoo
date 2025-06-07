from odoo import Command, fields

from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestPurchaseDownpayment(TestPurchaseToInvoiceCommon):

    def test_downpayment_basic(self):
        po = self.init_purchase(confirm=False, products=[self.product_order])
        po.order_line.product_qty = 10.0
        po.button_confirm()

        dp_bill = self.init_invoice('in_invoice', amounts=[69.00], post=True)

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        action = match_lines.action_add_to_po()

        wizard = self.env['bill.to.po.wizard'].with_context({**action['context'], 'active_ids': match_lines.ids}).create({})
        wizard.action_add_downpayment()

        po_dp_section_line = po.order_line.filtered(lambda l: l.display_type == 'line_section' and l.is_downpayment)
        self.assertEqual(len(po_dp_section_line), 1)
        po_dp_line = po.order_line.filtered(lambda l: l.display_type != 'line_section' and l.is_downpayment)
        self.assertEqual(po_dp_line.name, 'Down Payment (ref: %s)' % dp_bill.invoice_line_ids.display_name)
        self.assertEqual(po_dp_line.sequence, po_dp_section_line.sequence + 1)

        # This is not the normal flow, but we test the deduction of the downpayment
        action_view_bill = po.action_create_invoice()
        generated_bill = self.env['account.move'].browse(action_view_bill['res_id'])

        self.assertRecordValues(generated_bill.invoice_line_ids, [
            # pylint: disable=C0326
            {'product_id': self.product_order.id, 'display_type': 'product',      'quantity': 10, 'is_downpayment': False, 'balance': 10.0 * self.product_order.standard_price},
            {'product_id': False,                 'display_type': 'line_section', 'quantity': 0,  'is_downpayment': True,  'balance': 0.0},
            {'product_id': False,                 'display_type': 'product',      'quantity': -1, 'is_downpayment': True,  'balance': -69.0},
        ])

        # Normal flow: New bill with negative down payment line
        final_bill = generated_bill.copy()
        generated_bill.button_cancel()
        generated_bill.unlink()
        final_bill.invoice_date = fields.Date.from_string('2019-01-02')
        self.assertFalse(final_bill.line_ids.purchase_line_id)

        self.env['account.move'].flush_model()
        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        match_lines.action_match_lines()

        self.assertEqual(final_bill.invoice_line_ids.purchase_order_id.invoice_status, 'invoiced')
        self.assertRecordValues(po_dp_line, [{
            'qty_invoiced': 0,
            'invoice_lines': dp_bill.invoice_line_ids.ids + final_bill.invoice_line_ids[-1:].ids,
        }])
        self.env.flush_all()
        self.assertFalse(self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)]))

    def test_product_supplierinfo_downpayment(self):
        """Check that the creation of a downpayment does not affect already existing lines"""
        self.product_a.seller_ids = [Command.create({
            'partner_id': self.partner_a.id,
            'price': 750.0,
            'min_qty': 10
        })]

        down_po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_qty': 10,
            })]
        })

        product_line = down_po.order_line
        self.assertEqual(product_line.price_unit, 750.0)
        down_po.order_line.price_unit = 800
        down_po.button_confirm()

        self.init_invoice('in_invoice', amounts=[1600.00], post=True)

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        action = match_lines.action_add_to_po()

        wizard = self.env['bill.to.po.wizard'].with_context({**action['context'], 'active_ids': match_lines.ids}).create({})
        wizard.action_add_downpayment()

        self.assertEqual(product_line.price_unit, 800.0)

    def test_downpayment_in_accrued_expense_entry(self):
        """Check that the downpayment is not included in the accrued expense entry"""
        po = self.init_purchase(confirm=False, products=[self.product_order])
        po.button_confirm()

        self.init_invoice('in_invoice', amounts=[1600.00], post=True)

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        action = match_lines.action_add_to_po()

        wizard = self.env['bill.to.po.wizard'].with_context({**action['context'], 'active_ids': match_lines.ids}).create({})
        wizard.action_add_downpayment()

        account_expense = self.company_data['default_account_expense']
        accrued_wizard = self.env['account.accrued.orders.wizard'].with_context(
            active_model='purchase.order',
            active_ids=po.ids,
        ).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2025-01-01',
        })

        self.assertRecordValues(self.env['account.move'].search(accrued_wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': account_expense.id, 'debit': 0, 'credit': 235.0},
            {'account_id': accrued_wizard.account_id.id, 'debit': 235.0, 'credit': 0},
            # move lines
            {'account_id': account_expense.id, 'debit': 235.0, 'credit': 0},
            {'account_id': accrued_wizard.account_id.id, 'debit': 0, 'credit': 235.0},
        ])
        self.assertFalse(self.env['account.move'].search(accrued_wizard.create_entries()['domain']).line_ids.filtered(lambda l: l.is_downpayment))
