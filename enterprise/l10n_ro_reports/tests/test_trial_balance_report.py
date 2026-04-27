from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nROTrialBalanceReport(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()

        def invoice_move(date, mult=1000.0):
            cls.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string(date),
                'journal_id': cls.company_data['default_journal_misc'].id,
                'line_ids': [
                    Command.create({'debit': mult,     'credit': 0.0,      'name': 'payable', 'account_id': cls.company_data['default_account_payable'].id}),
                    Command.create({'debit': 2 * mult, 'credit': 0.0,      'name': 'expense', 'account_id': cls.company_data['default_account_expense'].id}),
                    Command.create({'debit': 0.0,      'credit': 3 * mult, 'name': 'revenue', 'account_id': cls.company_data['default_account_revenue'].id}),
                ],
            }).action_post()

        invoice_move('2023-12-31')

        invoice_move('2024-01-05')
        invoice_move('2024-02-21', mult=100.0)
        invoice_move('2024-03-09')
        invoice_move('2024-04-10')

    def test_case_4_col_report_current_fiscal_year(self):
        report = self.env.ref('l10n_ro_reports.l10n_ro_trial_balance_4_column')
        report.filter_hierarchy = 'never'

        options = self._generate_options(report, fields.Date.from_string('2024-02-01'), fields.Date.from_string('2024-02-29'))

        self.assertLinesValues(
            report._get_lines(options),
            #                                                                  [ Initial Balance ]     [    Feb 2010     ]     [  Total Amounts  ]     [   End Balance   ]
            #                                                                    Debit      Credit      Debit       Credit       Debit     Credit        Debit      Credit
            [    0,                                                                 1,          2,         3,           4,          5,          6,          7,          8],
            [
                ("121000 Profit and loss",                                         0.0,     1000.0,       0.0,         0.0,         0.0,     1000.0,         0.0,     1000.0),
                ("401100 Providers - resumed in a period of up to one year",    2000.0,        0.0,     100.0,         0.0,      2100.0,        0.0,      2100.0,        0.0),
                ("601000 Raw material expenses",                                2000.0,        0.0,     200.0,         0.0,      2200.0,        0.0,      2200.0,        0.0),
                ("701500 Revenue from the sale of finished products",              0.0,     3000.0,       0.0,       300.0,         0.0,     3300.0,         0.0,     3300.0),
                ("Total",                                                       4000.0,     4000.0,     300.0,       300.0,      4300.0,     4300.0,      4300.0,     4300.0),
            ],
            options,
        )

    def test_case_5_col_report_with_4_col_edge_case(self):
        """
        When the date filter is set to the entire month of January, there should only be 4 columns in the report
        """
        report = self.env.ref('l10n_ro_reports.l10n_ro_trial_balance_5_column')
        report.filter_hierarchy = 'never'

        options = self._generate_options(report, '2024-01-01', '2024-01-31', default_options={'hierarchy': False})

        self.assertLinesValues(
            report._get_lines(options),
            #                                                                  [ Initial Balance ]     [    Jan 2024     ]     [  Total Amounts  ]     [   End Balance   ]
            #                                                                    Debit      Credit       Debit      Credit       Debit      Credit       Debit      Credit
            [    0,                                                                1,           2,          3,          4,          5,          6,          7,          8],
            [
                ("121000 Profit and loss",                                       0.0,      1000.0,        0.0,        0.0,        0.0,     1000.0,        0.0,     1000.0),
                ("401100 Providers - resumed in a period of up to one year",  1000.0,         0.0,     1000.0,        0.0,     2000.0,        0.0,     2000.0,        0.0),
                ("601000 Raw material expenses",                                 0.0,         0.0,     2000.0,        0.0,     2000.0,        0.0,     2000.0,        0.0),
                ("701500 Revenue from the sale of finished products",            0.0,         0.0,        0.0,     3000.0,        0.0,     3000.0,        0.0,     3000.0),
                ("Total",                                                     1000.0,      1000.0,     3000.0,     3000.0,     4000.0,     4000.0,     4000.0,     4000.0),
            ],
            options,
        )

    def test_case_5_col_report_current_fiscal_year(self):
        report = self.env.ref('l10n_ro_reports.l10n_ro_trial_balance_5_column')
        report.filter_hierarchy = 'never'

        options = self._generate_options(report, '2024-04-01', '2024-04-30', default_options={'hierarchy': False})

        self.assertLinesValues(
            report._get_lines(options),
            #                                                                  [ Initial Balance ]     [ Jan - Mar 2024 ]      [    Apr 2024     ]     [  Total Amounts  ]     [   End Balance   ]
            #                                                                   Debit       Credit       Debit      Credit      Debit       Credit       Debit      Credit       Debit      Credit
            [    0,                                                                1,           2,          3,          4,         5,           6,          7,          8,          9,         10],
            [
                ("121000 Profit and loss",                                       0.0,         0.0,        0.0,        0.0,       0.0,         0.0,        0.0,        0.0,        0.0,     1000.0),
                ("401100 Providers - resumed in a period of up to one year",  1000.0,         0.0,     2100.0,        0.0,    1000.0,         0.0,     4100.0,        0.0,     4100.0,        0.0),
                ("601000 Raw material expenses",                              2000.0,         0.0,     4200.0,        0.0,    2000.0,         0.0,     8200.0,        0.0,     6200.0,        0.0),
                ("701500 Revenue from the sale of finished products",            0.0,      3000.0,        0.0,     6300.0,       0.0,      3000.0,        0.0,    12300.0,        0.0,     9300.0),
                ("Total",                                                     3000.0,      3000.0,     6300.0,     6300.0,    3000.0,      3000.0,    12300.0,    12300.0,    10300.0,    10300.0),
            ],
            options,
        )
