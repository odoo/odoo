from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command, release
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('-at_install', 'post_install_l10n', 'post_install')
class AccountTestSIE4Export(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chart_template = 'se'
        cls.currency = cls.env.ref('base.SEK')
        cls.company_id = cls.setup_other_company(name='SIE 4  Test Company')['company']
        cls.report = cls.env.ref('account_reports.general_ledger_report')
        cls.handler = cls.env[cls.report.custom_handler_model_name]
        cls.journal_misc = cls.env['account.journal'].search(
            domain=[('company_id', '=', cls.company_id.id), ('type', '=', 'general')],
            limit=1,
        )

    def create_move(self, date, code_amount: list[tuple[str, float]], branch_id=False):
        currency_id = self.currency.id
        account_amount_map = {}
        for account_code, amount in code_amount:
            account = self.env['account.account'].with_company(branch_id or self.company_id).search([('code', '=', account_code)])
            account_amount_map[account.id] = amount

        move = self.env['account.move'].create({
            'company_id': (branch_id or self.company_id).id,
            'partner_id': self.partner_a.id,
            'move_type': 'entry',
            'date': date,
            'invoice_date': date,
            'journal_id': self.journal_misc.id,
            'line_ids': [
                Command.create({'balance': balance, 'account_id': account_id, 'currency_id': currency_id})
                for account_id, balance in account_amount_map.items()
            ],
        })
        move.action_post()
        return move

    def export_sie4_result_list(self, options):
        res = [
            *self.handler._export_l10n_se_sie4_identification(options),
            *self.handler._export_l10n_se_sie4_chart_of_account(options),
            *self.handler._export_l10n_se_sie4_bs_balance(options),
            *self.handler._export_l10n_se_sie4_pl_balance(options),
            *self.handler._export_l10n_se_sie4_verification(options),
        ]

        # Remove/replace added accounts from the OSS and other modules that modifies some of
        # the base account records. This ensures the result of the test result always stays
        # the same no matter what module is installed.
        values_to_remove = {
            '#KONTO 1934 "Outstanding Payments"',
            '#KTYP  1934 T',
            '#KONTO 1935 "Credit Journal"',
            '#KTYP  1935 S',
            '#KONTO 2601 "Outgoing VAT on sales within Sweden, 25% OSS"',
            '#KTYP 2601 S',
        }
        values_to_replace = {
            '#KONTO 1933 "Outstanding Receipts"': '#KONTO 1933 "Credit Journal"',
            '#KTYP  1933 T': '#KTYP  1933 S',
        }
        return [
            values_to_replace.get(line, line)
            for line in res
            if line not in values_to_remove
        ]

    @freeze_time('2024-07-01')
    @patch.object(release, 'version', '99.0')
    def test_sie4_export_file(self):
        amounts = (100, 200, 300, 400, 500, 600, 700, 800, 900)

        # Fill #IB and #UB lines
        code_to_debit = ('1030', '1039', '1060', '1069', '1110', '1119', '1130', '1150', '1159')
        code_to_credit = ('2019', '2020', '2030', '2040', '2060', '2070', '2081', '2083', '2086')
        for idx in range(9):
            self.create_move('2022-01-05', [(code_to_debit[idx], amounts[idx]), (code_to_credit[idx], -amounts[idx])])
            self.create_move('2023-01-05', [(code_to_debit[idx], amounts[idx]), (code_to_credit[idx], -amounts[idx])])
            self.create_move('2024-01-05', [(code_to_debit[idx], amounts[idx]), (code_to_credit[idx], -amounts[idx])])

        # Fill #RES lines
        code_to_debit = ('3000', '3001', '3002', '3003', '3004', '3100', '3105', '3106', '3108')
        code_to_credit = ('4533', '4535', '4536', '4537', '4538', '4545', '4546', '4547', '4600')
        for idx in range(9):
            self.create_move('2023-04-01', [(code_to_debit[idx], amounts[idx]), (code_to_credit[idx], -amounts[idx])])
            self.create_move('2024-04-01', [(code_to_debit[idx], amounts[idx]), (code_to_credit[idx], -amounts[idx])])

        options = self._generate_options(self.report, '2024-01-01', '2024-12-31')
        res = self.export_sie4_result_list(options)

        with file_open('l10n_se_sie4_export/tests/test_files/sie4_export.se') as f:
            file_res = f.read().strip().split('\n')
            self.assertListEqual(res, file_res)

    @freeze_time('2024-08-01')
    @patch.object(release, 'version', '99.0')
    def test_sie4_export_from_branch(self):
        branch = self.env['res.company'].create({
            'name': "SE Branch Company",
            'parent_id': self.company_id.id,
        })
        self.create_move('2024-06-15', [('3000', 1000), ('4533', -1000)], branch_id=branch)
        report_branch_company = self.report.with_context(allowed_company_ids=branch.ids)
        options = self._generate_options(report_branch_company, '2024-01-01', '2024-12-31')
        res = self.export_sie4_result_list(options)

        self.assertEqual(len(res), 689)
        self.assertListEqual(res[:10], [  # check first 10 lines to make sure the header data and some accounts are exported
            '#FLAGGA 0',
            '#FORMAT PC8',
            '#SIETYP 4',
            '#PROGRAM "Odoo" 99.0',
            '#GEN 20240801',
            '#FNAMN "SE Branch Company"',
            '#RAR -1 20230101 20231231',
            '#RAR  0 20240101 20241231',
            '#KONTO 1030 "Patents"',
            '#KTYP  1030 T',
        ])
        self.assertListEqual(res[-10:], [  # check last 10 lines to make sure RES and VER are correctly exported
            '#KTYP  999999 S',
            '#RES -1 3000 0.0',
            '#RES  0 3000 1000.0',
            '#RES -1 4533 0.0',
            '#RES  0 4533 -1000.0',
            '#VER A 1 20240615 "MISC/2024/06/0001"',
            '{',
            '    #TRANS 3000 {} 1000.0',
            '    #TRANS 4533 {} -1000.0',
            '}',
        ])

    @freeze_time('2026-02-01')
    def test_sie4_export_not_include_cancelled_entry(self):
        move = self.create_move('2026-02-15', [('4000', 1000), ('2440', -1000)])
        move.button_cancel()
        options = self._generate_options(self.report, '2026-02-01', '2026-12-28')
        res = self.export_sie4_result_list(options)

        self.assertListEqual(res[-10:], [
            '#KONTO 9991 "Cash Difference Gain"',
            '#KTYP  9991 I',
            '#KONTO 9992 "Cash Difference Loss"',
            '#KTYP  9992 K',
            '#KONTO 9993 "Cash Discount Loss"',
            '#KTYP  9993 K',
            '#KONTO 9994 "Cash Discount Gain"',
            '#KTYP  9994 I',
            '#KONTO 999999 "Undistributed Profits/Losses"',
            '#KTYP  999999 S',
        ])
