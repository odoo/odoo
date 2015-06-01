from datetime import datetime
from openerp.tests.common import TransactionCase
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

class TestChildAccounts(TransactionCase):
    
    def setUp(self):
        super(TestChildAccounts, self).setUp()
        self.budget_model = self.registry('crossovered.budget')
        self.budget_post_model = self.registry('account.budget.post')
        self.account_model = self.registry('account.account')
        self.analytic_account_model = self.registry('account.analytic.account')

    def test_child_accounts(self):
        '''
        Test if an analytic's child account's lines are also counted in a
        budget
        '''
        account_id = self.account_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testaccount',
                    'code': 'test42',
                    'user_type': self.ref(
                        'account.data_account_type_receivable'),
                })
        analytic_account_id = self.analytic_account_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testaccount',
                    'code': 'test42',
                })
        analytic_account_child_id = self.analytic_account_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testaccount child',
                    'code': 'test42.1',
                    'parent_id': analytic_account_id,
                })
        budget_post_id = self.budget_post_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testbudgetpost',
                    'code': 'test42',
                    'account_ids': [(6, 0, [account_id])],
                })
        budget_id = self.budget_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testbudget',
                    'code': 'test42',
                    'date_from': datetime.today().replace(month=1, day=1)\
                            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'date_to': datetime.today().replace(month=12, day=31)\
                            .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'crossovered_budget_line': [
                        (
                            0, 0,
                            {
                                'general_budget_id': budget_post_id,
                                'analytic_account_id': analytic_account_id,
                                'date_from': datetime.today()\
                                        .replace(month=1, day=1)\
                                        .strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT),
                                'date_to': datetime.today()\
                                        .replace(month=12, day=31)\
                                        .strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT),
                                'planned_amount': 42,
                            },
                        )
                        ],
                })
        journal_id = self.registry('account.analytic.journal').search(
                self.cr, self.uid, [])[0]

        self.analytic_account_model.write(
                self.cr,
                self.uid,
                analytic_account_id,
                {
                    'line_ids': [
                        (
                            0, 0,
                            {
                                'name': '/',
                                'date': datetime.today()\
                                        .strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT),
                                'amount': 42,
                                'general_account_id': account_id,
                                'journal_id': journal_id,
                            },
                        ),
                    ],
                })
        self.analytic_account_model.write(
                self.cr,
                self.uid,
                analytic_account_child_id,
                {
                    'line_ids': [
                        (
                            0, 0,
                            {
                                'name': '/',
                                'date': datetime.today()\
                                        .strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT),
                                'amount': 42,
                                'general_account_id': account_id,
                                'journal_id': journal_id,
                            },
                        ),
                    ],
                })


        budget = self.budget_model.browse(self.cr, self.uid, budget_id)
        self.assertEqual(
            budget.crossovered_budget_line[0].practical_amount, 84)
