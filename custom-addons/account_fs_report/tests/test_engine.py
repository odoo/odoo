from datetime import timedelta

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

ASSET_TYPES = (
    'asset_receivable,asset_cash,asset_current,asset_non_current,'
    'asset_prepayments,asset_fixed'
)
LIABILITY_TYPES = (
    'liability_payable,liability_credit_card,liability_current,liability_non_current'
)
EQUITY_TYPES = 'equity'


@tagged('post_install', '-at_install')
class TestFsReportEngine(AccountTestInvoicingCommon):

    def test_assets_equal_liabilities_plus_equity(self):
        company = self.env.company
        as_of = fields.Date.today()
        fiscal_year = company.compute_fiscalyear_dates(as_of)
        previous_date = fiscal_year['date_from'] - timedelta(days=1)
        no_tax = self.env['account.tax']
        self._create_invoice_one_line(
            price_unit=100.0,
            product_id=self.product_a,
            tax_ids=no_tax,
            invoice_date=previous_date,
            post=True,
        )
        self._create_invoice_one_line(
            price_unit=250.0,
            product_id=self.product_a,
            tax_ids=no_tax,
            invoice_date=as_of,
            post=True,
        )
        report = self.env['fs.report'].create({
            'name': 'Balance Sheet',
            'code': 'BS_TEST',
            'report_type': 'balance_sheet',
            'line_ids': [
                Command.create({
                    'sequence': 10,
                    'code': 'TA',
                    'name': 'Assets',
                    'formula_type': 'account_type',
                    'account_types': ASSET_TYPES,
                    'sign': 1,
                }),
                Command.create({
                    'sequence': 20,
                    'code': 'TL',
                    'name': 'Liabilities',
                    'formula_type': 'account_type',
                    'account_types': LIABILITY_TYPES,
                    'sign': -1,
                }),
                Command.create({
                    'sequence': 30,
                    'code': 'EQE',
                    'name': 'Equity (& Earnings)',
                    'formula_type': 'none',
                }),
                Command.create({
                    'sequence': 31,
                    'code': 'EQ',
                    'name': 'Equity',
                    'formula_type': 'account_type',
                    'account_types': EQUITY_TYPES,
                    'sign': -1,
                    'parent_id': False,
                }),
                Command.create({
                    'sequence': 40,
                    'code': 'CYE',
                    'name': 'Current Year Earnings',
                    'formula_type': 'current_earnings',
                    'sign': -1,
                }),
                Command.create({
                    'sequence': 50,
                    'code': 'PYE',
                    'name': 'Previous Years Earnings',
                    'formula_type': 'previous_earnings',
                    'sign': -1,
                }),
                Command.create({
                    'sequence': 60,
                    'code': 'TLE',
                    'name': 'Liabilities + Equity',
                    'formula_type': 'aggregation',
                    'aggregation': 'TL+EQ+CYE+PYE',
                }),
            ],
        })
        # Attach EQ/CYE/PYE under EQE for rollup used by TLE via EQ+CYE+PYE aggregation above.
        rows = self.env['fs.report.engine'].get_report_data(report.id, {
            'company_ids': company.ids,
            'target_move': 'posted',
            'columns': [{'label': 'As of', 'date_to': as_of}],
        })['lines']
        amounts = {row['code']: row['columns'][0] for row in rows}
        self.assertAlmostEqual(amounts['TA'], amounts['TLE'])
        self.assertAlmostEqual(amounts['CYE'], 250.0)
        self.assertAlmostEqual(amounts['PYE'], 100.0)

    def test_string_dates_and_all_account_types(self):
        company = self.env.company
        as_of = fields.Date.to_date('2026-12-31')
        fiscal_year = company.compute_fiscalyear_dates(as_of)
        expense = self.env['account.account'].create({
            'name': 'Other Expense',
            'code': '619997',
            'account_type': 'expense_other',
            'company_ids': [Command.link(company.id)],
        })
        retained = self.env['account.account'].create({
            'name': 'Retained Earnings',
            'code': '319997',
            'account_type': 'equity_retained',
            'company_ids': [Command.link(company.id)],
        })
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fiscal_year['date_from'],
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': expense.id,
                    'name': 'Other expense',
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': retained.id,
                    'name': 'Retained earnings',
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })
        move.action_post()
        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        rows = self.env['fs.report.engine'].get_report_data(report.id, {
            'company_ids': company.ids,
            'target_move': 'posted',
            'columns': [{'label': 'cur', 'date_to': '2026-12-31'}],
        })['lines']
        amounts = {row['code']: row['columns'][0] for row in rows}
        self.assertAlmostEqual(amounts['TA'], amounts['TLE'])

    def test_retained_account_counts_as_earnings(self):
        company = self.env.company
        as_of = fields.Date.today()
        fiscal_year = company.compute_fiscalyear_dates(as_of)
        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        options = {
            'company_ids': company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': as_of}],
        }
        before = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        retained = self.env['account.account'].create({
            'name': 'Retained Earnings Test',
            'code': '319998',
            'account_type': 'equity_retained',
            'company_ids': [Command.link(company.id)],
        })
        bank = self.company_data['default_account_revenue'].copy({
            'code': '101998',
            'name': 'Bank for retained test',
            'account_type': 'asset_cash',
        })
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fiscal_year['date_from'],
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': bank.id,
                    'name': 'Retained funding',
                    'debit': 5000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': retained.id,
                    'name': 'Retained earnings',
                    'debit': 0.0,
                    'credit': 5000.0,
                }),
            ],
        })
        move.action_post()
        after = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        self.assertAlmostEqual(after['CYE'] - before['CYE'], 5000.0)
        self.assertAlmostEqual(after['EQ'], before['EQ'])

    def test_unaffected_counts_as_earnings(self):
        company = self.env.company
        as_of = fields.Date.today()
        fiscal_year = company.compute_fiscalyear_dates(as_of)
        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        options = {
            'company_ids': company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': as_of}],
        }
        before = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        unaffected = self.env['account.account'].create({
            'name': 'Unaffected Earnings Test',
            'code': '399998',
            'account_type': 'equity_unaffected',
            'company_ids': [Command.link(company.id)],
        })
        bank = self.company_data['default_account_revenue'].copy({
            'code': '101997',
            'name': 'Bank for unaffected test',
            'account_type': 'asset_cash',
        })
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fiscal_year['date_from'],
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': bank.id,
                    'name': 'Unaffected funding',
                    'debit': 2000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': unaffected.id,
                    'name': 'Unaffected earnings',
                    'debit': 0.0,
                    'credit': 2000.0,
                }),
            ],
        })
        move.action_post()
        after = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        self.assertAlmostEqual(after['CYE'] - before['CYE'], 2000.0)
        self.assertAlmostEqual(after['EQ'], before['EQ'])

    def test_tree_order(self):
        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        rows = self.env['fs.report.engine'].get_report_data(report.id, {
            'company_ids': self.env.company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': fields.Date.today()}],
        })['lines']
        self.assertEqual(
            [r['code'] for r in rows],
            ['TA', 'CA', 'BANK', 'REC', 'CAO', 'PRE', 'FA', 'NCA',
             'TL', 'CL', 'CLO', 'CC', 'PAY', 'NCL',
             'EQE', 'EQ', 'ERN', 'CYE', 'PYE', 'TLE'],
        )
        self.assertEqual(
            [r['level'] for r in rows],
            [0, 1, 2, 2, 2, 2, 1, 1, 0, 1, 2, 2, 2, 1, 0, 1, 1, 2, 2, 0],
        )

    def test_fiscal_year_march(self):
        company = self.env.company
        month_field = company._fields['fiscalyear_last_month']
        march = '3' if month_field.type == 'selection' else 3
        company.write({'fiscalyear_last_day': 31, 'fiscalyear_last_month': march})
        bank = self.company_data['default_account_revenue'].copy({
            'code': '101996',
            'name': 'Bank for March FY test',
            'account_type': 'asset_cash',
        })
        income = self.company_data['default_account_revenue'].copy({
            'code': '401996',
            'name': 'Income for March FY test',
            'account_type': 'income',
        })
        journal = self.company_data['default_journal_misc']
        for date, amount in (('2025-02-10', 10000.0), ('2025-05-10', 4000.0)):
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': date,
                'journal_id': journal.id,
                'line_ids': [
                    Command.create({
                        'account_id': bank.id,
                        'name': f'March FY {date}',
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'account_id': income.id,
                        'name': f'March FY {date}',
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ],
            })
            move.action_post()
        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        options = {
            'company_ids': company.ids,
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': '2025-06-30'}],
        }
        amounts = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        self.assertAlmostEqual(amounts['CYE'], 4000.0)
        self.assertAlmostEqual(amounts['PYE'], 10000.0)
        options['columns'] = [{'label': 'cur', 'date_to': '2025-03-31'}]
        amounts = {
            row['code']: row['columns'][0]
            for row in self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        }
        self.assertAlmostEqual(amounts['CYE'], 10000.0)
        self.assertAlmostEqual(amounts['PYE'], 0.0)

    def test_multicurrency_translation(self):
        usd = self.env.ref('base.USD')
        inr = self.env.ref('base.INR')
        (usd | inr).write({'active': True})

        company_u = self.env.company
        company_u.currency_id = usd

        data_i = self.setup_other_company(name='Company I INR', currency_id=inr.id)
        company_i = data_i['company']
        self.env.user.write({'company_ids': [Command.link(company_i.id)]})

        Rate = self.env['res.currency.rate']
        Rate.create({
            'name': '2024-01-01',
            'rate': 80.0,
            'currency_id': inr.id,
            'company_id': company_u.id,
        })
        Rate.create({
            'name': '2025-01-01',
            'rate': 100.0,
            'currency_id': inr.id,
            'company_id': company_u.id,
        })

        bank = self.env['account.account'].create({
            'name': 'Bank INR',
            'code': '101900',
            'account_type': 'asset_cash',
            'company_ids': [Command.link(company_i.id)],
        })
        equity = self.env['account.account'].create({
            'name': 'Capital INR',
            'code': '301900',
            'account_type': 'equity',
            'company_ids': [Command.link(company_i.id)],
        })
        income = self.env['account.account'].create({
            'name': 'Income INR',
            'code': '401900',
            'account_type': 'income',
            'company_ids': [Command.link(company_i.id)],
        })
        journal = data_i['default_journal_misc']

        move_2024 = self.env['account.move'].with_company(company_i).create({
            'move_type': 'entry',
            'date': '2024-01-02',
            'journal_id': journal.id,
            'company_id': company_i.id,
            'line_ids': [
                Command.create({
                    'account_id': bank.id,
                    'name': 'Capital',
                    'debit': 8000000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': equity.id,
                    'name': 'Capital',
                    'debit': 0.0,
                    'credit': 8000000.0,
                }),
            ],
        })
        move_2024.action_post()

        move_2025 = self.env['account.move'].with_company(company_i).create({
            'move_type': 'entry',
            'date': '2025-03-01',
            'journal_id': journal.id,
            'company_id': company_i.id,
            'line_ids': [
                Command.create({
                    'account_id': bank.id,
                    'name': 'Income',
                    'debit': 1000000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': income.id,
                    'name': 'Income',
                    'debit': 0.0,
                    'credit': 1000000.0,
                }),
            ],
        })
        move_2025.action_post()

        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        options = {
            'company_ids': [company_u.id, company_i.id],
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': '2025-12-31'}],
        }
        rows = self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        amounts = {row['code']: row['columns'][0] for row in rows}
        self.assertAlmostEqual(amounts['BANK'], 90000.0)
        self.assertAlmostEqual(amounts['EQ'], 100000.0)
        self.assertAlmostEqual(amounts['CYE'], 10000.0)
        self.assertAlmostEqual(amounts['PYE'], 0.0)
        self.assertAlmostEqual(amounts['CTA'], -20000.0)
        self.assertAlmostEqual(amounts['TA'], amounts['TLE'])

        options['columns'] = [{'label': 'cur', 'date_to': '2024-12-31'}]
        rows = self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        codes = {row['code'] for row in rows}
        self.assertNotIn('CTA', codes)
        self.assertNotIn('OCI', codes)
        amounts = {row['code']: row['columns'][0] for row in rows}
        self.assertAlmostEqual(amounts['TA'], amounts['TLE'])

    def test_average_rate_current_year_earnings(self):
        usd = self.env.ref('base.USD')
        inr = self.env.ref('base.INR')
        (usd | inr).write({'active': True})

        company_u = self.env.company
        company_u.currency_id = usd

        data_i = self.setup_other_company(name='Company I AvgRate INR', currency_id=inr.id)
        company_i = data_i['company']
        self.env.user.write({'company_ids': [Command.link(company_i.id)]})

        Rate = self.env['res.currency.rate']
        Rate.create({
            'name': '2025-01-01',
            'rate': 100.0,
            'currency_id': inr.id,
            'company_id': company_u.id,
        })
        Rate.create({
            'name': '2025-05-01',
            'rate': 160.0,
            'currency_id': inr.id,
            'company_id': company_u.id,
        })

        bank = self.env['account.account'].create({
            'name': 'Bank INR AvgRate',
            'code': '101910',
            'account_type': 'asset_cash',
            'company_ids': [Command.link(company_i.id)],
        })
        income = self.env['account.account'].create({
            'name': 'Income INR AvgRate',
            'code': '401910',
            'account_type': 'income',
            'company_ids': [Command.link(company_i.id)],
        })
        journal = data_i['default_journal_misc']

        move = self.env['account.move'].with_company(company_i).create({
            'move_type': 'entry',
            'date': '2025-04-10',
            'journal_id': journal.id,
            'company_id': company_i.id,
            'line_ids': [
                Command.create({
                    'account_id': bank.id,
                    'name': 'Income',
                    'debit': 6000000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': income.id,
                    'name': 'Income',
                    'debit': 0.0,
                    'credit': 6000000.0,
                }),
            ],
        })
        move.action_post()

        report = self.env.ref('account_fs_report.fs_report_balance_sheet')
        options = {
            'company_ids': [company_u.id, company_i.id],
            'target_move': 'posted',
            'journal_ids': [],
            'columns': [{'label': 'cur', 'date_to': '2025-06-30'}],
        }
        rows = self.env['fs.report.engine'].get_report_data(report.id, options)['lines']
        amounts = {row['code']: row['columns'][0] for row in rows}
        self.assertAlmostEqual(amounts['CYE'], 52417.13, places=2)
        self.assertAlmostEqual(amounts['BANK'], 37500.0, places=2)
        self.assertAlmostEqual(amounts['EQ'], 0.0, places=2)
        self.assertAlmostEqual(amounts['CTA'], -14917.13, places=2)
        self.assertAlmostEqual(amounts['TA'], amounts['TLE'], places=2)
