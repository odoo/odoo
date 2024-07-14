from .common import TestAccountReportsCommon

from odoo import fields, Command
from odoo.tests import tagged
from odoo.tools import frozendict

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestReportEngines(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].totals_below_sections = False

        cls.garbage_account = cls.env['account.account'].create({
            'code': "turlututu",
            'name': "turlututu",
            'account_type': "asset_current",
        })

        cls.fake_country = cls.env['res.country'].create({
            'name': "L'Île de la Mouche",
            'code': 'YY',
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _prepare_test_account_move_line(self, balance, account_code=None, tax_tags=None, date='2020-01-01', **kwargs):
        if tax_tags:
            tags = self.env['account.account.tag'].search([
                ('applicability', '=', 'taxes'),
                ('country_id', '=', self.fake_country.id),
                ('name', 'in', tax_tags),
            ])
        else:
            tags = self.env['account.account.tag']

        return {
            'account_move_line_values': {
                'name': "turlututu",
                'account_id': self.garbage_account.id,
                **kwargs,
                'debit': balance if balance > 0.0 else 0.0,
                'credit': -balance if balance < 0.0 else 0.0,
                'tax_tag_ids': [Command.set(tags.ids)],
            },
            'account_move_values': {'date': date},
            'account_code': account_code,
        }

    def _create_test_account_moves(self, test_account_move_line_values_list):
        # Create the missing account on-the-fly.
        accounts_to_create_by_code = set()
        for test_account_move_line_values in test_account_move_line_values_list:
            if test_account_move_line_values.get('account_code'):
                accounts_to_create_by_code.add(test_account_move_line_values['account_code'])

        if accounts_to_create_by_code:
            accounts = self.env['account.account'].create([
                {
                    'code': account_code,
                    'name': account_code,
                    'account_type': "asset_current",
                }
                for account_code in accounts_to_create_by_code
            ])
            account_by_code = {x.code: x for x in accounts}

            for test_account_move_line_values in test_account_move_line_values_list:
                account = account_by_code.get(test_account_move_line_values.get('account_code'))
                if account:
                    test_account_move_line_values['account_move_line_values']['account_id'] = account.id

        # Create the journal entries.
        to_create = {}
        for test_account_move_line_values in test_account_move_line_values_list:
            account_move_key = frozendict(test_account_move_line_values['account_move_values'])
            account_move_line_values = test_account_move_line_values['account_move_line_values']
            account_move_to_create = to_create.setdefault(account_move_key, {
                'account_move_values': {'line_ids': []},
                'balance': 0.0,
            })
            account_move_to_create['account_move_values']['line_ids'].append(Command.create(account_move_line_values))
            account_move_to_create['balance'] += account_move_line_values['debit'] - account_move_line_values['credit']

        account_move_create_list = []
        for account_move_dict, account_move_to_create in to_create.items():
            open_balance = account_move_to_create['balance']
            account_move_values = account_move_to_create['account_move_values']
            if not self.env.company.currency_id.is_zero(open_balance):
                account_move_values['line_ids'].append(Command.create({
                    'name': 'open balance',
                    'account_id': self.garbage_account.id,
                    'debit': -open_balance if open_balance < 0.0 else 0.0,
                    'credit': open_balance if open_balance > 0.0 else 0.0,
                }))
            account_move_create_list.append({
                **account_move_dict,
                **account_move_values,
            })

        moves = self.env['account.move'].create(account_move_create_list)
        moves.action_post()
        return moves

    def _prepare_test_external_values(self, value, date, figure_type=False):
        field_name = 'text_value' if figure_type == 'string' else 'value'
        return {
            'name': date,
            field_name: value,
            'date': date,
        }

    def _prepare_test_expression(self, formula, label='balance', **kwargs):
        return {
            'expression_values': {
                'label': label,
                'formula': formula,
                **kwargs,
            },
        }

    def _prepare_test_expression_tax_tags(self, formula, **kwargs):
        return self._prepare_test_expression(engine='tax_tags', formula=formula, **kwargs)

    def _prepare_test_expression_domain(self, formula, subformula, **kwargs):
        return self._prepare_test_expression(engine='domain', formula=formula, subformula=subformula, **kwargs)

    def _prepare_test_expression_account_codes(self, formula, **kwargs):
        return self._prepare_test_expression(engine='account_codes', formula=formula, **kwargs)

    def _prepare_test_expression_external(self, formula, external_value_generators, **kwargs):
        return {
            **self._prepare_test_expression(engine='external', formula=formula, **kwargs),
            'external_value_generators': external_value_generators,
        }

    def _prepare_test_expression_custom(self, formula, **kwargs):
        return self._prepare_test_expression(engine='custom', formula=formula, **kwargs)

    def _prepare_test_expression_aggregation(self, formula, subformula=None, column='balance', date_scope=None):
        expression_values = {
            'label': column,
            'engine': 'aggregation',
            'formula': formula,
            'subformula': subformula,
        }

        if date_scope:
            expression_values['date_scope'] = date_scope

        return {
            'expression_values': expression_values,
        }

    def _prepare_test_report_line(self, *expression_generators, **kwargs):
        return {
            'report_line_values': {
                **kwargs,
                'expression_ids': [
                    Command.create({
                        'date_scope': 'strict_range',
                        **expression_values['expression_values'],
                    })
                    for expression_values in expression_generators
                ],
            },
            'expression_generators': expression_generators,
        }

    def _create_report(self, test_report_line_values_list, columns=None, **kwargs):
        if not columns:
            columns = ['balance']

        # Create a new report
        report = self.env['account.report'].create({
            'name': "_run_report",
            'filter_date_range': True,
            'filter_unfold_all': True,
            **kwargs,
            'column_ids': [
                Command.create({
                    'name': column,
                    'expression_label': column,
                    'sequence': i,
                })
                for i, column in enumerate(columns)
            ],
            'line_ids': [
                Command.create({
                    'name': f"test_line_{i}",
                    **test_report_line_values['report_line_values'],
                    'sequence': i,
                })
                for i, test_report_line_values in enumerate(test_report_line_values_list, start=1)
            ],
        })

        # Create the external values
        external_values_create_list = []
        for report_line, test_report_line_values in zip(report.line_ids, test_report_line_values_list):
            for expression, expression_values in zip(report_line.expression_ids, test_report_line_values['expression_generators']):
                for external_values in expression_values.get('external_value_generators', []):
                    external_values_create_list.append({
                        **external_values,
                        'target_report_expression_id': expression.id,
                    })
        self.env['account.report.external.value'].create(external_values_create_list)

        return report

    # -------------------------------------------------------------------------
    # TESTS
    # -------------------------------------------------------------------------

    def test_engine_tax_tags(self):
        self.env.company.account_fiscal_country_id = self.fake_country

        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('11'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('222T'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('3333'),
            groupby='account_id',
        )
        report = self._create_report(
            [test_line_1, test_line_2, test_line_3],
            country_id=self.fake_country.id,
        )

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001', tax_tags=['+11', '-222T']),
            self._prepare_test_account_move_line(1000.0, account_code='101001', tax_tags=['+11', '-222T']),
            self._prepare_test_account_move_line(3600.0, account_code='101001', tax_tags=['+222T']),
            self._prepare_test_account_move_line(-600.0, account_code='101001', tax_tags=['+222T', '-3333']),
            self._prepare_test_account_move_line(-900.0, account_code='101002', tax_tags=['-11']),
            self._prepare_test_account_move_line(1500.0, account_code='101002', tax_tags=['+11']),
        ])

        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',        5400.0),
                ('101001 101001',      3000.0),
                ('101002 101002',      2400.0),
                ('test_line_2',           0.0),
                ('101001 101001',         0.0),
                ('test_line_3',         600.0),
                ('101001 101001',       600.0),
            ],
            options,
        )

        # Check redirection.
        expected_redirection_values_list = [
            move.line_ids[:2] + move.line_ids[4:6],
            move.line_ids[:4],
            move.line_ids[3],
        ]
        for report_line, expected_amls in zip(report.line_ids, expected_redirection_values_list):
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_domain(self):
        domain = [('account_id.code', '=like', '1%'), ('balance', '<', 0.0)]

        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum_if_neg'),
            groupby='account_id',
        )
        test_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum_if_neg'),
            groupby='account_id',
        )
        test_line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'sum_if_pos'),
            groupby='account_id',
        )
        test_line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, '-sum_if_pos'),
            groupby='account_id',
        )
        test_line_7 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(domain, 'count_rows'),
            groupby='account_id',
        )
        report = self._create_report([test_line_1, test_line_2, test_line_3, test_line_4, test_line_5, test_line_6, test_line_7])

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(-600.0, account_code='101003'),
            self._prepare_test_account_move_line(-900.0, account_code='101004'),
        ])

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',       -1800.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('101004 101004',      -900.0),
                ('test_line_2',        1800.0),
                ('101002 101002',       300.0),
                ('101003 101003',       600.0),
                ('101004 101004',       900.0),
                ('test_line_3',       -1800.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('101004 101004',      -900.0),
                ('test_line_4',        1800.0),
                ('101002 101002',       300.0),
                ('101003 101003',       600.0),
                ('101004 101004',       900.0),
                ('test_line_5',           0.0),
                ('test_line_6',           0.0),
                ('test_line_7',             3),
                ('101002 101002',           1),
                ('101003 101003',           1),
                ('101004 101004',           1),
            ],
            options,
        )

        # Check redirection.
        expected_amls = move.line_ids.search(domain)
        for report_line in report.line_ids:
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_account_codes(self):
        # Create test account tags
        account_tags = self.env['account.account.tag']._load_records([
            {
                'xml_id': 'account_reports.account_codes_engine_test_tag1',
                'noupdate': True,
                'values': {
                    'name': "account_codes test tag 1",
                    'applicability': 'accounts',
                },
            },

            {
                'xml_id': 'account_reports.account_codes_engine_test_tag2',
                'noupdate': True,
                'values': {
                    'name': "account_codes test tag 2",
                    'applicability': 'accounts',
                },
            },
        ])

        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1C'),
            groupby='account_id',
        )
        test_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1D'),
            groupby='account_id',
        )
        test_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101003)'),
            groupby='account_id',
        )
        test_line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101003)C'),
            groupby='account_id',
        )
        test_line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'-101\(101002,101003)'),
            groupby='account_id',
        )
        test_line_7 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.'),
            groupby='account_id',
        )
        test_line_8 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.20'),
            groupby='account_id',
        )
        test_line_9 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10.20 - 101 + 101002'),
            groupby='account_id',
        )
        test_line_10 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'10.20 - 101\(101002)'),
            groupby='account_id',
        )
        test_line_11 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'345D\()D'),
            groupby='account_id',
        )
        test_line_12 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'345D\()C'),
            groupby='account_id',
        )
        test_line_13 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(rf'tag(account_reports.account_codes_engine_test_tag1) + tag({account_tags[1].id})'),
            groupby='account_id',
        )
        test_line_14 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'tag(account_reports.account_codes_engine_test_tag1)D'),
            groupby='account_id',
        )
        test_line_15 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(r'tag(account_reports.account_codes_engine_test_tag1)C'),
            groupby='account_id',
        )
        test_line_16 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes(rf'tag(account_reports.account_codes_engine_test_tag1)\(101)D + 101003 + tag({account_tags[1].id})\(101)C'),
            groupby='account_id',
        )

        report = self._create_report([
            test_line_1, test_line_2, test_line_3, test_line_4, test_line_5, test_line_6, test_line_7, test_line_8,
            test_line_9, test_line_10, test_line_11, test_line_12, test_line_13, test_line_14, test_line_15, test_line_16
        ])

        # Create the journal entries.
        move = self._create_test_account_moves([
            self._prepare_test_account_move_line(1000.0, account_code='100001'),
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(-600.0, account_code='101003'),
            self._prepare_test_account_move_line(10000.0, account_code='10.20.0'),
            self._prepare_test_account_move_line(10.0, account_code='345D'),
        ])

        # Setup tags on accounts
        self.env['account.account'].search([('code', 'in', ('100001', '101001'))]).tag_ids = account_tags[0]
        self.env['account.account'].search([('code', 'in', ('10.20.0', '101002'))]).tag_ids = account_tags[1]

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01', default_options={'unfold_all': True})
        report_lines = report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',       12100.0),
                ('10.20.0 10.20.0',   10000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('test_line_2',        -900.0),
                ('101002 101002',      -300.0),
                ('101003 101003',      -600.0),
                ('test_line_3',       13000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('test_line_4',       -1700.0),
                ('101001 101001',     -2000.0),
                ('101002 101002',       300.0),
                ('test_line_5',         300.0),
                ('101002 101002',       300.0),
                ('test_line_6',       -2000.0),
                ('101001 101001',     -2000.0),
                ('test_line_7',       10000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('test_line_8',       10000.0),
                ('10.20.0 10.20.0',   10000.0),
                ('test_line_9',        8600.0),
                ('10.20.0 10.20.0',   10000.0),
                ('101001 101001',     -2000.0),
                ('101002 101002',      -300.0),
                ('101003 101003',       600.0),
                ('test_line_10',       8600.0),
                ('10.20.0 10.20.0',   10000.0),
                ('101001 101001',     -2000.0),
                ('101003 101003',       600.0),
                ('test_line_11',         10.0),
                ('345D 345D',            10.0),
                ('test_line_12',          0.0),
                ('test_line_13',      12700.0),
                ('10.20.0 10.20.0',   10000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('101002 101002',      -300.0),
                ('test_line_14',       3000.0),
                ('100001 100001',      1000.0),
                ('101001 101001',      2000.0),
                ('test_line_15',          0.0),
                ('test_line_16',        400.0),
                ('100001 100001',      1000.0),
                ('101003 101003',      -600.0),
            ],
            options,
        )

        # Check redirection.
        expected_redirection_values_list = [
            move.line_ids[:5],
            move.line_ids[:5],
            move.line_ids[:5],
            move.line_ids[1:3],
            move.line_ids[1:3],
            move.line_ids[1],
            move.line_ids[4],
            move.line_ids[4],
            move.line_ids[1:5],
            move.line_ids[1] + move.line_ids[3:5],
            move.line_ids[5],
            move.line_ids[5],
        ]
        for report_line, expected_amls in zip(report.line_ids, expected_redirection_values_list):
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(move.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_external(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_external('sum', [
                self._prepare_test_external_values(100.0, '2020-01-02'),
                self._prepare_test_external_values(200.0, '2020-01-03'),
                self._prepare_test_external_values(300.0, '2020-01-03'),
                self._prepare_test_external_values(299.999999999, '2020-01-05'),
            ])
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_external('most_recent', [
                self._prepare_test_external_values(100.0, '2020-01-02'),
                self._prepare_test_external_values(200.0, '2020-01-03'),
                self._prepare_test_external_values(300.0, '2020-01-03'),
                self._prepare_test_external_values(299.999999999, '2020-01-05'),
            ])
        )
        report = self._create_report([test_line_1, test_line_2])

        # Check the values at multiple dates.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',           0.0),
                ('test_line_2',           0.0),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-02')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',         100.0),
                ('test_line_2',         100.0),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-03', '2020-01-03')
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test_line_1',         500.0),
                ('test_line_2',         500.0),
            ],
            options,
        )

        # Check redirection.
        for report_line, report_line_dict in zip(report.line_ids, report_lines):
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertRecordValues(
                    self.env['account.report.external.value'].search(action_dict['domain']),
                    [
                        {'date': fields.Date.from_string('2020-01-03')},
                        {'date': fields.Date.from_string('2020-01-03')},
                    ],
                )

        options = self._generate_options(report, '2020-01-04', '2020-01-04')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',           0.0),
                ('test_line_2',           0.0),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-04')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          600.0),
                ('test_line_2',          500.0),
            ],
            options,
        )

        # Check redirection.
        expected_redirection_values_list = [
            [
                {'date': fields.Date.from_string('2020-01-02')},
                {'date': fields.Date.from_string('2020-01-03')},
                {'date': fields.Date.from_string('2020-01-03')},
            ],
            [
                {'date': fields.Date.from_string('2020-01-03')},
                {'date': fields.Date.from_string('2020-01-03')},
            ],
        ]
        for report_line, report_line_dict, expected_values in zip(report.line_ids, report_lines, expected_redirection_values_list):
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertRecordValues(
                    self.env['account.report.external.value'].search(action_dict['domain']),
                    expected_values,
                )

        options = self._generate_options(report, '2020-01-03', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          800.0),
                ('test_line_2',          300.0),
            ],
            options,
        )

    def test_engine_external_editable_percentage(self):
        # Create the report.
        test_rounding_4 = self._prepare_test_report_line(
            self._prepare_test_expression_external(
                'most_recent', [
                    self._prepare_test_external_values(10.1254, '2020-01-01'),
                    self._prepare_test_external_values(5, '2020-01-02'),
                ], figure_type='percentage', subformula='editable;rounding=4',
            ),
            code='TEST_PERCENTAGE'
        )
        test_rounding_2 = self._prepare_test_report_line(
            self._prepare_test_expression_external(
                'most_recent', [
                    self._prepare_test_external_values(10.12, '2020-01-01'),
                    self._prepare_test_external_values(5, '2020-01-02'),
                ], figure_type='percentage', subformula='editable;rounding=2',
            )
        )
        test_percentage_aggregate = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('10000 * TEST_PERCENTAGE.balance'),
        )
        test_float = self._prepare_test_report_line(
            self._prepare_test_expression_external(
                'most_recent', [
                    self._prepare_test_external_values(10.12, '2020-01-01'),
                    self._prepare_test_external_values(5, '2020-01-02'),
                ], figure_type='float', subformula='editable;rounding=2',
            )
        )

        report = self._create_report([test_rounding_4, test_rounding_2, test_percentage_aggregate, test_float])
        # Check the values at multiple dates.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [0,                          1],
            [
                ('test_line_1', '10.1254%'),
                ('test_line_2',   '10.12%'),
                ('test_line_3',     101254),
                ('test_line_4',    '10.12'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-02')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [0,                         1],
            [
                ('test_line_1', '5.0000%'),
                ('test_line_2',   '5.00%'),
                ('test_line_3',     50000),
                ('test_line_4',    '5.00'),
            ],
            options,
        )

    def test_engine_custom(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_custom('_custom_engine_test', subformula='sum'),
            groupby='account_id',
        )
        report = self._create_report([test_line_1])

        # Create the journal entries.
        self._create_test_account_moves([
            self._prepare_test_account_move_line(2000.0, account_code='101001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
        ])

        # Check the values.

        def _custom_engine_test(expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
            domain = [('account_id.code', '=', '101002')]
            domain_key = str(domain)
            formulas_dict = {domain_key: expressions}
            domain_result = report._compute_formula_batch_with_engine_domain(
                options, date_scope, formulas_dict, current_groupby, next_groupby,
                offset=offset, limit=limit,
            )
            return list(domain_result.values())[0]

        orig_get_custom_report_function = report._get_custom_report_function

        def get_custom_report_function(_report, function_name, prefix):
            if function_name == '_custom_engine_test':
                return _custom_engine_test
            return orig_get_custom_report_function(function_name, prefix)

        with patch.object(type(report), '_get_custom_report_function', get_custom_report_function):
            options = self._generate_options(report, '2020-01-01', '2020-01-01')
            self.assertLinesValues(
                # pylint: disable=bad-whitespace
                report._get_lines(options),
                [   0,                          1],
                [
                    ('test_line_1',        -300.0),
                    ('101002 101002',      -300.0),
                ],
                options,
            )

    def test_engine_aggregation(self):
        self.env.company.account_fiscal_country_id = self.fake_country
        self.currency_data['currency'].name = 'GOL'

        # Test division by zero.
        test1 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('11', label='tax_tags'),
            self._prepare_test_expression_domain([('account_id.code', '=', '101002')], 'sum', label='domain'),
            self._prepare_test_expression_external('sum', [self._prepare_test_external_values(100.0, '2020-01-01')], label='external'),
            self._prepare_test_expression_aggregation('test1.tax_tags + test1.domain', column='aggregation'),
            self._prepare_test_expression_aggregation('test1.tax_tags / 0'),
            self._prepare_test_expression_external('sum', [self._prepare_test_external_values(100.47, '2020-01-01')], label='external_decimal'),
            name='test1', code='test1',
        )

        # Test if_(above|below|between) operators.
        test2_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(0))'),
            name='test2_1', code='test2_1',
        )
        test2_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(1999.9999999))'),
            name='test2_2', code='test2_2',
        )
        test2_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(USD(2500.0))'),
            name='test2_3', code='test2_3',
        )
        test2_4 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags', subformula='if_above(GOL(3600.0))'),
            name='test2_4', code='test2_4',
        )
        test3_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(0))'),
            name='test3_1', code='test3_1',
        )
        test3_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(-300.00001))'),
            name='test3_2', code='test3_2',
        )
        test3_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain', subformula='if_below(USD(- 350))'),
            name='test3_3', code='test3_3',
        )
        test4_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags + test1.domain', subformula='if_between(USD(0), USD(2000))'),
            name='test4_1', code='test4_1',
        )
        test4_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags + test1.domain', subformula='if_between(GOL(0), GOL(3000))'),
            name='test4_2', code='test4_2',
        )

        # Test line code recognition.
        test5 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('101003', label='account_codes'),
            self._prepare_test_expression_aggregation('test1.tax_tags + 9999.account_codes'),
            name='9999', code='9999',
        )

        # Test mathematical operators.
        test6 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation(
                '(test1.tax_tags + (2 * test1.domain) + 100.0) / (9999.account_codes)'
            ),
            name='test6', code='test6',
        )

        # Test other date scope
        test7 = self._prepare_test_report_line(
            self._prepare_test_expression_domain(
                [('account_id.code', '=', '101002')],
                'sum',
                label='domain',
                date_scope='to_beginning_of_period',
            ),
            self._prepare_test_expression_aggregation('test7.domain'),
            name='test7', code='test7',
        )

        # Test exponential notation
        test9 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation(
                '(test1.tax_tags + (2 * test1.domain) + 100.0 + 1.752e-17) / (9999.account_codes)'
            ),
            name='test9', code='test9',
        )

        # Test 'round' subformula
        test10_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external_decimal', subformula='round(0)'),
            name='test10_1', code='test10_1',
        )
        test10_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external_decimal', subformula='round(1)'),
            name='test10_2', code='test10_2',
        )
        test10_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external_decimal', subformula='round(3)'),
            name='test10_3', code='test10_3',
        )

        # Test if_other_expr_above / if_other_expr_below
        test11_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_above(test1.tax_tags, USD(3000.0))'),
            name='test11_1', code='test11_1',
        )
        test11_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_below(test1.tax_tags, USD(3000.0))'),
            name='test11_2', code='test11_2',
        )
        test11_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_above(test1.tax_tags, USD(1000.0))'),
            name='test11_3', code='test11_3',
        )
        test11_4 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_below(test1.tax_tags, USD(1000.0))'),
            name='test11_4', code='test11_4',
        )
        # Test with an aggregation in the condition
        test11_5 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_above(test1.aggregation, USD(1000.0))'),
            name='test11_5', code='test11_5',
        )
        test11_6 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.external', subformula='if_other_expr_below(test1.aggregation, USD(1000.0))'),
            name='test11_6', code='test11_6',
        )

        # Test sum_children formula (parent_id relationship is populated below)
        test_12_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('sum_children'),
            name='test12_1', code='test12_1',
        )
        test_12_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.tax_tags'),
            name='test12_2', code='test12_2',
        )
        test_12_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test1.domain'),
            name='test12_3', code='test12_3',
        )
        test_12_4 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('sum_children'),
            name='test12_4', code='test12_4',
        )
        test_12_5 = self._prepare_test_report_line(
            self._prepare_test_expression_domain([('account_id.code', '=', '101003')], 'sum'),
            name='test12_5', # No code on purpose to check a different case of sum_children
        )

        report = self._create_report(
            [
                test1, test2_1, test2_2, test2_3, test2_4, test3_1, test3_2, test3_3, test4_1, test4_2,
                test5, test6, test7, test9, test10_1, test10_2, test10_3, test11_1, test11_2, test11_3, test11_4,
                test11_5, test11_6, test_12_1, test_12_2, test_12_3, test_12_4, test_12_5,
            ],
            country_id=self.fake_country.id,
        )

        # Set parent link properly for sum_children test, now that all lines are created:
        line_12_1 = self.env['account.report.line'].search([('code', '=', 'test12_1')])
        self.env['account.report.line'].search([('code', 'in', ('test12_2', 'test12_3', 'test12_4'))]).parent_id = line_12_1
        line_12_4 = self.env['account.report.line'].search([('code', '=', 'test12_4')])
        self.env['account.report.line'].search([('name', '=', 'test12_5')]).parent_id = line_12_4

        # Create the journal entries.
        moves = self._create_test_account_moves([
            self._prepare_test_account_move_line(100000.0, account_code='101002', date='2019-01-01'),
            self._prepare_test_account_move_line(2000.0, account_code='101001', tax_tags=['+11']),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(1500.0, account_code='101003'),
        ])

        # Check the values.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        report_lines = report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_lines,
            [   0,                          1],
            [
                ('test1',                 0.0),
                ('test2_1',            2000.0),
                ('test2_2',               0.0),
                ('test2_3',               0.0),
                ('test2_4',            2000.0),
                ('test3_1',            -300.0),
                ('test3_2',               0.0),
                ('test3_3',               0.0),
                ('test4_1',            1700.0),
                ('test4_2',               0.0),
                ('9999',               3500.0),
                ('test6',                 1.0),
                ('test7',            100000.0),
                ('test9',                 1.0),
                ('test10_1',            100.0),
                ('test10_2',            100.5),
                ('test10_3',            100.47),
                ('test11_1',              0.0),
                ('test11_2',            100.0),
                ('test11_3',            100.0),
                ('test11_4',              0.0),
                ('test11_5',            100.0),
                ('test11_6',              0.0),
                ('test12_1',           3200.0),
                ('test12_2',           2000.0),
                ('test12_3',           -300.0),
                ('test12_4',           1500.0),
                ('test12_5',           1500.0),
            ],
            options,
        )

        # Check redirection.
        expected_amls_to_test = [
            ('9999', moves[1].line_ids[0] + moves[1].line_ids[2]),
            ('test7', moves[0].line_ids[0]),
            ('test12_1', moves[1].line_ids[:3]),
        ]
        for report_line_name, expected_amls in expected_amls_to_test:
            report_line = report.line_ids.filtered(lambda x: x.name == report_line_name)
            report_line_dict = [x for x in report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = report.action_audit_cell(options, self._get_audit_params_from_report_line(options, report_line, report_line_dict))
                self.assertEqual(moves.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_aggregation_cross_report(self):
        moves = self._create_test_account_moves([
            self._prepare_test_account_move_line(1.0, account_code='100000', date='2020-01-01'),
            self._prepare_test_account_move_line(2.0, account_code='100000', date='2021-01-01'),
            self._prepare_test_account_move_line(3.0, account_code='200000', date='2020-01-01'),
            self._prepare_test_account_move_line(4.0, account_code='200000', date='2021-01-01'),
            self._prepare_test_account_move_line(5.0, account_code='300000', date='2021-01-01'),
        ])

        # Other report
        other_report_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1'),
            name='other_report_line_1', code='other_report_line_1',
        )

        other_report_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('2'),
            name='other_report_line_2', code='other_report_line_2',
        )

        other_report_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('other_report_line_1.balance + other_report_line_2.balance'),
            name='other_report_line_3', code='other_report_line_3',
        )

        other_report_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('3'),
            name='other_report_line_4', code='other_report_line_4',
        )

        other_report = self._create_report([other_report_line_1, other_report_line_2, other_report_line_3, other_report_line_4])
        other_report_options = self._generate_options(other_report, '2021-01-01', '2021-01-01')

        # Main report
        main_report_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('other_report_line_2.balance', subformula='cross_report', date_scope='strict_range'),
            name='main_report_line_1', code='main_report_line_1',
        )

        main_report_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('other_report_line_2.balance', subformula='cross_report', date_scope='from_beginning'),
            name='main_report_line_2', code='main_report_line_2',
        )

        main_report_line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('other_report_line_3.balance', subformula='cross_report', date_scope='strict_range'),
            name='main_report_line_3', code='main_report_line_3',
        )

        main_report_line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('other_report_line_3.balance', subformula='cross_report', date_scope='from_beginning'),
            name='main_report_line_4', code='main_report_line_4',
        )

        main_report_line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation(
                'main_report_line_1.balance + main_report_line_2.balance + main_report_line_3.balance + main_report_line_4.balance',
            ),
            name='main_report_line_5', code='main_report_line_5',
        )

        main_report_line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation(
                'main_report_line_1.balance + main_report_line_2.balance + main_report_line_3.balance + main_report_line_4.balance',
            ),
            name='main_report_line_6', code='main_report_line_6',
        )

        main_report = self._create_report([main_report_line_1, main_report_line_2, main_report_line_3, main_report_line_4, main_report_line_5, main_report_line_6])
        main_report_options = self._generate_options(main_report, '2021-01-01', '2021-01-01')

        # First check other_report
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            other_report._get_lines(other_report_options),
            [   0,                                      1],
            [
                ('other_report_line_1',               2.0),
                ('other_report_line_2',               4.0),
                ('other_report_line_3',               6.0),
                ('other_report_line_4',               5.0),
            ],
            other_report_options,
        )

        # Check main_report
        main_report_options = self._generate_options(main_report, '2021-01-01', '2021-01-01')
        main_report_lines = main_report._get_lines(main_report_options)
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            main_report_lines,
            [   0,                                      1],
            [
                ('main_report_line_1',                4.0),
                ('main_report_line_2',                7.0),
                ('main_report_line_3',                6.0),
                ('main_report_line_4',               10.0),
                ('main_report_line_5',               27.0),
                ('main_report_line_6',               27.0),
            ],
            main_report_options,
        )

        # Check redirection.
        expected_amls_to_test = [
            ('main_report_line_1', moves[1].line_ids[1]),
            ('main_report_line_2', moves[1].line_ids[1] + moves[0].line_ids[1]),
        ]

        for report_line_name, expected_amls in expected_amls_to_test:
            report_line = main_report.line_ids.filtered(lambda x: x.name == report_line_name)
            report_line_dict = [x for x in main_report_lines if x['name'] == report_line.name][0]
            with self.subTest(report_line=report_line.name):
                action_dict = main_report.action_audit_cell(main_report_options, self._get_audit_params_from_report_line(main_report_options, report_line, report_line_dict))
                self.assertEqual(moves.line_ids.filtered_domain(action_dict['domain']), expected_amls)

    def test_engine_aggregation_expansion(self):
        report = self._create_report([
            self._prepare_test_report_line(
                self._prepare_test_expression_tax_tags('42'),
                code='TAG_1',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_tax_tags('221292'),
                code='TAG_2',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_tax_tags('777'),
                code='TAG_3',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('TAG_1.balance + TAG_2.balance'),
                code='SIMPLE_AGG',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('SIMPLE_AGG.balance + TAG_3.balance'),
                code='COMPLEX_AGG',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('TAG_1.balance + TAG_2.balance', subformula='if_other_expr_above(TAG_3.balance, EUR(13))'),
                code='BOUNDED_AGG',
            ),
            self._prepare_test_report_line(
                self._prepare_test_expression_tax_tags('3333'),
            ),
        ])

        other_report = self._create_report([
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('SIMPLE_AGG.balance + BOUNDED_AGG.balance', subformula='cross_report'),
                code='CROSS_REPORT_AGG',
            ),
        ])

        expr_map = {expression.report_line_id.code: expression for expression in (report + other_report).line_ids.expression_ids}

        self.assertEqual(
            expr_map['SIMPLE_AGG']._expand_aggregations(),
            expr_map['SIMPLE_AGG'] + expr_map['TAG_1'] + expr_map['TAG_2'],
        )

        self.assertEqual(
            expr_map['COMPLEX_AGG']._expand_aggregations(),
            expr_map['COMPLEX_AGG'] + expr_map['SIMPLE_AGG'] + expr_map['TAG_1'] + expr_map['TAG_2'] + expr_map['TAG_3'],
        )

        self.assertEqual(
            expr_map['BOUNDED_AGG']._expand_aggregations(),
            expr_map['BOUNDED_AGG'] + expr_map['TAG_1'] + expr_map['TAG_2'] + expr_map['TAG_3'],
        )

        self.assertEqual(
            expr_map['CROSS_REPORT_AGG']._expand_aggregations(),
            expr_map['CROSS_REPORT_AGG'] + expr_map['SIMPLE_AGG'] + expr_map['BOUNDED_AGG'] + expr_map['TAG_1'] + expr_map['TAG_2'] + expr_map['TAG_3'],
        )

    def test_load_more(self):
        partner_a, partner_b, partner_c = self.env['res.partner'].create([
            {'name': 'Partner A'},
            {'name': 'Partner B'},
            {'name': 'Partner C'},
        ])

        self._create_test_account_moves([
            self._prepare_test_account_move_line(1000.0, partner_id=partner_a.id, date='2020-01-01'),
            self._prepare_test_account_move_line(2000.0, partner_id=partner_b.id, date='2020-01-01'),
            self._prepare_test_account_move_line(3000.0, partner_id=partner_c.id, date='2020-01-01'),
        ])

        report = self._create_report(
            test_report_line_values_list=[self._prepare_test_report_line(
                self._prepare_test_expression_domain([('partner_id', '!=', False)], 'sum'),
                groupby='partner_id',
            )],
            load_more_limit=2,
        )

        options = self._generate_options(report, '2020-01-01', '2020-01-31')
        lines = report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            lines,
            [   0,                                1],
            [
                ('test_line_1',          '6,000.00'),
                ('Partner A',            '1,000.00'),
                ('Partner B',            '2,000.00'),
                ('Load more...',                 ''),
            ],
            options,
        )

        load_more_line = lines[-1]
        load_more_res = report._get_custom_report_function(load_more_line['expand_function'], 'expand_unfoldable_line')(
            load_more_line['id'],
            load_more_line['groupby'],
            options,
            load_more_line['progress'],
            load_more_line['offset']
        )['lines']

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            load_more_res,
            [   0,                                1],
            [
                ('Partner C',            '3,000.00'),
            ],
            options,
        )

    def test_engine_external_boolean(self):
        # Create the report.
        test_line = self._prepare_test_report_line(
            self._prepare_test_expression_external('most_recent', [
                self._prepare_test_external_values('1', '2020-01-02'),
                self._prepare_test_external_values('0', '2020-01-03'),
                self._prepare_test_external_values('1', '2020-01-03'),
                self._prepare_test_external_values('0', '2020-01-05'),
            ], figure_type='boolean')
        )

        report = self._create_report([test_line])
        # Check the values at multiple dates.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          'No'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-02')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',         'Yes'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-03', '2020-01-03')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',         'Yes'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-05', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          'No'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                          1],
            [
                ('test_line_1',          'No'),
            ],
            options,
        )

    def test_engine_external_string(self):
        # Create the report.
        test_line = self._prepare_test_report_line(
            self._prepare_test_expression_external('most_recent', [
                self._prepare_test_external_values('TARDIS', '2020-01-02', figure_type='string'),
                self._prepare_test_external_values('Kris Kelvin', '2020-01-03', figure_type='string'),
                self._prepare_test_external_values('Trisolaris', '2020-01-03', figure_type='string'),
                self._prepare_test_external_values("5-ounce bird carrying a 1-pound coconut", '2020-01-05', figure_type='string'),
            ], figure_type='string')
        )

        report = self._create_report([test_line])
        # Check the values at multiple dates.
        options = self._generate_options(report, '2020-01-01', '2020-01-01')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                                    1],
            [
                ('test_line_1',                      ''),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-02')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                                    1],
            [
                ('test_line_1',                'TARDIS'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-03', '2020-01-03')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                                    1],
            [
                ('test_line_1',            'Trisolaris'),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-05', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                                    1],
            [
                ('test_line_1', "5-ounce bird carrying a 1-pound coconut"),
            ],
            options,
        )

        options = self._generate_options(report, '2020-01-02', '2020-01-05')
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options),
            [   0,                                    1],
            [
                ('test_line_1', "5-ounce bird carrying a 1-pound coconut"),
            ],
            options,
        )

    def test_engine_external_default_value_tax_closing_fiscalyear_lock_date(self):
        def lock_via_fiscalyear_lock_date(non_tax_report, tax_report, report_options_map):
            lock_date_wizard = self.env['account.change.lock.date'].create({
                'fiscalyear_lock_date': fields.Date.from_string('2020-01-02'),
            })
            lock_date_wizard.change_lock_date()

        self._run_external_engine_default_test_case(False, True, lock_via_fiscalyear_lock_date)

    def test_engine_external_default_value_tax_closing_tax_lock_date(self):
        def lock_via_tax_lock_date(non_tax_report, tax_report, report_options_map):
            lock_date_wizard = self.env['account.change.lock.date'].create({
                'tax_lock_date': fields.Date.from_string('2020-01-02'),
            })
            lock_date_wizard.change_lock_date()

        self._run_external_engine_default_test_case(True, False, lock_via_tax_lock_date)

    def test_engine_external_default_value_tax_closing(self):
        def lock_via_tax_closing(non_tax_report, tax_report, report_options_map):
            tax_closing_action = self.env['account.tax.report.handler'].action_periodic_vat_entries(report_options_map[tax_report])
            closing_move_id = tax_closing_action['res_id']
            self.env['account.move'].browse(closing_move_id).action_post()

        self._run_external_engine_default_test_case(True, False, lock_via_tax_closing)

    def _run_external_engine_default_test_case(self, impact_tax_report, impact_non_tax_report, lock_operation_function):
        """ Common helper to run the tests of _default expressions
        """
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('10'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_external('sum', {}),
            self._prepare_test_expression_account_codes('10', label='_default_balance'),
        )

        non_tax_report = self._create_report([test_line_1, test_line_2], name="non_tax_report")
        tax_report = self._create_report([test_line_1, test_line_2], root_report_id=self.env.ref('account.generic_tax_report').id, name="tax_report")

        # Create the journal entries.
        self._create_test_account_moves([
            self._prepare_test_account_move_line(1000.0, account_code='100001'),
            self._prepare_test_account_move_line(-300.0, account_code='101002'),
            self._prepare_test_account_move_line(-600.0, account_code='314159'),
        ])

        report_options_map = {
            report: self._generate_options(
                report,
                '2020-01-01', '2020-01-31',
                default_options={
                    'unfold_all': True,
                }
            )
            for report in [non_tax_report, tax_report]
        }

        # Check the values before locking
        for report in [non_tax_report, tax_report]:
            with self.subTest(report=report.name):
                options = report_options_map[report]
                self.assertLinesValues(
                    # pylint: disable=bad-whitespace
                    report._get_lines(options),
                    [0,                             1],
                    [
                        ('test_line_1',         700.0),
                        ('100001 100001',      1000.0),
                        ('101002 101002',      -300.0),
                        ('test_line_2',           0.0),
                    ],
                    options,
                )

        # Run the lock operation
        lock_operation_function(non_tax_report, tax_report, report_options_map)

        # Check the values after locking
        for report, impacted in [(non_tax_report, impact_non_tax_report), (tax_report, impact_tax_report)]:
            with self.subTest(report=report.name):
                options = report_options_map[report]
                if impacted:
                    self.assertLinesValues(
                        # pylint: disable=bad-whitespace
                        report._get_lines(options),
                        [0,                             1],
                        [
                            ('test_line_1',         700.0),
                            ('100001 100001',      1000.0),
                            ('101002 101002',      -300.0),
                            ('test_line_2',         700.0),
                        ],
                        options,
                    )
                else:
                    self.assertLinesValues(
                        # pylint: disable=bad-whitespace
                        report._get_lines(options),
                        [0,                             1],
                        [
                            ('test_line_1',         700.0),
                            ('100001 100001',      1000.0),
                            ('101002 101002',      -300.0),
                            ('test_line_2',           0.0),
                        ],
                        options,
                    )

    def test_engine_aggregation_cross_bound(self):
        report_1 = self._create_report([
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('line_2_1.balance', subformula='cross_report'),
                name='Line 1-1',
                code='line_1_1',
            ),
        ])

        self._create_report([
            self._prepare_test_report_line(
                self._prepare_test_expression_aggregation('14.0', subformula='if_other_expr_above(line_2_1.dudu, EUR(0))'),
                self._prepare_test_expression_account_codes('101', label='dudu'),
                name='Line 2-1',
                code='line_2_1',
            ),
        ])

        options = self._generate_options(report_1, '2020-01-01', '2020-01-01')

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_1._get_lines(options),
            [   0,                          1],
            [
                ('Line 1-1',              0.0),
            ],
            options
        )

        self._create_test_account_moves([
            self._prepare_test_account_move_line(10, account_code='101001'),
            self._prepare_test_account_move_line(-10, account_code='100001'),
        ])

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report_1._get_lines(options),
            [   0,                          1],
            [
                ('Line 1-1',             14.0),
            ],
            options
        )

    def test_change_expression_engine_to_tax_tags(self):
        """
        Ensure that tax tags are created when switching the expression engine to tax tags if formula is unchanged.
        """
        formula = 'dudu'
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_external(formula, [self._prepare_test_external_values(100.0, '2020-01-01')], label='external'),
        )
        report = self._create_report([test_line_1], country_id=self.fake_country.id)
        tags = self.env['account.account.tag']._get_tax_tags(formula, self.fake_country.id)
        self.assertEqual(len(tags), 0)
        report.line_ids[0].expression_ids[0].engine = 'tax_tags'
        tags = self.env['account.account.tag']._get_tax_tags(formula, self.fake_country.id)
        self.assertEqual(tags.mapped('name'), ['-' + formula, '+' + formula])

    def test_integer_rounding(self):
        line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_domain([('account_id.code', '=', '101001')], 'sum'),
            code='test_1',
        )
        line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('42'),
            code='test_2',
        )
        line_3 = self._prepare_test_report_line(
            self._prepare_test_expression_account_codes('1'),
            code='test_3',
        )
        line_4 = self._prepare_test_report_line(
            self._prepare_test_expression_external('sum', [
                self._prepare_test_external_values(3.5, '2023-01-01'),
            ]),
            code='test_4',
        )
        line_5 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test_1.balance + test_2.balance + test_3.balance + test_4.balance'),
            code='test_5',
        )
        line_6 = self._prepare_test_report_line(
            self._prepare_test_expression_aggregation('test_5.balance / 10'),
        )

        report = self._create_report([line_1, line_2, line_3, line_4, line_5, line_6], country_id=self.fake_country.id,)

        self._create_test_account_moves([
            self._prepare_test_account_move_line(5.4, account_code='101001', tax_tags=['+42'], date='2023-01-01'),
        ])

        main_options = self._generate_options(report, '2023-01-01', '2023-01-01')

        # Test with a first rounding
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(report._custom_options_add_integer_rounding({**main_options}, 'HALF-UP')),
            [   0,                              1],
            [
                ('test_line_1',               5.0),
                ('test_line_2',               5.0),
                ('test_line_3',               5.0),
                ('test_line_4',               4.0),
                ('test_line_5',              19.0),
                ('test_line_6',               2.0),
            ],
            main_options,
        )

        # Test with another rounding method
        up_options = report._custom_options_add_integer_rounding({**main_options}, 'UP', previous_options={'integer_rounding_enabled': True})
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(up_options),
            [   0,                              1],
            [
                ('test_line_1',               6.0),
                ('test_line_2',               6.0),
                ('test_line_3',               6.0),
                ('test_line_4',               4.0),
                ('test_line_5',              22.0),
                ('test_line_6',               3.0),
            ],
            up_options
        )

        # In file export mode, the rounding should always be applied, even if it was previously disabled
        print_mode_options = report._custom_options_add_integer_rounding(
            {**main_options, 'export_mode': 'file'},
            'HALF-UP',
            previous_options={'integer_rounding_enabled': False},
        )
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(print_mode_options),
            [   0,                              1],
            [
                ('test_line_1',               5.0),
                ('test_line_2',               5.0),
                ('test_line_3',               5.0),
                ('test_line_4',               4.0),
                ('test_line_5',              19.0),
                ('test_line_6',               2.0),
            ],
            print_mode_options,
        )

        # Rounding available, but disabled
        no_rounding_options = report._custom_options_add_integer_rounding({**main_options}, 'UP', previous_options={'integer_rounding_enabled': False})
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(no_rounding_options),
            [   0,                               1],
            [
                ('test_line_1',               5.40),
                ('test_line_2',               5.40),
                ('test_line_3',               5.40),
                ('test_line_4',               3.50),
                ('test_line_5',              19.70),
                ('test_line_6',               1.97),
            ],
            no_rounding_options,
        )

    def test_print_hide_0_lines(self):
        # Create the report.
        test_line_1 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('11'),
            groupby='account_id',
        )
        test_line_2 = self._prepare_test_report_line(
            self._prepare_test_expression_tax_tags('222T'),
            groupby='account_id',
        )
        report = self._create_report([test_line_1, test_line_2], country_id=self.fake_country.id)

        # Create the journal entries.
        self._create_test_account_moves([
            self._prepare_test_account_move_line(3000.0, account_code='101001', tax_tags=['+11', '-222T']),
            self._prepare_test_account_move_line(3600.0, account_code='101001', tax_tags=['+222T']),
            self._prepare_test_account_move_line(-600.0, account_code='101001', tax_tags=['+222T', '-11']),
        ])

        # To ensure that the lines are shown when hide_0_lines isn't toggled and vice versa, we test both scenarios.
        options_not_hide = self._generate_options(
            report,
            '2020-01-01', '2020-01-01',
            default_options={'unfold_all': True, 'export_mode': 'print'}
        )
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options_not_hide),
            [   0,                        1],
            [
                ('test_line_1',      3600.0),
                ('101001 101001',    3600.0),
                ('test_line_2',         0.0),
                ('101001 101001',       0.0),
            ],
            options_not_hide,
        )

        options_hide = self._generate_options(
            report,
            '2020-01-01', '2020-01-01',
            default_options={'unfold_all': True, 'export_mode': 'print', 'hide_0_lines': True}
        )
        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            report._get_lines(options_hide),
            [   0,                        1],
            [
                ('test_line_1',      3600.0),
                ('101001 101001',    3600.0),
            ],
            options_hide,
        )
