# -*- coding: utf-8 -*-
from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user, tagged


@tagged('post_install', '-at_install')
class TestSetupWizard(AccountTestInvoicingCommon):

    def test_setup_bank_account(self):
        """
        Test that no error is raised when creating the bank setup wizard
        """
        wizard = self.env['account.setup.bank.manual.config'].create([
            {
                'num_journals_without_account': 1,
                'linked_journal_id': False,
                'acc_number': 'BE15001559627230',
                'bank_id': self.env['res.bank'].create({'name': 'Test bank'}).id,
                'bank_bic': False
            }
        ])
        self.assertTrue(wizard)

    def test_financial_year_opening_accounting_manager(self):
        """ An accounting manager, without the right to write on companies, can set
        the opening date with the opening balance wizard. """
        accountant = new_test_user(
            self.env, login='accountant', groups='account.group_account_manager',
            company_id=self.env.company.id,
        )
        wizard = self.env['account.financial.year.op'].with_user(accountant).create({
            'company_id': self.env.company.id,
        })
        wizard.opening_date = '2025-01-01'
        self.assertEqual(self.env.company.account_opening_date, date(2025, 1, 1))
