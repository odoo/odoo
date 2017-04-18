# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
import time
from odoo import tools
from odoo.modules.module import get_resource_path


class TestAccountBankStatement(common.TransactionCase):

    def test_account_bank_statement_def(self):
        """  In order to test Bank Statement feature of account I create a bank statement line
             and confirm it and check it's move created  """

        tools.convert_file(self.cr, 'account',
                           get_resource_path('account', 'test', 'account_minimal_test.xml'),
                           {}, 'init', False, 'test', self.registry._assertion_report)

        # Select the period and journal for the bank statement
        journal = self.env['account.bank.statement'].with_context({
            'lang': u'en_US',
            'tz': False,
            'active_model': 'ir.ui.menu',
            'journal_type': 'bank',
            'date': time.strftime("%Y/%m/%d")
        })._default_journal()
        self.assertTrue(journal, 'Journal has not been selected')

        # Create a bank statement with Opening and Closing balance 0
        account_statement = self.env['account.bank.statement'].create({
            'balance_end_real': 0.0,
            'balance_start': 0.0,
            'date': time.strftime("%Y-%m-%d"),
            'company_id': self.ref('base.main_company'),
            'journal_id': journal.id,
        })

        # Create Account bank statement line
        account_bank_statement_line = self.env['account.bank.statement.line'].create({
            'amount': 1000,
            'date': time.strftime('%Y-%m-%d'),
            'partner_id': self.ref('base.res_partner_4'),
            'name': 'EXT001',
            'statement_id': account_statement.id,
        })

        # Create a Account for bank statement line process
        account = self.env['account.account'].create({
            'name': 'toto',
            'code': 'bidule',
            'user_type_id': self.ref('account.data_account_type_fixed_assets'),
        })

        # Process the bank statement line
        account_statement.line_ids.process_reconciliation(new_aml_dicts=[{
            'credit': 1000,
            'debit': 0,
            'name': 'toto',
            'account_id': account.id,
        }])

        # Modify the bank statement and set the Closing Balance 1000.
        account_statement.write({'balance_end_real': 1000.00})

        # Confirm the bank statement using Confirm button
        account_statement.button_confirm_bank()

        # Check bank statement state should be confirm
        self.assertEquals(account_statement.state, 'confirm')
