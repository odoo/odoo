# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged,TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccountAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # By default, tests are run with the current user set on the first company.
        cls.env.user.company_id = cls.company_data['company']

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


@tagged('post_install', '-at_install')
class TestPerformance(TransactionCase):
    def test_create_batch(self):
        """Enforce some models create overrides support batch record creation."""
        self.assertModelCreateMulti("account.move")
        self.assertModelCreateMulti("account.move.line", [dict(move_id=i) for i in range(2)])
        self.assertModelCreateMulti("account.account")
        self.assertModelCreateMulti("account.payment")
        # TODO account.bank.statement.line
        # account.bank.statement.line needs a more advanced setup to be tested
        # self.env["account.bank.statement.line"].create([dict(statement_id=i) for i in range(2)])
