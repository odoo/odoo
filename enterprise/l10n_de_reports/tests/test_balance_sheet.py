from freezegun import freeze_time
from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class GermanyBalanceSheetReportTest(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_chart_template('de_skr03')
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.report = cls.env.ref('l10n_de_reports.balance_sheet_l10n_de')

    @freeze_time('2025-03-17')
    def test_balance_sheet_unaffected_carry_over(self):
        _invoice_1 = self.init_invoice('out_invoice', invoice_date='2024-03-17', post=True, amounts=[1000])
        _invoice_2 = self.init_invoice('out_invoice', invoice_date='2025-03-17', post=True, amounts=[1000])

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_year'}, 'comparison': {'filter': 'previous_period', 'number_period': 1}})

        expected_lines = [
            # name                                                                                                              2025                                    2024
            ('Assets',                                                                                             f'2,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('A. Fixed assets',                                                                                        f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('I. Intangible assets',                                                                                   f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Self-generated industrial property rights and similar rights and assets',                             f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Concessions, licenses and similar rights and assets',                                                 f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Goodwill',                                                                                            f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Prepayments on intangible assets',                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('II. Tangible assets',                                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Land, land rights and buildings',                                                                     f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Technical equipment and machines',                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Other equipment, factory and office equipment',                                                       f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Prepayments on intangible assets and construction in progress',                                       f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('III. Financial assets',                                                                                  f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Shares in affiliated companies',                                                                      f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Loans to affiliated companies',                                                                       f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Participations',                                                                                      f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Loans to companies in which participations are held',                                                 f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('5. Long-term investments',                                                                               f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('6. Other loans',      				                                                                   f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('B. Current assets',                                                                                  f'2,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('I. Inventories',                                                                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Raw materials and supplies',                                                                          f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Work in progress',                                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Finished goods and merchandise',                                                                      f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Prepayments on inventories',                                                                          f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('II. Receivables and other assets',                                                                   f'2,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('1. Trade receivables',                                                                               f'2,380.00{NON_BREAKING_SPACE}€',     f'1,190.00{NON_BREAKING_SPACE}€'),
            ('2. Receivables from affiliated companies',                                                               f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Receivables from companies in which participations are held',                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Other assets',                                                                                     f'-380.00{NON_BREAKING_SPACE}€',      f'-190.00{NON_BREAKING_SPACE}€'),
            ('III. Securities',                                                                                        f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Shares in affiliated companies',                                                                      f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. other short term investments',                                                                        f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('IV. Cash on hand, Bundesbank balances, bank balances and checks',                                        f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('C. Prepaid expenses',                                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('D. Deferred tax assets',                                                                                 f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('E. Difference on the assets side from the offsetting of assets',                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('Equity and liabilities',                                                                             f'2,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('A. Equity',                                                                                          f'2,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('I. Subscribed capital',                                                                                  f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('II. Subscribed capital',                                                                                 f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('III. Revenue reserves',                                                                                  f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Legal reserve',                                                                                       f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Reserve for own shares',                                                                              f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Statutory reserves',                                                                                  f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Other retained earnings',                                                                             f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('IV. Retained earnings/accumulated losses brought forward',                                           f'1,000.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('V. Net income/loss for the year',                                                                    f'1,000.00{NON_BREAKING_SPACE}€',     f'1,000.00{NON_BREAKING_SPACE}€'),
            ('B. Liabilities',                                                                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Accrued pension and similar obligations',                                                             f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Tax accruals',                                                                                        f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Other accruals',                                                                                      f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('C. Liabilities',                                                                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('1. Loans, of which convertible',                                                                         f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('2. Liabilities to banks',                                                                                f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('3. Payments received on account of orders',                                                              f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('4. Trade payable',                                                                                       f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('5. Liabilities on bills accepted and drawn',                                                             f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('6. Payables to affiliated companies',                                                                    f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('7. Payables to companies in which participations are held',                                              f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('8. Other liabilities, of which taxes, of which relating to social security and similar obligations',     f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('D. Deferred income',                                                                                     f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€'),
            ('E. Deferred tax liabilities',                                                                            f'0.00{NON_BREAKING_SPACE}€',         f'0.00{NON_BREAKING_SPACE}€')
        ]

        self.assertLinesValues(
            self.report._get_lines(options),
            # name, 2025, 2024
            [0, 1, 2],
            expected_lines,
            options
        )

        equity_unaffected_account = self.env['account.account'].search([('account_type', '=', 'equity_unaffected')], limit=1)
        equity_account = self.env['account.account'].search([('account_type', '=', 'equity')], limit=1)
        closing_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2024-12-31',
            'line_ids': [
                Command.create({
                    'account_id': equity_unaffected_account.id,
                    'debit': 1000,
                }),
                Command.create({
                    'account_id': equity_account.id,
                    'credit': 1000,
                })
            ]
        })
        closing_entry.action_post()

        expected_lines[39] = ('I. Subscribed capital', f'1,000.00{NON_BREAKING_SPACE}€', f'1,000.00{NON_BREAKING_SPACE}€')
        expected_lines[46] = ('IV. Retained earnings/accumulated losses brought forward', f'0.00{NON_BREAKING_SPACE}€', f'0.00{NON_BREAKING_SPACE}€')
        expected_lines[47] = ('V. Net income/loss for the year', f'1,000.00{NON_BREAKING_SPACE}€', f'0.00{NON_BREAKING_SPACE}€')

        self.assertLinesValues(
            self.report._get_lines(options),
            # name, 2025, 2024
            [0, 1, 2],
            expected_lines,
            options
        )
