from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
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
        invoice = self._create_invoice(review_state='todo')
        invoice.action_post()
        with self.assertRaisesRegex(ValidationError, 'This entry has already been reviewed.'):
            invoice.with_user(self.simple_accountman).button_draft()

        invoice.button_draft()
        self.assertEqual(invoice.state, 'draft')

        invoice.action_post()
        self.assertEqual(invoice.review_state, 'reviewed')
        invoice.review_state = 'todo'
        invoice.with_user(self.simple_accountman).button_draft()
        self.assertEqual(invoice.state, 'draft')

    def test_sales_change_invoice_from_accountant(self):
        invoice = self._create_invoice()
        invoice.action_post()
        with self.assertRaisesRegex(ValidationError, 'This entry has already been reviewed.'):
            invoice.with_user(self.simple_accountman).button_draft()

    def test_sales_modify_draft_reviewed(self):
        invoice = self._create_invoice(review_state='reviewed')
        invoice.with_user(self.simple_accountman).invoice_date = '2017-01-01'
        self.assertEqual(invoice.review_state, 'todo')

    def test_post_move_auto_check(self):
        invoice_admin = self._create_invoice()
        invoice_admin.action_post()
        # As the user has admin right, the move doesn't need to be checked
        self.assertFalse(invoice_admin.review_state)

        invoice_invoicing = self._create_invoice(user_id=self.simple_accountman.id)
        invoice_invoicing.with_user(self.simple_accountman).action_post()
        # As the user has only invoicing right, the move shouldn't be checked
        self.assertEqual(invoice_invoicing.review_state, 'todo')

    def test_post_move_auto_check_with_auto_post_at_date_accountant(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.auto_post = 'at_date'
        self.assertFalse(invoice.review_state)
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertFalse(invoice.review_state)

    def test_post_move_auto_check_with_auto_post_at_date_sales(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.with_user(self.simple_accountman).auto_post = 'at_date'
        self.assertEqual(invoice.review_state, 'todo')
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertEqual(invoice.review_state, 'todo')

    def test_post_move_auto_check_with_auto_post_at_date_sales_prereviewed(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.with_user(self.simple_accountman).auto_post = 'at_date'
        self.assertEqual(invoice.review_state, 'todo')
        invoice.review_state = 'reviewed'
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertEqual(invoice.review_state, 'reviewed')

    def test_post_move_auto_check_with_auto_post_monthly_accountant(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.auto_post = 'monthly'
        self.assertFalse(invoice.review_state)
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertFalse(invoice.review_state)
        last_recurring = self.env['account.move'].search([('auto_post_origin_id', '=', invoice.id)], limit=1, order='date desc')
        self.assertFalse(last_recurring.review_state)

    def test_post_move_auto_check_with_auto_post_monthly_sales(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.with_user(self.simple_accountman).auto_post = 'monthly'
        self.assertEqual(invoice.review_state, 'todo')
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertEqual(invoice.review_state, 'todo')
        last_recurring = self.env['account.move'].search([('auto_post_origin_id', '=', invoice.id)], limit=1, order='date desc')
        self.assertEqual(last_recurring.review_state, 'todo')

    def test_post_move_auto_check_with_auto_post_monthly_sales_prereviewed(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.with_user(self.simple_accountman).auto_post = 'monthly'
        self.assertEqual(invoice.review_state, 'todo')
        invoice.review_state = 'reviewed'
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        self.assertEqual(invoice.review_state, 'reviewed')
        last_recurring = self.env['account.move'].search([('auto_post_origin_id', '=', invoice.id)], limit=1, order='date desc')
        self.assertEqual(last_recurring.review_state, 'reviewed')

    def test_post_move_auto_check_with_auto_post_monthly_sales_postreviewed(self):
        invoice = self._create_invoice(date=fields.Date.today())
        invoice.with_user(self.simple_accountman).auto_post = 'monthly'
        self.assertEqual(invoice.review_state, 'todo')
        with freeze_time(invoice.date + relativedelta(days=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        invoice.review_state = 'reviewed'
        last_recurring = self.env['account.move'].search([('auto_post_origin_id', '=', invoice.id)], limit=1, order='date desc')
        self.assertEqual(last_recurring.review_state, 'todo')
        last_recurring.review_state = 'reviewed'
        with freeze_time(invoice.date + relativedelta(days=1, months=1)), self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
        last_recurring = self.env['account.move'].search([('auto_post_origin_id', '=', invoice.id)], limit=1, order='date desc')
        self.assertEqual(last_recurring.review_state, 'reviewed')

    def test_create_statement_line_auto_check(self):
        if 'account_accountant' not in self.env["ir.module.module"]._installed():
            self.skipTest('account_accountant is not installed')  # required for `_try_auto_reconcile_statement_lines`
        """Test if a user changes the reconciliation on a st_line, it marks the bank move as 'To Review'"""
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'amount': 100,
            'journal_id': self.company_data['default_journal_bank'].id,
            'memo': 'INV/2025/00001',
        })
        payment.action_post()

        bank_line_1 = self.env['account.bank.statement.line'].create([{
            'journal_id': self.bank_journal.id,
            'date': '2025-01-01',
            'payment_ref': "INV/2025/00001",
            'amount': -100,
        }])
        bank_line_1._try_auto_reconcile_statement_lines()
        self.assertFalse(bank_line_1.move_id.review_state)
        with self.assertRaisesRegex(ValidationError, 'Validated entries can only be changed by your accountant.'):
            bank_line_1.with_user(self.simple_accountman).delete_reconciled_line(payment.move_id.line_ids[0].id)

    def test_auto_post_invoicing_only(self):
        """ Test that an Administrator user with only invoicing installed can still auto post invoice"""
        # By default, invoicing users don't have group_account_user
        self.env.user.write({'group_ids': [Command.unlink(self.env.ref('account.group_account_user').id)]})
        invoice = self._create_invoice(date=fields.Date.today(), auto_post='monthly')
        invoice.action_post()
