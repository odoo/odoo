# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


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
