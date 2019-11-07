from odoo.addons.account.tests.common import AccountTestNoChartCommon
from odoo.tests.common import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestControlJournalAccount(AccountTestNoChartCommon):
    @classmethod
    def setUpClass(cls):
        super(TestControlJournalAccount, cls).setUpClass()
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

        cls.move_data = {
            'journal_id': cls.journal_general.id,
            'line_ids': [
                (0, 0, {
                    'account_id': cls.account_income.id,
                    'debit': 100,
                }),
                (0, 0, {
                    'account_id': cls.account_expense.id,
                    'credit': 100,
                }),
            ]
        }

    def test_can_create(self):
        # There is no problem creating this move when there are no restrictions
        self.env['account.move'].create(self.move_data.copy())

    def test_restrict_journal(self):
        self.journal_general.account_control_ids = self.account_income

        # Cannot create because of restrictions on journal
        with self.assertRaises(UserError), self.cr.savepoint(flush=False):
            self.env['account.move'].create(self.move_data.copy())

        self.journal_general.account_control_ids += self.account_expense

        # Can create now
        self.env['account.move'].create(self.move_data.copy())

    def test_prevent_restrict_journal(self):
        self.env['account.move'].create(self.move_data.copy())
        # There is already an item in another account
        with(self.assertRaises(ValidationError)):
            self.journal_general.account_control_ids = self.account_income
        # We can set the restriction to the account of the existing entry
        self.journal_general.account_control_ids = self.account_income + self.account_expense

    def test_restrict_account(self):
        self.account_expense.allowed_journal_ids = self.journal_sale

        # Cannot create because of restrictions on account
        with self.assertRaises(UserError), self.cr.savepoint(flush=False):
            move = self.env['account.move'].create(self.move_data.copy())

        self.account_expense.allowed_journal_ids += self.journal_general

        # Can create now
        self.env['account.move'].create(self.move_data.copy())

    def test_prevent_restrict_account(self):
        self.env['account.move'].create(self.move_data.copy())
        # There is already an item in another journal
        with self.assertRaises(ValidationError):
            self.account_expense.allowed_journal_ids = self.journal_sale
        # We can set the restriction to the journal of the existing entry
        self.account_expense.allowed_journal_ids = self.journal_general
