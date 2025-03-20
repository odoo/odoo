from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class SpreadsheetAccountingBalanceTagFunctionTest(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tag_1 = cls._create_account_tag('tag_1')
        cls.tag_2 = cls._create_account_tag('tag_2')

        cls.company_data['default_account_receivable'].tag_ids |= cls.tag_1
        cls.company_data['default_account_revenue'].tag_ids |= cls.tag_1
        cls.company_data['default_account_expense'].tag_ids |= cls.tag_2

        cls.posted_move = cls.env['account.move'].create({
            'company_id': cls.company_data['company'].id,
            'move_type': 'entry',
            'date': '2025-01-01',
            'line_ids': [
                Command.create({
                    'name': "posted line debit 1",
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 100,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'name': "posted line debit 2",
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 50,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'name': "posted line credit 1",
                    'account_id': cls.company_data['default_account_expense'].id,
                    'credit': 150,
                    'company_id': cls.company_data['company'].id,
                }),
            ],
        })
        cls.posted_move.action_post()

        cls.draft_move = cls.env['account.move'].create({
            'company_id': cls.company_data['company'].id,
            'move_type': 'entry',
            'date': '2024-01-01',
            'line_ids': [
                Command.create({
                    'name': "draft line debit 1",
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 100,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'name': "draft line credit 1",
                    'account_id': cls.company_data['default_account_expense'].id,
                    'credit': 100,
                    'company_id': cls.company_data['company'].id,
                }),
            ],
        })

    @classmethod
    def _create_account_tag(cls, tag_name):
        return cls.env['account.account.tag'].create([{
            'name': tag_name,
            'applicability': 'accounts',
        }])

    def test_sreadsheet_balance_tags_empty_payload(self):
        self.assertEqual(
            self.env["account.account"].spreadsheet_fetch_balance_tag([]), []
        )

    def test_spreadsheet_balance_tags(self):
        tag_balances = self.env["account.account"].spreadsheet_fetch_balance_tag([
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2025,
                },
                'account_tag_ids': self.tag_1.ids,
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2025,
                },
                'account_tag_ids': (self.tag_1 + self.tag_2).ids,
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2024,
                },
                'account_tag_ids': self.tag_1.ids,
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2024,
                },
                'account_tag_ids': self.tag_1.ids,
                'company_id': None,
                'include_unposted': True,
            },
        ])

        self.assertEqual(tag_balances, [
            {'balance': 150.0},    # year 2025, tag_1
            {'balance': 0.0},      # year 2025, tag_1 & tag_2
            {'balance': 0.0},      # year 2024, tag_1, posted_only
            {'balance': 100.0},    # year 2024, tag_1, draft included
        ])
