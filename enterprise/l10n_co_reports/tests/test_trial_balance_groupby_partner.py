from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCoReportsTrialBalanceReport(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('co')
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.trial_balance_report')
        cls.partner_a.vat = '11111'
        cls.partner_b.vat = '22222'

        cls.account_asset = cls.env['account.account'].search([
            ('company_ids', '=', cls.company_data['company'].id),
            ('code', '=', '112000')
        ], limit=1)
        cls.account_asset_name = cls.account_asset.display_name
        cls.account_receivable_name = cls.company_data['default_account_receivable'].display_name
        cls.account_revenue_name = cls.company_data['default_account_revenue'].display_name
        cls.undistributed_pl_account_name = cls.env['account.account'].search([
            ('company_ids', '=', cls.company_data['company'].id),
            ('account_type', '=', 'equity_unaffected')
        ]).display_name

    def test_trial_balance_groupby_partner_id_balance_sheet_accounts(self):
        """
            Ensure that a move line on profit account in the previous fiscal year
            is displayed in the unrealized profit and loss account
            Move:   Q4 of 2022
            Report: Q1 of 2023
        """
        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2022-12-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': 'move_line_2',
                    'account_id': self.company_data['default_account_receivable'].id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner Name    Debit        Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,           4,          5,          6,          7,          8],
            [
                (self.account_asset_name,                    '',           '',         1000.0,         0.0,        0.0,        0.0,      1000.0,       0.0),
                (self.account_asset_name,               '11111',  'partner_a',         1000.0,         0.0,        0.0,        0.0,      1000.0,       0.0),
                (self.account_receivable_name,               '',           '',            0.0,      1000.0,        0.0,        0.0,         0.0,    1000.0),
                (self.account_receivable_name,          '11111',  'partner_a',            0.0,      1000.0,        0.0,        0.0,         0.0,    1000.0),
                ('Total',                                    '',           '',         1000.0,      1000.0,        0.0,        0.0,      1000.0,    1000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_balance_sheet_accounts_multiple_partners(self):
        """
            Same logic as previous test but with several partners and a move without partner
            Move:   Q4 of 2022
            Report: Q1 of 2023
        """
        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2022-12-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'debit': 500.0,
                    'credit': 0.0,
                    'name': 'move_line_2',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'debit': 500.0,
                    'credit': 0.0,
                    'name': 'move_line_3',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_4',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 3000.0,
                    'name': 'move_line_5',
                    'account_id': self.company_data['default_account_receivable'].id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner Name    Debit       Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,          4,          5,          6,          7,          8],
            [
                (self.account_asset_name,                    '',                 '',   3000.0,        0.0,        0.0,        0.0,         3000.0,      0.0),
                (self.account_asset_name,               '11111',        'partner_a',   1000.0,        0.0,        0.0,        0.0,         1000.0,      0.0),
                (self.account_asset_name,               '22222',        'partner_b',   1000.0,        0.0,        0.0,        0.0,         1000.0,      0.0),
                (self.account_asset_name,                    '',           '(None)',   1000.0,        0.0,        0.0,        0.0,         1000.0,      0.0),
                (self.account_receivable_name,               '',                 '',      0.0,     3000.0,        0.0,        0.0,            0.0,   3000.0),
                (self.account_receivable_name,          '11111',        'partner_a',      0.0,     3000.0,        0.0,        0.0,            0.0,   3000.0),
                ('Total',                                    '',                 '',   3000.0,     3000.0,        0.0,        0.0,         3000.0,   3000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_unrealized_profit_account(self):
        """
            Ensure that a move line on profit account in the previous fiscal year
            is displayed in the unrealized profit and loss account
            Move:   Q4 of 2022
            Report: Q1 of 2023
        """
        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2022-12-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': 'move_line_2',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner name    Debit       Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,          4,          5,          6,          7,          8],
            [
                (self.account_asset_name,                   '',             '',         1000.0,       0.0,        0.0,        0.0,     1000.0,        0.0),
                (self.account_asset_name,              '11111',    'partner_a',         1000.0,       0.0,        0.0,        0.0,     1000.0,        0.0),
                (self.undistributed_pl_account_name,        '',             '',            0.0,    1000.0,        0.0,        0.0,        0.0,     1000.0),
                (self.undistributed_pl_account_name,        '',       '(None)',            0.0,    1000.0,        0.0,        0.0,        0.0,     1000.0),
                ('Total',                                   '',             '',         1000.0,    1000.0,        0.0,        0.0,     1000.0,     1000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_unrealized_profit_account_multiple_partners(self):
        """
            Same logic as previous test but with several partners and a move without partner
            Move:   Q4 of 2022
            Report: Q1 of 2023
        """
        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2022-12-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': 'move_line_1',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'debit': 0.0,
                    'credit': 500.0,
                    'name': 'move_line_2',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'debit': 0.0,
                    'credit': 500.0,
                    'name': 'move_line_3',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': 'move_line_4',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 3000.0,
                    'credit': 0.0,
                    'name': 'move_line_5',
                    'account_id': self.account_asset.id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [  Initial Balance ]     [     Balance    ]      [   End Balance     ]
            #    Name                                       Partner VAT     Partner name    Debit         Credit      Debit       Credit      Debit         Credit
            [   0,                                          1,              2,              3,            4,          5,          6,          7,            8],
            [
                (self.account_asset_name,                   '',             '',             3000.0,      0.0,        0.0,        0.0,         3000.0,      0.0),
                (self.account_asset_name,               '11111',   'partner_a',             3000.0,      0.0,        0.0,        0.0,         3000.0,      0.0),
                (self.undistributed_pl_account_name,        '',             '',                0.0,   3000.0,        0.0,        0.0,            0.0,   3000.0),
                (self.undistributed_pl_account_name,        '',       '(None)',                0.0,   3000.0,        0.0,        0.0,            0.0,   3000.0),
                ('Total',                                   '',             '',             3000.0,   3000.0,        0.0,        0.0,         3000.0,   3000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_unrealized_profit_account_with_move(self):
        """
            Ensure that a move line on profit account in the previous fiscal year
            is added to a move on the unaffected earning account (both for the initial period)
            Move:   Q4 of 2022
            Report: Q1 of 2023
        """

        unaffected_earnings_account = self.env['account.account'].search([
            ('account_type', '=', 'equity_unaffected'),
            ('company_ids', '=', self.company_data['company']['id'])
        ])

        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': '2022-12-01',
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_2',
                    'account_id': unaffected_earnings_account.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 2000.0,
                    'name': 'move_line_3',
                    'account_id': self.account_asset.id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner name    Debit       Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,          4,          5,          6,          7,          8],
            [
                (self.account_asset_name,                   '',            '',            0.0,         2000.0,      0.0,        0.0,        0.0,    2000.0),
                (self.account_asset_name,              '11111',   'partner_a',            0.0,         2000.0,      0.0,        0.0,        0.0,    2000.0),
                (self.undistributed_pl_account_name,        '',             '',        2000.0,            0.0,      0.0,        0.0,     2000.0,       0.0),
                (self.undistributed_pl_account_name,        '',       '(None)',        2000.0,            0.0,      0.0,        0.0,     2000.0,       0.0),
                ('Total',                                   '',             '',        2000.0,         2000.0,      0.0,        0.0,     2000.0,    2000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_current_year_profit_account(self):
        """
            Ensure that a move line on profit account in the current fiscal year
            is displayed in its profit account even though being made in a previous period
            Move:   Q1 of 2023
            Report: Q2 of 2023
        """
        move_q1_2023 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2023-01-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'name': 'move_line_2',
                    'account_id': self.company_data['default_account_revenue'].id
                }),
            ],
        }])
        move_q1_2023.action_post()

        options = self._generate_options(
            self.report, '2023-04-01', '2023-06-30',
            default_options={'l10n_co_reports_groupby_partner_id': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner name    Debit       Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,          4,          5,          6,          7,          8],
            [
                (self.account_asset_name,                    '',              '',       1000.0,        0.0,        0.0,        0.0,      1000.0,        0.0),
                (self.account_asset_name,               '11111',     'partner_a',       1000.0,        0.0,        0.0,        0.0,      1000.0,        0.0),
                (self.account_revenue_name,                  '',              '',          0.0,     1000.0,        0.0,        0.0,         0.0,     1000.0),
                (self.account_revenue_name,             '11111',     'partner_a',          0.0,     1000.0,        0.0,        0.0,         0.0,     1000.0),
                ('Total',                                    '',              '',       1000.0,     1000.0,        0.0,        0.0,      1000.0,     1000.0),
            ],
            options,
        )

    def test_trial_balance_groupby_partner_id_account_groups(self):
        """"
            Ensure that account groups are displayed automatically and correctly with this variant of the trial balance
        """
        self.env['account.group'].create([
            {'name': 'Group_10',    'code_prefix_start': '10',      'code_prefix_end': '10'},  # must not be displayed
            {'name': 'Group_1',     'code_prefix_start': '1',       'code_prefix_end': '1'},
            {'name': 'Group_11',    'code_prefix_start': '11',      'code_prefix_end': '11'},
            {'name': 'Group_112',   'code_prefix_start': '112',     'code_prefix_end': '112'},
            {'name': 'Group_1120',  'code_prefix_start': '1120',    'code_prefix_end': '1120'},
            {'name': 'Group_13',    'code_prefix_start': '13',      'code_prefix_end': '13'},
        ])

        move_q4_2022 = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2022-12-01'),
            'line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_1',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_b.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'name': 'move_line_2',
                    'account_id': self.account_asset.id
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'debit': 0.0,
                    'credit': 2000.0,
                    'name': 'move_line_3',
                    'account_id': self.company_data['default_account_receivable'].id
                }),
            ],
        }])
        move_q4_2022.action_post()

        options = self._generate_options(
            self.report, '2023-01-01', '2023-03-31',
            default_options={'l10n_co_reports_groupby_partner_id': True, 'hierarchy': True, 'unfold_all': True}
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #                                                                               [ Initial Balance ]     [     Balance    ]      [   End Balance   ]
            #    Name                                       Partner VAT     Partner name    Debit       Credit      Debit       Credit      Debit       Credit
            [   0,                                          1,              2,              3,          4,          5,          6,          7,          8],
            [
                ('1 Group_1',                               '',             '',           2000.0,     2000.0,      0.0,        0.0,       2000.0,     2000.0),
                ('11 Group_11',                             '',             '',           2000.0,        0.0,      0.0,        0.0,       2000.0,        0.0),
                ('112 Group_112',                           '',             '',           2000.0,        0.0,      0.0,        0.0,       2000.0,        0.0),
                ('1120 Group_1120',                         '',             '',           2000.0,        0.0,      0.0,        0.0,       2000.0,        0.0),
                (self.account_asset_name,                   '',             '',           2000.0,        0.0,      0.0,        0.0,       2000.0,        0.0),
                (self.account_asset_name,              '11111',    'partner_a',           1000.0,        0.0,      0.0,        0.0,       1000.0,        0.0),
                (self.account_asset_name,              '22222',    'partner_b',           1000.0,        0.0,      0.0,        0.0,       1000.0,        0.0),
                ('13 Group_13',                             '',             '',              0.0,     2000.0,      0.0,        0.0,          0.0,     2000.0),
                (self.account_receivable_name,              '',             '',              0.0,     2000.0,      0.0,        0.0,          0.0,     2000.0),
                (self.account_receivable_name,         '11111',    'partner_a',              0.0,     2000.0,      0.0,        0.0,          0.0,     2000.0),
                ('Total',                                   '',             '',           2000.0,     2000.0,      0.0,        0.0,       2000.0,     2000.0),
            ],
            options,
        )
