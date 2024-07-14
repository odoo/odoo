# -*- coding: utf-8 -*-
# pylint: disable=C0326

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import Command
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nMXTrialBalanceMonth13(TestAccountReportsCommon):
    """ Testing the MX Trial Balance when there are Month 13 closing entries. """
    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.mx')

        # Create:
        # - an invoice dated 2021-12-01,
        # - a Month 13 closing entry dated 2021-12-31,
        # - an invoice dated 2022-12-06,
        # - an invoice dated 2022-12-31,
        # - a Month 13 closing entry dated 2022-12-31, and
        # - an invoice dated 2023-01-01.
        inv_2021 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 1000.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 1000.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2021-12-01',
        })
        inv_2021.action_post()

        account_current_year_earnings = cls.env['account.account'].search([('code', '=', '305.01.01'), ('company_id', '=', cls.company_data['company'].id)])
        closing_2021 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 800.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': account_current_year_earnings.id,
                    'debit': 0.0,
                    'credit': 800.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2021-12-31',
            'l10n_mx_closing_move': True,
        })
        closing_2021.action_post()

        inv_dec_6 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 200.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 200.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2022-12-06',
        })
        inv_dec_6.action_post()

        inv_dec_31 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2022-12-31',
        })
        inv_dec_31.action_post()

        closing_2022 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 250.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': account_current_year_earnings.id,
                    'debit': 0.0,
                    'credit': 250.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2022-12-31',
            'l10n_mx_closing_move': True,
        })
        closing_2022.action_post()

        inv_jan_1 = cls.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 20.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 20.0,
                }),
            ],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': '2023-01-01',
        })
        inv_jan_1.action_post()

        cls.report = cls.env.ref('account_reports.trial_balance_report')

    def test_non_month_13(self):
        """ Test the Trial Balance report in the case where the 'Month 13' filter is not set.
            We generate the TB for two periods: from 2022-12-01 to 2022-12-31, and from 2022-12-01 to 2023-01-01.

            For 2022-12-01 to 2022-12-31:
            - the closing entry for 2021 should appear in the initial balance
            - the closing entry for 2022 should not appear

            For 2022-12-01 to 2023-01-01:
            - the closing entry for 2021 should appear in the initial balance
            - the closing entry for 2022 should appear in the current period"""

        # Generate the Trial Balance for Dec 2022.
        options = self._generate_options(self.report, '2022-12-01', '2022-12-31', {'hierarchy': False, 'unfold_all': True})
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,       2,       3,       4,        5,         6],
            [
                ('105.01.01 Domestic customers',                              1000.0,     0.0,  300.0,    0.0,     1300.0,       0.0),
                ('305.01.01 Profit for the year',                                0.0,   800.0,    0.0,     0.0,       0.0,     800.0),
                ('401.01.01 Sales and/or services taxed at the general rate',    0.0,     0.0,    0.0,   300.0,       0.0,     300.0),
                ('999999 Undistributed Profits/Losses',                          0.0,   200.0,    0.0,     0.0,       0.0,     200.0),
                ('Total',                                                     1000.0,  1000.0,  300.0,   300.0,    1300.0,    1300.0),
            ],
            options,
        )

        # Generate the Trial Balance between 2022-12-01 and 2023-01-01.
        options = self._generate_options(self.report, '2022-12-01', '2023-01-01', {'hierarchy': False, 'unfold_all': True})
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,         2,         3,       4,        5,         6],
            [
                ('105.01.01 Domestic customers',                              1000.0,       0.0,    320.0,     0.0,    1320.0,       0.0),
                ('305.01.01 Profit for the year',                                0.0,     800.0,      0.0,   250.0,       0.0,    1050.0),
                ('401.01.01 Sales and/or services taxed at the general rate',    0.0,       0.0,    250.0,   320.0,       0.0,      70.0),
                ('999999 Undistributed Profits/Losses',                          0.0,     200.0,      0.0,     0.0,       0.0,     200.0),
                ('Total',                                                     1000.0,    1000.0,    570.0,   570.0,    1320.0,    1320.0),
            ],
            options,
        )

    def test_month_13(self):
        """ Test the Trial Balance report in the case where the 'Month 13' filter is set.
            We generate the TB for period 2022-12-01 to 2022-12-31.
            We expect:
            - the invoices in Dec 2022 and the closing entry for 2021 appear in the initial balance
            - the closing entry for 2022 appears in the current period.
        """

        # Generate the Trial Balance for Dec 2022 with the 'Month 13' filter active.
        options = self._generate_options(self.report, '2022-12-01', '2022-12-31', {'hierarchy': False, 'unfold_all': True, 'l10n_mx_month_13': True})
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,         2,         3,       4,        5,         6],
            [
                ('105.01.01 Domestic customers',                              1300.0,       0.0,      0.0,     0.0,    1300.0,       0.0),
                ('305.01.01 Profit for the year',                                0.0,     800.0,      0.0,   250.0,       0.0,    1050.0),
                ('401.01.01 Sales and/or services taxed at the general rate',    0.0,     300.0,    250.0,     0.0,       0.0,      50.0),
                ('999999 Undistributed Profits/Losses',                          0.0,     200.0,      0.0,     0.0,       0.0,     200.0),
                ('Total',                                                     1300.0,    1300.0,    250.0,   250.0,    1300.0,    1300.0),
            ],
            options,
        )

    def test_comparison(self):
        """ Test comparisons when there are Month 13 closing entries.

            - With the Month 13 filter active, comparisons are disabled (so we don't test them)
            - With the Month 13 filter inactive, the closing entry should appear as part of the month of December,
              unless December is the last period in the comparison - in that case the closing entry shouldn't appear.
        """

        # Generate the Trial Balance for Dec 2022, comparing with Nov 2022, and without the 'Month 13' filter.
        options = self._generate_options(self.report, '2022-12-01', '2022-12-31', {
            'hierarchy': False,
            'unfold_all': True,
            'comparison': {
                'filter': 'previous_period',
                'number_period': 1,
            },
        })
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,       2,      3,    4,    5,      6,      7,       8],
            [
                ('105.01.01 Domestic customers',                              1000.0,     0.0, 0.0,  0.0,  300.0,    0.0,  1300.0,   0.0),
                ('305.01.01 Profit for the year',                                0.0,   800.0, 0.0,  0.0,    0.0,    0.0,     0.0,   800.0),
                ('401.01.01 Sales and/or services taxed at the general rate',    0.0,     0.0, 0.0,  0.0,    0.0,  300.0,     0.0,   300.0),
                ('999999 Undistributed Profits/Losses',                          0.0,   200.0, 0.0,  0.0,    0.0,    0.0,     0.0,   200.0),
                ('Total',                                                     1000.0,  1000.0, 0.0,  0.0,  300.0,  300.0,  1300.0,  1300.0),
            ],
            options,
        )

        # Generate the Trial Balance for Jan 2023, comparing with Dec 2022, and without the 'Month 13' filter.
        options = self._generate_options(self.report, '2023-01-01', '2023-01-31', {
            'hierarchy': False,
            'unfold_all': True,
            'comparison': {
                'filter': 'previous_period',
                'number_period': 1,
            },
        })
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                                            1,         2,         3,       4,      5,     6,     7,       8],
            [
                ('105.01.01 Domestic customers',                              1000.0,       0.0,    300.0,     0.0,  20.0,   0.0,  1320.0,     0.0),
                ('305.01.01 Profit for the year',                                0.0,     800.0,      0.0,   250.0,   0.0,   0.0,     0.0,  1050.0),
                ('401.01.01 Sales and/or services taxed at the general rate',    0.0,       0.0,    250.0,   300.0,   0.0,  20.0,     0.0,    70.0),
                ('999999 Undistributed Profits/Losses',                          0.0,     200.0,      0.0,     0.0,   0.0,   0.0,     0.0,   200.0),
                ('Total',                                                     1000.0,    1000.0,    550.0,   550.0,  20.0,  20.0,  1320.0,  1320.0),
            ],
            options,
        )
