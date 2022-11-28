# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestAccountAccount(AccountTestInvoicingCommon):

    def test_changing_account_company(self):
        ''' Ensure you can't change the company of an account.account if there are some journal entries '''

        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': 'line_credit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })

        with self.assertRaises(UserError), self.cr.savepoint():
            self.company_data['default_account_revenue'].company_id = self.company_data_2['company']

    def test_toggle_reconcile(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with existing journal entries. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })
        move.action_post()
        self.env['account.move.line'].flush_model()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set the account as reconcile and fully reconcile something.
        account.reconcile = True
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 100.0, 'amount_residual_currency': 200.0},
            {'reconciled': False, 'amount_residual': -100.0, 'amount_residual_currency': -200.0},
        ])

        move.line_ids.reconcile()
        self.assertRecordValues(move.line_ids, [
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set back to a not reconcile account and check the journal items.
        move.line_ids.remove_move_reconcile()
        account.reconcile = False
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

    def test_toggle_reconcile_with_partials(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with partial reconciliation. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
            ],
        })
        move.action_post()

        # Set the account as reconcile and partially reconcile something.
        account.reconcile = True
        self.env.invalidate_all()

        move.line_ids.filtered(lambda line: line.account_id == account).reconcile()

        # Try to set the account as a not-reconcile one.
        with self.assertRaises(UserError), self.cr.savepoint():
            account.reconcile = False

    def test_toggle_reconcile_outstanding_account(self):
        ''' Test the feature when the user sets an account as not reconcilable when a journal
        is configured with this account as the payment credit or debit account.
        Since such an account should be reconcilable by nature, a ValidationError is raised.'''
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_bank'].company_id.account_journal_payment_debit_account_id.reconcile = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_bank'].company_id.account_journal_payment_credit_account_id.reconcile = False

    def test_remove_account_from_account_group(self):
        """Test if an account is well removed from account group"""
        group = self.env['account.group'].create({
            'name': 'test_group',
            'code_prefix_start': 401000,
            'code_prefix_end': 402000,
            'company_id': self.env.company.id
        })

        account_1 = self.company_data['default_account_revenue'].copy({'code': 401000})
        account_2 = self.company_data['default_account_revenue'].copy({'code': 402000})

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}] * 2)

        group.code_prefix_end = 401000

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}, {'group_id': False}])

    def test_name_create(self):
        """name_create should only be possible when importing
           Code and Name should be split
        """
        with self.assertRaises(UserError):
            self.env['account.account'].name_create('550003 Existing Account')
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550003 Existing Account')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550003")
        self.assertEqual(account.name, "Existing Account")

    def test_compute_account_type(self):
        existing_account = self.env['account.account'].search([], limit=1)
        # account_type should be computed
        new_account_code = self.env['account.account']._search_new_account_code(
            company=existing_account.company_id,
            digits=len(existing_account.code),
            prefix=existing_account.code[:-1])
        new_account = self.env['account.account'].create({
            'code': new_account_code,
            'name': 'A new account'
        })
        self.assertEqual(new_account.account_type, existing_account.account_type)
        # account_type should not be altered
        alternate_account = self.env['account.account'].search([('account_type', '!=', existing_account.account_type)], limit=1)
        alternate_code = self.env['account.account']._search_new_account_code(
            company=alternate_account.company_id,
            digits=len(alternate_account.code),
            prefix=alternate_account.code[:-1])
        new_account.code = alternate_code
        self.assertEqual(new_account.account_type, existing_account.account_type)

    def test_compute_current_balance(self):
        """ Test if an account's current_balance is computed correctly """

        account_payable = self.company_data['default_account_payable']
        account_receivable = self.company_data['default_account_receivable']

        payable_debit_move = {
            'line_ids': [
                (0, 0, {'name': 'debit', 'account_id': account_payable.id, 'debit': 100.0, 'credit': 0.0}),
                (0, 0, {'name': 'credit', 'account_id': account_receivable.id, 'debit': 0.0, 'credit': 100.0}),
            ],
        }
        payable_credit_move = {
            'line_ids': [
                (0, 0, {'name': 'credit', 'account_id': account_payable.id, 'debit': 0.0, 'credit': 100.0}),
                (0, 0, {'name': 'debit', 'account_id': account_receivable.id, 'debit': 100.0, 'credit': 0.0}),
            ],
        }

        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_debit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 100)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100)

        self.env['account.move'].create(payable_credit_move).button_cancel()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Canceled invoices/bills should not be used when computing the balance')

        # draft invoice
        self.env['account.move'].create(payable_credit_move)
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Draft invoices/bills should not be used when computing the balance')
