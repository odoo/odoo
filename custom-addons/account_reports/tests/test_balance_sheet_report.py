# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=bad-whitespace
from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBalanceSheetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.report = cls.env.ref('account_reports.balance_sheet')

    def test_report_lines_ordering(self):
        """ Check that the report lines are correctly ordered with nested account groups """
        self.env['account.group'].create([{
            'name': 'A',
            'code_prefix_start': '101401',
            'code_prefix_end': '101601',
        }, {
            'name': 'A1',
            'code_prefix_start': '1014010',
            'code_prefix_end': '1015010',
        }])

        cid = self.env.company.id
        account_bank = self.env.ref(f"account.{cid}_bank").default_account_id
        account_cash = self.env.ref(f"account.{cid}_cash").default_account_id
        account_a = self.env['account.account'].create([{'code': '1014010', 'name': 'A', 'account_type': 'asset_cash'}])
        account_c = self.env['account.account'].create([{'code': '101600', 'name': 'C', 'account_type': 'asset_cash'}])

        # Create a journal lines for each account
        move = self.env['account.move'].create({
            'date': '2020-02-02',
            'line_ids': [
                Command.create({
                    'account_id': account.id,
                    'name': 'name',
                })
                for account in [account_a, account_c, account_bank, account_cash]
            ],
        })
        move.action_post()
        move.line_ids.flush_recordset()

        # Create the report hierarchy with the Bank and Cash Accounts lines unfolded
        line_id = self._get_basic_line_dict_id_from_report_line_ref('account_reports.account_financial_report_bank_view0')
        options = self._generate_options(
            self.report,
            fields.Date.from_string('2020-02-01'),
            fields.Date.from_string('2020-02-28')
        )
        options['unfolded_lines'] = [line_id]
        options['hierarchy'] = True
        self.env.company.totals_below_sections = False
        lines = self.report._get_lines(options)

        # The Bank and Cash Accounts section start at index 2
        # Since we created 4 lines + 2 groups, we keep the 6 following lines
        unfolded_lines = self.report._get_unfolded_lines(lines, line_id)
        unfolded_lines = [{'name': line['name'], 'level': line['level']} for line in unfolded_lines]

        self.assertEqual(
            unfolded_lines,
            [
                {'level': 5, 'name': 'Bank and Cash Accounts'},
                {'level': 6, 'name': '101401-101601 A'},
                {'level': 7, 'name': '101401 Bank'},
                {'level': 7, 'name': '1014010-1015010 A1'},
                {'level': 8, 'name': '1014010 A'},
                {'level': 8, 'name': '101501 Cash'},
                {'level': 7, 'name': '101600 C'},
            ]
        )

    def test_balance_sheet_custom_date(self):
        line_id = self.env.ref('account_reports.account_financial_report_bank_view0').id
        self.report.filter_multi_company = 'disabled'
        options = self._generate_options(self.report, fields.Date.from_string('2020-02-01'), fields.Date.from_string('2020-02-28'))
        options['date']['filter'] = 'custom'
        options['unfolded_lines'] = [line_id]

        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2020-0%s-15' % i,
            'invoice_date': '2020-0%s-15' % i,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        } for i in range(1, 4)])
        invoices.action_post()

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #   Name                                            Balance
            [   0,                                              1],
            [
                ('ASSETS',                                      2300.00),
                ('Current Assets',                              2300.00),
                ('Bank and Cash Accounts',                         0.00),
                ('Receivables',                                 2300.00),
                ('Current Assets',                                 0.00),
                ('Prepayments',                                    0.00),
                ('Total Current Assets',                        2300.00),
                ('Plus Fixed Assets',                              0.00),
                ('Plus Non-current Assets',                        0.00),
                ('Total ASSETS',                                2300.00),

                ('LIABILITIES',                                 300.00),
                ('Current Liabilities',                         300.00),
                ('Current Liabilities',                         300.00),
                ('Payables',                                       0.00),
                ('Total Current Liabilities',                   300.00),
                ('Plus Non-current Liabilities',                   0.00),
                ('Total LIABILITIES',                           300.00),

                ('EQUITY',                                      2000.00),
                ('Unallocated Earnings',                        2000.00),
                ('Current Year Unallocated Earnings',           2000.00),
                ('Current Year Earnings',                       2000.00),
                ('Current Year Allocated Earnings',                0.00),
                ('Total Current Year Unallocated Earnings',     2000.00),
                ('Previous Years Unallocated Earnings',            0.00),
                ('Total Unallocated Earnings',                  2000.00),
                ('Retained Earnings',                              0.00),
                ('Total EQUITY',                                2000.00),
                ('LIABILITIES + EQUITY',                        2300.00),
            ],
            options,
        )

    def test_unfold_all_and_total_lines(self):
        """ Check that exactly the total lines we want exist when we use the 'unfold_all' option. I.e. empty sections should not have total lines (since there are not lines to total).
        This test only tests the function '_get_lines'. It does not test that the total lines are always handled correctly for manual unfolds in the web UI. """

        self.env.company.totals_below_sections = True
        options = self._generate_options(
            self.report,
            fields.Date.from_string('1990-01-01'),
            fields.Date.from_string('1990-01-01')
        )

        bank_journal = self.company_data['default_journal_bank']
        account_bank = bank_journal.default_account_id
        account_other = self.env['account.account'].create({
            'account_type': 'asset_current',
            'name': 'account_other',
            'code': '121040',
            'reconcile': True,
        })
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '1990-01-01',
            'journal_id': bank_journal.id,
            'line_ids': [
                (0, 0, {'debit': 200.0,     'credit':   0.0,     'account_id': account_bank.id}),
                (0, 0, {'debit':   0.0,     'credit': 200.0,     'account_id': account_other.id}),
            ],
        }).action_post()

        # Note that assertLinesValues filters / ignores children lines of folded lines.
        # The total lines for the 2 visible lines with groupbys already exist in 'folded_lines' but are filtered / ignored by assertLinesValues.
        # (Thus they do not appear in the expected result below either.)
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name
            [   0],
            [
                ('ASSETS',),
                ('Current Assets',),
                ('Bank and Cash Accounts',),
                ('Receivables',),
                ('Current Assets',),
                ('Prepayments',),
                ('Total Current Assets',),
                ('Plus Fixed Assets',),
                ('Plus Non-current Assets',),
                ('Total ASSETS',),
                ('LIABILITIES',),
                ('Current Liabilities',),
                ('Current Liabilities',),
                ('Payables',),
                ('Total Current Liabilities',),
                ('Plus Non-current Liabilities',),
                ('Total LIABILITIES',),
                ('EQUITY',),
                ('Unallocated Earnings',),
                ('Current Year Unallocated Earnings',),
                ('Current Year Earnings',),
                ('Current Year Allocated Earnings',),
                ('Total Current Year Unallocated Earnings',),
                ('Previous Years Unallocated Earnings',),
                ('Total Unallocated Earnings',),
                ('Retained Earnings',),
                ('Total EQUITY',),
                ('LIABILITIES + EQUITY',),
            ],
            options,
        )

        options['unfold_all'] = True
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name
            [   0],
            [
                ('ASSETS',),
                ('Current Assets',),
                ('Bank and Cash Accounts',),
                (account_bank.display_name,),
                ('Total Bank and Cash Accounts',),
                ('Receivables',),
                ('Current Assets',),
                (account_other.display_name,),
                ('Total Current Assets',),
                ('Prepayments',),
                ('Total Current Assets',),
                ('Plus Fixed Assets',),
                ('Plus Non-current Assets',),
                ('Total ASSETS',),
                ('LIABILITIES',),
                ('Current Liabilities',),
                ('Current Liabilities',),
                ('Payables',),
                ('Total Current Liabilities',),
                ('Plus Non-current Liabilities',),
                ('Total LIABILITIES',),
                ('EQUITY',),
                ('Unallocated Earnings',),
                ('Current Year Unallocated Earnings',),
                ('Current Year Earnings',),
                ('Current Year Allocated Earnings',),
                ('Total Current Year Unallocated Earnings',),
                ('Previous Years Unallocated Earnings',),
                ('Total Unallocated Earnings',),
                ('Retained Earnings',),
                ('Total EQUITY',),
                ('LIABILITIES + EQUITY',),
            ],
            options,
        )
