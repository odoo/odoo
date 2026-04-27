from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestBankCashReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].vat = "20512528458"

    @freeze_time('2024-01-01')
    def test_cash_report(self):
        """Ensure that cash report is generated correctly"""

        cash_journal = self.company_data['default_journal_cash']
        # ==== Statements ====
        bank_statement = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2024-01-01',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'line_ids': [
                Command.create({'payment_ref': 'line_1', 'amount': 600.0, 'date': '2024-01-01', 'journal_id': cash_journal.id}),
                Command.create({'payment_ref': 'line_2', 'amount': -500.0, 'date': '2024-01-01', 'journal_id': cash_journal.id}),
            ],
        })
        line_one, line_two = bank_statement.line_ids

        # ==== Report ====
        report = self.env.ref('account_reports.cash_flow_report')

        options = self._generate_options(report, fields.Date.today(), fields.Date.today())

        self.assertSequenceEqual(
            self.env[report.custom_handler_model_name].l10n_pe_export_ple_11_to_txt(options)['file_content'].decode().split('\n'),
            [
                f'20240100|{line_one.move_id.id}|M1|1031001|||PEN|00||000|01/01/2024||01/01/2024|line_1|line_1|600.00|0.00||1|',
                f'20240100|{line_two.move_id.id}|M1|1031001|||PEN|00||000|01/01/2024||01/01/2024|line_2|line_2|0.00|500.00||1|',
                '',
             ]
        )

    @freeze_time('2024-01-01')
    def test_bank_report(self):
        """Ensure that bank report is generated correctly"""

        bank_journal = self.company_data['default_journal_bank']
        # ==== Statements ====
        bank_statement = self.env['account.bank.statement'].create({
            'name': 'statement_1',
            'date': '2024-01-01',
            'balance_start': 0.0,
            'balance_end_real': 100.0,
            'line_ids': [
                Command.create({'payment_ref': 'line_1', 'amount': 600.0, 'date': '2024-01-01', 'journal_id': bank_journal.id}),
                Command.create({'payment_ref': 'line_2', 'amount': -500.0, 'date': '2024-01-01', 'journal_id': bank_journal.id}),
            ],
        })
        line_one, line_two = bank_statement.line_ids

        # ==== Report ====
        report = self.env.ref('account_reports.cash_flow_report')

        options = self._generate_options(report, fields.Date.today(), fields.Date.today())
        self.assertSequenceEqual(
            self.env[report.custom_handler_model_name].l10n_pe_export_ple_12_to_txt(options)['file_content'].decode().split('\n'),
            [
                f'20240100|{line_one.move_id.id}|M1|99||01/01/2024|003|line_1|-|-|-|BNK1202400001|600.00|0.00|1|',
                f'20240100|{line_two.move_id.id}|M1|99||01/01/2024|003|line_2|-|-|-|BNK1202400002|0.00|500.00|1|',
                '',
            ]
        )
