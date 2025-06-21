from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestCheckAccountMoves(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.simple_accountman.group_ids = cls.env.ref('account.group_account_invoice')
        cls.bank_journal = cls.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', cls.company.id)], limit=1)

    def test_try_check_move_with_invoicing_user(self):
        invoice = self._create_invoice(checked=True)
        invoice.action_post()
        with self.assertRaises(ValidationError):
            invoice.with_user(self.simple_accountman).button_draft()

        invoice.button_draft()
        self.assertEqual(invoice.state, 'draft')

        invoice.action_post()
        invoice.checked = False
        invoice.with_user(self.simple_accountman).button_draft()
        self.assertEqual(invoice.state, 'draft')

    def test_post_move_auto_check(self):
        invoice_admin = self._create_invoice()
        invoice_admin.action_post()
        # As the user has admin right, the move should be auto checked
        self.assertTrue(invoice_admin.checked)

        invoice_invoicing = self._create_invoice(user_id=self.simple_accountman.id)
        invoice_invoicing.with_user(self.simple_accountman).action_post()
        # As the user has only invoicing right, the move shouldn't be checked
        self.assertFalse(invoice_invoicing.checked)

    def test_post_move_auto_check_with_auto_post(self):
        invoice = self._create_invoice(auto_post='at_date', date=fields.Date.today())
        self.assertFalse(invoice.checked)
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertTrue(invoice.checked)

    def test_create_statement_line_auto_check(self):
        """Test if a user changes the reconciliation on a st_line, it marks the bank move as 'To Review'"""
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'amount': 100,
            'journal_id': self.company_data['default_journal_bank'].id,
            'memo': 'INV/2025/00001'
        })
        payment.action_post()
        bank_line_1 = self.env['account.bank.statement.line'].create([
            {
                'journal_id': self.bank_journal.id,
                'date': '2025-01-01',
                'payment_ref': "INV/2025/00001",
                'amount': -100,
            }
        ])
        bank_line_1._try_auto_reconcile_statement_lines()
        self.assertTrue(bank_line_1.move_id.checked)
        bank_line_1.with_user(self.simple_accountman).set_line_bank_statement_line(payment.move_id.line_ids[0].id)
        self.assertFalse(bank_line_1.move_id.checked)
