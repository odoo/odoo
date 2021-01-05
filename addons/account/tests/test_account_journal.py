# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestAccountJournal(AccountTestInvoicingCommon):

    def test_constraint_currency_consistency_with_accounts(self):
        ''' The accounts linked to a bank/cash journal must share the same foreign currency
        if specified.
        '''
        journal_bank = self.company_data['default_journal_bank']
        journal_bank.currency_id = self.currency_data['currency']

        # Try to set a different currency on the 'debit' account.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            journal_bank.default_account_id.currency_id = self.company_data['currency']

    def test_changing_journal_company(self):
        ''' Ensure you can't change the company of an account.journal if there are some journal entries '''

        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaises(UserError), self.cr.savepoint():
            self.company_data['default_journal_sale'].company_id = self.company_data_2['company']

    def test_account_control_create_journal_entry(self):
        move_vals = {
            'line_ids': [
                (0, 0, {
                    'name': 'debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'credit',
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        }

        # Should fail because 'default_account_expense' is not allowed.
        self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_revenue']
        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['account.move'].create(move_vals)

        # Should be allowed because both accounts are accepted.
        self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_expense']
        self.env['account.move'].create(move_vals)

    def test_account_control_existing_journal_entry(self):
        self.env['account.move'].create({
            'line_ids': [
                (0, 0, {
                    'name': 'debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'credit',
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })

        # There is already an other line using the 'default_account_expense' account.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_revenue']

        # Assigning both should be allowed
        self.company_data['default_journal_misc'].account_control_ids = \
            self.company_data['default_account_revenue'] + self.company_data['default_account_expense']
