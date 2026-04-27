# -*- coding: utf-8 -*-
# pylint: disable=C0326

from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestFinancialReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ==== Partners ====
        cls.partner_c = cls._create_partner(name='partner_c')

        # ==== Accounts ====

        # Cleanup existing "Current year earnings" accounts since we can only have one by company.
        cls.env['account.account'].search([
            ('company_ids', 'in', (cls.company_data['company'] + cls.company_data_2['company']).ids),
            ('account_type', '=', 'equity_unaffected'),
        ]).unlink()

        account_type_data = [
            ('asset_receivable',    {'reconcile': True}),
            ('liability_payable',   {'reconcile': True}),
            ('asset_cash',          {}),
            ('asset_current',       {}),
            ('asset_prepayments',   {}),
            ('asset_fixed',         {}),
            ('asset_non_current',   {}),
            ('equity',              {}),
            ('equity_unaffected',   {}),
            ('income',              {}),
        ]

        accounts = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % i,
            'code': 'code%s' % i,
            'account_type': data[0],
        } for i, data in enumerate(account_type_data)])

        accounts_2 = cls.env['account.account'].create([{
            **data[1],
            'name': 'account%s' % (i + 100),
            'code': 'code%s' % (i + 100),
            'account_type': data[0],
            'company_ids': [Command.link(cls.company_data_2['company'].id)]
        } for i, data in enumerate(account_type_data)])

        for account in accounts_2:
            account.code = account.with_company(cls.company_data_2['company']).code

        # ==== Custom filters ====

        cls.horizontal_group = cls.env['account.report.horizontal.group'].create({
            'name': 'Horizontal Group',
            'rule_ids': [
                Command.create({
                    'field_name': 'partner_id',
                    'domain': f"[('id', 'in', {(cls.partner_a + cls.partner_b).ids})]",
                }),
                Command.create({
                    'field_name': 'account_id',
                    'domain': f"[('id', 'in', {accounts[:2].ids})]",
                }),
            ],
        })

        # ==== Journal entries ====

        cls.move_2019 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2019-01-01'),
            'line_ids': [
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 25.0,      'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': accounts[1].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 300.0,    'account_id': accounts[2].id,   'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 400.0,     'credit': 0.0,      'account_id': accounts[3].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1100.0,   'account_id': accounts[4].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 700.0,     'credit': 0.0,      'account_id': accounts[6].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 800.0,    'account_id': accounts[7].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 800.0,     'credit': 0.0,      'account_id': accounts[8].id,   'partner_id': cls.partner_c.id}),
            ],
        })
        cls.move_2019.action_post()

        cls.move_2018 = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2018-01-01'),
            'line_ids': [
                (0, 0, {'debit': 1000.0,    'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 1000.0,   'account_id': accounts[2].id,   'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 250.0,     'credit': 0.0,      'account_id': accounts[0].id,   'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 250.0,    'account_id': accounts[9].id,   'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2018.action_post()

        cls.move_2017 = cls.env['account.move'].with_company(cls.company_data_2['company']).create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2017-01-01'),
            'line_ids': [
                (0, 0, {'debit': 2000.0,    'credit': 0.0,      'account_id': accounts_2[0].id, 'partner_id': cls.partner_a.id}),
                (0, 0, {'debit': 0.0,       'credit': 4000.0,   'account_id': accounts_2[2].id, 'partner_id': cls.partner_b.id}),
                (0, 0, {'debit': 0.0,       'credit': 5000.0,   'account_id': accounts_2[4].id, 'partner_id': cls.partner_c.id}),
                (0, 0, {'debit': 7000.0,    'credit': 0.0,      'account_id': accounts_2[6].id, 'partner_id': cls.partner_a.id}),
            ],
        })
        cls.move_2017.action_post()

        cls.report = cls.env.ref('account_reports.balance_sheet')

        cls.report_no_parent_id = cls.env["account.report"].create({
            'name': "Test report",

            'column_ids': [
                Command.create({
                    'name': 'Balance',
                    'expression_label': 'balance',
                    'sequence': 1
                })
            ],

            'line_ids': [
                Command.create({
                    'name': "Invisible Partner A line",
                    'code': "INVA",
                    'sequence': 1,
                    'hierarchy_level': 0,
                    'groupby': "account_id",
                    'foldable': True,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'domain',
                        'formula': [("partner_id", "=", cls.partner_a.id)],
                        'subformula': 'sum',
                    })],
                }),
                Command.create({
                    'name': "Invisible Partner B line",
                    'code': "INVB",
                    'sequence': 2,
                    'hierarchy_level': 0,
                    'groupby': "account_id",
                    'foldable': True,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'domain',
                        'formula': [("partner_id", "=", cls.partner_b.id)],
                        'subformula': 'sum',
                    })],
                }),
                Command.create({
                    'name': "Total of Invisible lines",
                    'code': "INVT",
                    'sequence': 3,
                    'hierarchy_level': 0,
                    'expression_ids': [Command.clear(), Command.create({
                        'label': 'balance',
                        'engine': 'aggregation',
                        'formula': 'INVA.balance + INVB.balance',
                    })],
                }),
            ],
        })

    def _build_generic_id_from_financial_line(self, financial_rep_ln_xmlid):
        report_line = self.env.ref(financial_rep_ln_xmlid)
        return '-account.financial.html.report.line-%s' % report_line.id

    def _get_line_id_from_generic_id(self, generic_id):
        return int(generic_id.split('-')[-1])

    def test_financial_report_strict_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range """
        self.report_no_parent_id.filter_multi_company = 'disabled'
        options = self._generate_options(self.report_no_parent_id, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))

        lines = self.report_no_parent_id._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                         Balance
            [   0,                           1],
            [
                ('Invisible Partner A line', 1150.0),
                ('Invisible Partner B line', -1675.0),
                ('Total of Invisible lines', -525.0),

            ],
            options,
        )

    def test_financial_report_strict_empty_range_on_report_lines_with_no_parent_id(self):
        """ Tests that lines with no parent can be correctly filtered by date range with no invoices"""
        self.report_no_parent_id.filter_multi_company = 'disabled'
        options = self._generate_options(self.report_no_parent_id, fields.Date.from_string('2019-03-01'), fields.Date.from_string('2019-03-31'))

        lines = self.report_no_parent_id._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                          Balance
            [   0,                            1],
            [
                ('Invisible Partner A line',  0.0),
                ('Invisible Partner B line',  0.0),
                ('Total of Invisible lines',  0.0),
            ],
            options,
        )

    @freeze_time("2016-06-06")
    def test_balance_sheet_today_current_year_earnings(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-02-02',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 110,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.report.filter_multi_company = 'disabled'
        options = self._generate_options(self.report, fields.Date.from_string('2016-06-01'), fields.Date.from_string('2016-06-06'))
        options['date']['filter'] = 'today'

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      110.0),
                ('Current Assets',                              110.0),
                ('Bank and Cash Accounts',                        0.0),
                ('Receivables',                                 110.0),
                ('Current Assets',                                0.0),
                ('Prepayments',                                   0.0),
                ('Total Current Assets',                        110.0),
                ('Plus Fixed Assets',                             0.0),
                ('Plus Non-current Assets',                       0.0),
                ('Total ASSETS',                                110.0),

                ('LIABILITIES',                                   0.0),
                ('Current Liabilities',                           0.0),
                ('Current Liabilities',                           0.0),
                ('Payables',                                      0.0),
                ('Total Current Liabilities',                     0.0),
                ('Plus Non-current Liabilities',                  0.0),
                ('Total LIABILITIES',                             0.0),

                ('EQUITY',                                      110.0),
                ('Unallocated Earnings',                        110.0),
                ('Current Year Unallocated Earnings',           110.0),
                ('Previous Years Unallocated Earnings',           0.0),
                ('Total Unallocated Earnings',                  110.0),
                ('Retained Earnings',                             0.0),
                ('Current Year Retained Earnings',                0.0),
                ('Previous Years Retained Earnings',              0.0),
                ('Total Retained Earnings',                       0.0),
                ('Total EQUITY',                                110.0),

                ('LIABILITIES + EQUITY',                        110.0),
            ],
            options,
        )

    @freeze_time("2016-05-05")
    def test_balance_sheet_last_month_vs_custom_current_year_earnings(self):
        """
        Checks the balance sheet calls the right period of the P&L when using last_month date filter, or an equivalent custom filter
        (this used to fail due to options regeneration made by the P&L's get_options())"
        """
        to_invoice = [('15', '11'), ('15', '12'), ('16', '01'), ('16', '02'), ('16', '03'), ('16', '04')]
        for year, month in to_invoice:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': f'20{year}-{month}-01',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000,
                    'tax_ids': [],
                })]
            })
            invoice.action_post()
        expected_result =[
                ('ASSETS',                                      6000.0),
                ('Current Assets',                              6000.0),
                ('Bank and Cash Accounts',                         0.0),
                ('Receivables',                                 6000.0),
                ('Current Assets',                                 0.0),
                ('Prepayments',                                    0.0),
                ('Total Current Assets',                        6000.0),
                ('Plus Fixed Assets',                              0.0),
                ('Plus Non-current Assets',                        0.0),
                ('Total ASSETS',                                6000.0),

                ('LIABILITIES',                                    0.0),
                ('Current Liabilities',                            0.0),
                ('Current Liabilities',                            0.0),
                ('Payables',                                       0.0),
                ('Total Current Liabilities',                      0.0),
                ('Plus Non-current Liabilities',                   0.0),
                ('Total LIABILITIES',                              0.0),

                ('EQUITY',                                      6000.0),
                ('Unallocated Earnings',                        6000.0),
                ('Current Year Unallocated Earnings',           4000.0),
                ('Previous Years Unallocated Earnings',         2000.0),
                ('Total Unallocated Earnings',                  6000.0),
                ('Retained Earnings',                              0.0),
                ('Current Year Retained Earnings',                 0.0),
                ('Previous Years Retained Earnings',               0.0),
                ('Total Retained Earnings',                        0.0),
                ('Total EQUITY',                                6000.0),
                ('LIABILITIES + EQUITY',                        6000.0),

            ]
        self.report.filter_multi_company = 'disabled'
        options = self._generate_options(self.report, fields.Date.from_string('2016-05-05'), fields.Date.from_string('2016-05-05'))

        # End of Last Month
        options['date']['filter'] = 'last_month'
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
            options,
        )
        # Custom
        options['date']['filter'] = 'custom'
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            expected_result,
            options,
        )

    def test_financial_report_single_company(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        self.report.filter_multi_company = 'disabled'
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                        50.0),
                ('Current Assets',                              -650.0),
                ('Bank and Cash Accounts',                     -1300.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -1300.0),
                ('Receivables',                                 1350.0),
                ('Current Assets',                               400.0),
                ('Prepayments',                                -1100.0),
                ('Total Current Assets',                        -650.0),
                ('Plus Fixed Assets',                              0.0),
                ('Plus Non-current Assets',                      700.0),
                ('Total ASSETS',                                  50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                            0.0),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                   0.0),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                       250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Previous Years Unallocated Earnings',          250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                            800.0),
                ('Current Year Retained Earnings',               800.0),
                ('Previous Years Retained Earnings',               0.0),
                ('Total Retained Earnings',                      800.0),
                ('Total EQUITY',                                 250.0),

                ('LIABILITIES + EQUITY',                          50.0),
            ],
            options,
        )

        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        self.assertLinesValues(
            unfolded_lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                      -1300.0),
                ('code2 account2',                              -1300.0),
                ('Total Bank and Cash Accounts',                -1300.0),
            ],
            options,
        )

    def test_financial_report_multi_company_currency(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options['unfolded_lines'] = [line_id]

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                        50.0),
                ('Current Assets',                             -4150.0),
                ('Bank and Cash Accounts',                     -3300.0),
                ('code102 account102',                         -2000.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -3300.0),
                ('Receivables',                                 2350.0),
                ('Current Assets',                               400.0),
                ('Prepayments',                                -3600.0),
                ('Total Current Assets',                       -4150.0),
                ('Plus Fixed Assets',                              0.0),
                ('Plus Non-current Assets',                     4200.0),
                ('Total ASSETS',                                  50.0),

                ('LIABILITIES',                                 -200.0),
                ('Current Liabilities',                         -200.0),
                ('Current Liabilities',                            0.0),
                ('Payables',                                    -200.0),
                ('Total Current Liabilities',                   -200.0),
                ('Plus Non-current Liabilities',                   0.0),
                ('Total LIABILITIES',                           -200.0),

                ('EQUITY',                                       250.0),
                ('Unallocated Earnings',                        -550.0),
                ('Current Year Unallocated Earnings',           -800.0),
                ('Previous Years Unallocated Earnings',          250.0),
                ('Total Unallocated Earnings',                  -550.0),
                ('Retained Earnings',                            800.0),
                ('Current Year Retained Earnings',               800.0),
                ('Previous Years Retained Earnings',               0.0),
                ('Total Retained Earnings',                      800.0),
                ('Total EQUITY',                                 250.0),

                ('LIABILITIES + EQUITY',                          50.0),
            ],
            options,
        )

        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        self.assertLinesValues(
            unfolded_lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('Bank and Cash Accounts',                     -3300.0),
                ('code102 account102',                         -2000.0),
                ('code2 account2',                             -1300.0),
                ('Total Bank and Cash Accounts',               -3300.0),
            ],
            options,
        )

    def test_financial_report_comparison(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(self.report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))
        options['unfolded_lines'] = [line_id]

        lines = self.report._get_lines(options)

        self.assertColumnPercentComparisonValues(
            lines,
            [
                ('ASSETS',                                      '-80.0%',       'red'),
                ('Current Assets',                              '27.7%',        'red'),
                ('Bank and Cash Accounts',                      '10.0%',        'red'),
                ('code102 account102',                          '0.0%',       'muted'),
                ('code2 account2',                              '30.0%',        'red'),
                ('Total Bank and Cash Accounts',                '10.0%',        'red'),
                ('Receivables',                                 '4.4%',       'green'),
                ('Current Assets',                              'n/a',        'muted'),
                ('Prepayments',                                 '44.0%',        'red'),
                ('Total Current Assets',                        '27.7%',        'red'),
                ('Plus Fixed Assets',                           'n/a',        'muted'),
                ('Plus Non-current Assets',                     '20.0%',      'green'),
                ('Total ASSETS',                                '-80.0%',       'red'),

                ('LIABILITIES',                                 'n/a',        'muted'),
                ('Current Liabilities',                         'n/a',        'muted'),
                ('Current Liabilities',                         'n/a',        'muted'),
                ('Payables',                                    'n/a',        'muted'),
                ('Total Current Liabilities',                   'n/a',        'muted'),
                ('Plus Non-current Liabilities',                'n/a',        'muted'),
                ('Total LIABILITIES',                           'n/a',        'muted'),

                ('EQUITY',                                      '0.0%',       'muted'),
                ('Unallocated Earnings',                        '-320.0%',      'red'),
                ('Current Year Unallocated Earnings',           '-420.0%',      'red'),
                ('Previous Years Unallocated Earnings',         'n/a',        'muted'),
                ('Total Unallocated Earnings',                  '-320.0%',      'red'),
                ('Retained Earnings',                           'n/a',        'muted'),
                ('Current Year Retained Earnings',              'n/a',        'muted'),
                ('Previous Years Retained Earnings',            'n/a',        'muted'),
                ('Total Retained Earnings',                     'n/a',        'muted'),
                ('Total EQUITY',                                '0.0%',       'muted'),


                ('LIABILITIES + EQUITY',                        '-80.0%',     'green'),
            ]
        )

    def test_financial_report_horizontal_group(self):
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_receivable0')
        self.report.horizontal_group_ids |= self.horizontal_group

        options = self._generate_options(
            self.report,
            fields.Date.from_string('2019-01-01'),
            fields.Date.from_string('2019-12-31'),
            default_options={
                'unfolded_lines': [line_id],
                'selected_horizontal_group_id': self.horizontal_group.id,
            }
        )
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))

        lines = self.report._get_lines(options)
        self.assertHeadersValues(
            options['column_headers'],
            [
                ['As of 12/31/2019', 'As of 12/31/2018'],
                ['partner_a', 'partner_b'],
                ['code0 account0', 'code1 account1'],
            ]
        )
        self.assertLinesValues(
            lines,
            [   0,                                          1,                   2,                  3,                  4,                  5,                  6,                  7,                  8],
            [
                ('ASSETS',                                  1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('Current Assets',                          1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('Bank and Cash Accounts',                 0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Receivables',                             1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('code0 account0',                          1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('Total Receivables',                       1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('Current Assets',                         0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Prepayments',                            0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Current Assets',                    1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),
                ('Plus Fixed Assets',                      0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Plus Non-current Assets',                0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total ASSETS',                            1300.0,             0.0,                 25.0,              0.0,                 1250.0,            0.0,                0.0,                0.0),

                ('LIABILITIES',                            0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),
                ('Current Liabilities',                    0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),
                ('Current Liabilities',                    0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Payables',                               0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),
                ('Total Current Liabilities',              0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),
                ('Plus Non-current Liabilities',           0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total LIABILITIES',                      0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),

                ('EQUITY',                                 0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Unallocated Earnings',                   0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Current Year Unallocated Earnings',      0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Previous Years Unallocated Earnings',    0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Unallocated Earnings',             0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Retained Earnings',                      0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Current Year Retained Earnings',         0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Previous Years Retained Earnings',       0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total Retained Earnings',                0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),
                ('Total EQUITY',                           0.0,                 0.0,                0.0,                0.0,                0.0,                0.0,                0.0,                0.0),

                ('LIABILITIES + EQUITY',                   0.0,                 0.0,                0.0,                -200.0,             0.0,                0.0,                0.0,                0.0),
            ],
            options,
        )

    def test_financial_report_horizontal_group_total(self):
        """
        In case we don't have comparison, just one column and one level of groupby a new column is added which is the total
        of the horizontal group
        """
        horizontal_group = self.env['account.report.horizontal.group'].create({
            'name': 'Horizontal Group total',
            'rule_ids': [
                Command.create({
                    'field_name': 'partner_id',
                    'domain': f"[('id', 'in', {(self.partner_a + self.partner_b).ids})]",
                }),
            ],
        })
        self.report.horizontal_group_ids |= horizontal_group
        options = self._generate_options(self.report, '2019-01-01', '2019-12-31', default_options={'selected_horizontal_group_id': horizontal_group.id})
        self.assertHeadersValues(
            options['column_headers'],
            [
                ['As of 12/31/2019'],
                ['partner_a', 'partner_b'],
            ]
        )

        self.assertTrue(options['show_horizontal_group_total'])
        # Since we don't calculate the value when totals below section is activated, we disable it
        self.env.company.totals_below_sections = False
        self.assertHorizontalGroupTotal(
            self.report._get_lines(options),
            [
                ('ASSETS',                                      6900.0,          -4075.0,        2825.0),
                ('Current Assets',                              2700.0,          -4075.0,       -1375.0),
                ('Bank and Cash Accounts',                         0.0,          -3000.0,       -3000.0),
                ('Receivables',                                 2300.0,             25.0,        2325.0),
                ('Current Assets',                               400.0,              0.0,         400.0),
                ('Prepayments',                                    0.0,          -1100.0,       -1100.0),
                ('Plus Fixed Assets',                              0.0,              0.0,           0.0),
                ('Plus Non-current Assets',                     4200.0,              0.0,        4200.0),
                ('LIABILITIES',                                    0.0,           -200.0,        -200.0),
                ('Current Liabilities',                            0.0,           -200.0,        -200.0),
                ('Current Liabilities',                            0.0,              0.0,           0.0),
                ('Payables',                                       0.0,           -200.0,        -200.0),
                ('Plus Non-current Liabilities',                   0.0,              0.0,           0.0),
                ('EQUITY',                                       250.0,            800.0,        1050.0),
                ('Unallocated Earnings',                         250.0,              0.0,         250.0),
                ('Current Year Unallocated Earnings',              0.0,              0.0,           0.0),
                ('Previous Years Unallocated Earnings',          250.0,              0.0,         250.0),
                ('Retained Earnings',                              0.0,            800.0,         800.0),
                ('Current Year Retained Earnings',                 0.0,            800.0,         800.0),
                ('Previous Years Retained Earnings',               0.0,              0.0,           0.0),
                ('LIABILITIES + EQUITY',                         250.0,            600.0,         850.0),
            ],
        )

        options = self._generate_options(self.report, '2019-01-01', '2019-12-31', default_options={'selected_horizontal_group_id': horizontal_group.id})
        options = self._update_comparison_filter(options, self.report, 'custom', 1, date_to=fields.Date.from_string('2018-12-31'))
        self.assertHeadersValues(
            options['column_headers'],
            [
                ['As of 12/31/2019', 'As of 12/31/2018'],
                ['partner_a', 'partner_b'],
            ]
        )

        self.assertFalse(options['show_horizontal_group_total'])

        self.assertHorizontalGroupTotal(
            self.report._get_lines(options),
            [
                ('ASSETS',                                      6900.0,             -4075.0,     5750.0,     -3000.0),
                ('Current Assets',                              2700.0,             -4075.0,     2250.0,     -3000.0),
                ('Bank and Cash Accounts',                         0.0,             -3000.0,        0.0,     -3000.0),
                ('Receivables',                                 2300.0,                25.0,     2250.0,         0.0),
                ('Current Assets',                               400.0,                 0.0,        0.0,         0.0),
                ('Prepayments',                                    0.0,             -1100.0,        0.0,         0.0),
                ('Plus Fixed Assets',                              0.0,                 0.0,        0.0,         0.0),
                ('Plus Non-current Assets',                     4200.0,                 0.0,     3500.0,         0.0),
                ('LIABILITIES',                                    0.0,              -200.0,        0.0,         0.0),
                ('Current Liabilities',                            0.0,              -200.0,        0.0,         0.0),
                ('Current Liabilities',                            0.0,                 0.0,        0.0,         0.0),
                ('Payables',                                       0.0,              -200.0,        0.0,         0.0),
                ('Plus Non-current Liabilities',                   0.0,                 0.0,        0.0,         0.0),
                ('EQUITY',                                       250.0,               800.0,      250.0,         0.0),
                ('Unallocated Earnings',                         250.0,                 0.0,      250.0,         0.0),
                ('Current Year Unallocated Earnings',              0.0,                 0.0,      250.0,         0.0),
                ('Previous Years Unallocated Earnings',          250.0,                 0.0,        0.0,         0.0),
                ('Retained Earnings',                              0.0,               800.0,        0.0,         0.0),
                ('Current Year Retained Earnings',                 0.0,               800.0,        0.0,         0.0),
                ('Previous Years Retained Earnings',               0.0,                 0.0,        0.0,         0.0),
                ('LIABILITIES + EQUITY',                         250.0,               600.0,      250.0,         0.0),
            ],
        )

    def test_hide_if_zero_with_no_formulas(self):
        """
        Check if a report line stays displayed when hide_if_zero is True and no formulas
        is set on the line but has some child which have balance != 0
        We check also if the line is hidden when all its children have balance == 0
        """
        account1, account2 = self.env['account.account'].create([{
            'name': "test_financial_report_1",
            'code': "42241",
            'account_type': "asset_fixed",
        }, {
            'name': "test_financial_report_2",
            'code': "42242",
            'account_type': "asset_fixed",
        }])

        moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': account1.id}),
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-05-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 1.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
            {
                'move_type': 'entry',
                'date': '2019-04-01',
                'line_ids': [
                    (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': account2.id}),
                    (0, 0, {'debit': 3.0, 'credit': 0.0, 'account_id': self.company_data['default_account_revenue'].id}),
                ],
            },
        ])
        moves.action_post()
        moves.line_ids.flush_recordset()

        report = self.env["account.report"].create({
            'name': "test_financial_report_sum",
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                    'sequence': 1,
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': "Title",
                    'code': 'TT',
                    'hide_if_zero': True,
                    'sequence': 0,
                    'children_ids': [
                        Command.create({
                            'name': "report_line_1",
                            'code': 'TEST_L1',
                            'sequence': 1,
                            'expression_ids': [
                                Command.create({
                                    'label': 'balance',
                                    'engine': 'domain',
                                    'formula': f"[('account_id', '=', {account1.id})]",
                                    'subformula': 'sum',
                                    'date_scope': 'from_beginning',
                                }),
                            ],
                        }),
                        Command.create({
                            'name': "report_line_2",
                            'code': 'TEST_L2',
                            'sequence': 2,
                            'expression_ids': [
                                Command.create({
                                    'label': 'balance',
                                    'engine': 'domain',
                                    'formula': f"[('account_id', '=', {account2.id})]",
                                    'subformula': 'sum',
                                    'date_scope': 'from_beginning',
                                }),
                            ],
                        }),
                    ]
                }),
            ],
        })

        # TODO without this, the create() puts newIds in the sublines, and flushing doesn't help. Seems to be an ORM bug.
        self.env.invalidate_all()

        options = self._generate_options(report, fields.Date.from_string('2019-05-01'), fields.Date.from_string('2019-05-01'))
        options = self._update_comparison_filter(options, report, 'previous_period', 2)

        self.assertLinesValues(
            report._get_lines(options),
            [   0,                                   1,       2,       3],
            [
                ("Title",                           '',      '',      ''),
                ("report_line_1",                  3.0,     3.0,     0.0),
                ("report_line_2",                 -4.0,    -3.0,     0.0),
            ],
            options,
        )

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-05-01',
            'line_ids': [
                (0, 0, {'debit': 0.0, 'credit': 3.0, 'account_id': account1.id}),
                (0, 0, {'debit': 4.0, 'credit': 0.0, 'account_id': account2.id}),
                (0, 0, {'debit': 0.0, 'credit': 1.0, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        move.action_post()
        move.line_ids.flush_recordset()

        # With the comparison still on, the lines shouldn't be hidden
        self.assertLinesValues(
            report._get_lines(options),
            [   0,                                   1,       2,       3],
            [
                ("Title",                           '',      '',      ''),
                ("report_line_1",                  0.0,     3.0,     0.0),
                ("report_line_2",                  0.0,    -3.0,     0.0),
            ],
            options,
        )

        # Removing the comparison should hide the lines, as they will be 0 in every considered period (the current one)
        options = self._update_comparison_filter(options, report, 'previous_period', 0)
        self.assertLinesValues(report._get_lines(options), [0, 1, 2, 3], [], options)

    def test_option_hierarchy(self):
        """ Check that the report lines are correct when the option "Hierarchy and subtotals is ticked"""
        self.env['account.group'].create({
            'name': 'Sales',
            'code_prefix_start': '40',
            'code_prefix_end': '49',
        })

        move = self.env['account.move'].create({
            'date': '2020-02-02',
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_revenue'].id,
                    'name': 'name',
                })
            ],
        })
        move.action_post()
        move.line_ids.flush_recordset()
        profit_and_loss_report = self.env.ref('account_reports.profit_and_loss')
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_revenue0')
        options = self._generate_options(profit_and_loss_report, '2020-02-01', '2020-02-28')
        options['unfolded_lines'] = [line_id]
        options['hierarchy'] = True
        self.env.company.totals_below_sections = False
        lines = profit_and_loss_report._get_lines(options)

        unfolded_lines = profit_and_loss_report._get_unfolded_lines(lines, line_id)
        unfolded_lines = [{'name': line['name'], 'level': line['level']} for line in unfolded_lines]

        self.assertEqual(
            unfolded_lines,
            [
                {'level': 1, 'name': 'Revenue'},
                {'level': 2, 'name': '40-49 Sales'},
                {'level': 3, 'name': '400000 Product Sales'},
            ]
        )

    def test_option_hierarchy_with_no_group_lines(self):
        """ Check that the report lines of 'No Group' have correct ids with the option 'Hierarchy and subtotals' """
        self.env['account.group'].create({
            'name': 'Sales',
            'code_prefix_start': '45',
            'code_prefix_end': '49',
        })

        move = self.env['account.move'].create({
            'date': '2020-02-02',
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_revenue'].id,
                    'name': 'name',
                })
            ],
        })
        move.action_post()
        move.line_ids.flush_recordset()
        profit_and_loss_report = self.env.ref('account_reports.profit_and_loss')
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_revenue0')
        options = self._generate_options(profit_and_loss_report, '2020-02-01', '2020-02-28')
        options['unfolded_lines'] = [line_id]
        options['hierarchy'] = True
        self.env.company.totals_below_sections = False
        lines = profit_and_loss_report._get_lines(options)
        lines_array = [{'name': line['name'], 'level': line['level']} for line in lines]

        self.assertEqual(
            lines_array,
            [
                {'name': 'Revenue', 'level': 1},
                {'name': '(No Group)', 'level': 2},
                {'name': '400000 Product Sales', 'level': 3},
                {'name': 'Less Costs of Revenue', 'level': 1},
                {'name': 'Gross Profit', 'level': 0},
                {'name': 'Less Operating Expenses', 'level': 1},
                {'name': 'Operating Income (or Loss)', 'level': 0},
                {'name': 'Plus Other Income', 'level': 1},
                {'name': 'Less Other Expenses', 'level': 1},
                {'name': 'Net Profit', 'level': 0},
            ]
        )

        self.assertEqual(lines[1]['id'], lines[0]['id'] + '|' + '~account.group~')

    def test_parse_line_id(self):
        line_id_1 = self.env['account.report']._parse_line_id('markup1~account.account~5|markup2~res.partner~8|markup3~~')
        line_id_2 = self.env['account.report']._parse_line_id('~account.report~14|{"groupby_prefix_group": "~"}~account.report~21')

        self.assertEqual(line_id_1, [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8), ('markup3', None, None)])
        self.assertEqual(line_id_2, [('', 'account.report', 14), ({"groupby_prefix_group": "~"}, 'account.report', 21)])
