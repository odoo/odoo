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
            journal_bank.default_debit_account_id.currency_id = self.company_data['currency']

    def test_constraint_shared_accounts(self):
        ''' Ensure the bank/outstanding accounts are not shared between multiple journals. '''
        journal_bank = self.company_data['default_journal_bank']

        account_fields = (
            'default_debit_account_id',
            'default_credit_account_id',
            'payment_debit_account_id',
            'payment_credit_account_id',
        )
        for account_field in account_fields:
            with self.assertRaises(ValidationError), self.cr.savepoint():
                journal_bank.copy(default={
                    'name': 'test_constraint_shared_accounts %s' % account_field,
                    account_field: journal_bank[account_field].id,
                })
