from odoo import fields

from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestPurchaseDownpayment(TestPurchaseToInvoiceCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_downpayment_in_accrued_expense_entry(self):
        """Check that the downpayment is not included in the accrued expense entry"""
        po = self.init_purchase(confirm=True, products=[self.product_order])

        self.init_invoice('in_invoice', amounts=[1600.00], post=True)

        match_lines = self.env['purchase.bill.line.match'].search([('partner_id', '=', self.partner_a.id)])
        action = match_lines.action_add_to_po()

        wizard = self.env['bill.to.po.wizard'].with_context({**action['context'], 'active_ids': match_lines.ids}).create({})
        wizard.action_add_downpayment()

        account_expense = self.company_data['default_account_expense']
        accrued_wizard = self.env['stock_account.accrued.orders.wizard'].with_context(
            active_model='purchase.order',
            active_ids=po.ids,
        ).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': fields.Date.today(),
        })

        # Receive 1 qty to have something to accrual.
        po.order_line.qty_received = 1

        self.assertRecordValues(self.env['account.move'].search(accrued_wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': account_expense.id, 'debit': 0, 'credit': 235.0},
            {'account_id': accrued_wizard.account_id.id, 'debit': 235.0, 'credit': 0},
            # move lines
            {'account_id': account_expense.id, 'debit': 235.0, 'credit': 0},
            {'account_id': accrued_wizard.account_id.id, 'debit': 0, 'credit': 235.0},
        ])
        self.assertFalse(self.env['account.move'].search(accrued_wizard.create_entries()['domain']).line_ids.filtered(lambda l: l.is_downpayment))
