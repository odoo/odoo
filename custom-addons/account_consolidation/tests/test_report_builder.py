# -*- coding: utf-8 -*-
# pylint: disable=W0612
from odoo.tests import tagged
from odoo.addons.account_consolidation.tests.account_consolidation_test_classes import AccountConsolidationTestCase
from odoo.addons.account_consolidation.report.builder.comparison import ComparisonBuilder
from odoo.addons.account_consolidation.report.builder.comparison import ComparisonBuilder
from odoo.addons.account_consolidation.report.builder.default import DefaultBuilder
from odoo.tools.misc import NON_BREAKING_SPACE

from unittest.mock import patch


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestAbstractBuilder(AccountConsolidationTestCase):
    # Tested with a ComparisonBuilder as AbstractBuilder is abstract
    def setUp(self):
        super().setUp()
        self.ap = self._create_analysis_period(start_date="2019-02-01", end_date="2019-02-28")
        self.builder = ComparisonBuilder(self.env, self.ap._format_value)
        self.report = self.env.ref('account_consolidation.consolidated_balance_report')

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._get_hierarchy')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._get_plain')
    def test_get_lines(self, patched_get_plain, patched_get_hierarchy):
        patched_get_plain.return_value = [{'id': 1}]
        patched_get_hierarchy.return_value = [{'id': 2}]
        options = self.report.get_options()
        self.assertListEqual([], self.builder._get_lines([], options))
        patched_get_plain.assert_not_called()
        patched_get_hierarchy.assert_not_called()

        ap2 = self._create_analysis_period()
        period_ids = [self.ap.id, ap2.id]
        kwargs = {
            'period_ids': period_ids,
            'chart_ids': [self.chart.id],
            'cols_amount': len(period_ids),
            'include_percentage': True
        }
        # EMPTY OPTIONS
        self.assertListEqual(patched_get_hierarchy.return_value,
                             self.builder._get_lines(period_ids, options, None))
        patched_get_hierarchy.assert_called_once_with(options, None, **kwargs)
        patched_get_hierarchy.reset_mock()
        patched_get_plain.assert_not_called()

        # WITH HIERARCHY
        options = self.report.get_options({'consolidation_hierarchy': True})
        self.assertListEqual(patched_get_hierarchy.return_value, self.builder._get_lines(period_ids, options, None))
        patched_get_hierarchy.assert_called_once_with(options, None, **kwargs)
        patched_get_hierarchy.reset_mock()
        patched_get_plain.assert_not_called()

        # WITH HIERARCHY AND LINE ID
        self.assertListEqual(patched_get_hierarchy.return_value, self.builder._get_lines(period_ids, options, 1))
        patched_get_hierarchy.assert_called_once_with(options, 1, **kwargs)
        patched_get_hierarchy.reset_mock()
        patched_get_plain.assert_not_called()

        # WITHOUT HIERARCHY
        options = self.report.get_options({'consolidation_hierarchy': False})
        self.assertListEqual(patched_get_plain.return_value, self.builder._get_lines(period_ids, options, None))
        patched_get_plain.assert_called_once_with(options, **kwargs)
        patched_get_plain.reset_mock()
        patched_get_hierarchy.assert_not_called()

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._handle_accounts')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._build_total_line')
    def test__get_plain(self, patched_total, patched_handle):
        patched_total.return_value = {'name': 'bli'}
        patched_handle.return_value = ([42, 24], [{'name': 'bla'}, {'name': 'blu'}])
        chart_ids = [self.chart.id]
        cols_amount = 0
        period_ids = []
        include_percentage = False,
        options = {}
        kwargs = {
            'chart_ids': chart_ids,
            'cols_amount': cols_amount,
            'period_ids': period_ids,
            'include_percentage': include_percentage
        }
        res = self.builder._get_plain(options, **kwargs)
        # patched_handle.return_value[1] now contains also patched total return value as it has been append
        self.assertIn(patched_total.return_value, patched_handle.return_value[1])
        self.assertListEqual(res, patched_handle.return_value[1])
        accounts = self.env['consolidation.account'].search([('id', '<', 0)])
        patched_handle.assert_called_once_with(accounts, options, 3, **kwargs)
        patched_total.assert_called_once_with(patched_handle.return_value[0], options, **kwargs)

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._handle_orphan_accounts')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._get_root_sections')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._handle_sections')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._build_total_line')
    def test__get_hierarchy(self, patched_total, patched_sections, patched_root, patched_orphan):
        patched_total.return_value = {
            'columns': [{'no_format': 4242}, {'no_format': 2424}]
        }
        patched_sections.return_value = ([42, 24], [
            {'id': 'rootsect1', 'name': 'rootsect1', 'columns': [
                {'no_format': 40}, {'no_format': 20}
            ]},
            {'id': 'sect2', 'name': 'sect2', 'parent_id': 'rootsect1', 'columns': [
                {'no_format': 2}, {'no_format': 4}
            ]}])
        patched_root.return_value = [1]  # Need at least 1
        patched_orphan.return_value = ([4200, 2400], [{'id': 1, 'name': 'orphan1', 'columns': [
            {'no_format': 4200}, {'no_format': 2400}
        ]}])
        chart_ids = []
        cols_amount = 2
        period_ids = []
        include_percentage = False
        options = {}
        line_id = None
        res = self.builder._get_hierarchy(options, line_id, chart_ids=chart_ids, cols_amount=cols_amount,
                                          period_ids=period_ids, include_percentage=include_percentage)
        # ORPHANS then ROOT SECTIONS (ROOT SECT 1 + SUB) then TOTAL
        expected = patched_orphan.return_value[1] + patched_sections.return_value[1] + [patched_total.return_value]
        self.assertListEqual(res, expected)
        patched_total.assert_called_once_with([4242, 2424], {}, chart_ids=chart_ids, cols_amount=cols_amount,
                                              period_ids=period_ids, include_percentage=include_percentage)

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._build_section_line')
    @patch(
        'odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler.section_line_should_be_added',
        return_value=True)
    def test__handle_sections(self, patched_added, patched_build):
        section_totals = [4200.42, 28.0, -0.01]
        patched_build.return_value = (section_totals, [
            {
                'columns': [{'no_format': section_total} for section_total in section_totals]
            },
            {
                'columns': [{'no_format': -0.42}, {'no_format': -42.01}, {'no_format': 0.02}]
            },
            {
                'columns': [{'no_format': 4200.84}, {'no_format': 14.01}, {'no_format': -0.03}]
            },
        ])
        sections = ['fake1', 'fake2']
        amount_of_sections = len(sections)
        totals, lines = self.builder._handle_sections(sections, options={}, level=2, cols_amount=3, period_ids=[],
                                                      include_percentage=False)
        self.assertEqual(len(totals), len(section_totals))
        self.assertEqual(len(lines), len(section_totals) * amount_of_sections)
        self.assertListEqual(totals, [amount_of_sections * x for x in section_totals])
        self.assertListEqual(lines, amount_of_sections * patched_build.return_value[1])

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._get_orphan_accounts')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._handle_accounts')
    def test__handle_orphan_accounts(self, patched_handle_accounts, patched_get_orphan):
        patched_get_orphan.return_value = ['blouh']
        patched_handle_accounts.return_value = ([], [])
        chart_ids = []
        amount_of_columns = 0
        period_ids = []
        options = {}
        include_percentage = False
        level = 2
        kwargs = {
            'chart_ids': chart_ids,
            'cols_amount': amount_of_columns,
            'period_ids': period_ids,
            'include_percentage': include_percentage
        }
        self.builder._handle_orphan_accounts(options, level, **kwargs)
        patched_get_orphan.assert_called_once_with(options, **kwargs)
        patched_handle_accounts.assert_called_once_with(patched_get_orphan.return_value, options, level, **kwargs)

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._compute_account_totals')
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._format_account_line')
    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler.account_line_should_be_added',
           return_value=True)
    def test__handle_accounts(self, patched_account_added, patched_build_account, patched_compute):
        patched_build_account.return_value = [{}, {}]
        patched_compute.return_value = [42.0, 79.0]
        accounts = [self._create_consolidation_account(), self._create_consolidation_account()]
        # Simulates that there are 2 periods
        period_ids = [0, 0]
        totals, lines = self.builder._handle_accounts(accounts, {}, 2, cols_amount=2, period_ids=period_ids,
                                                      include_percentage=False)
        self.assertEqual(len(totals), 2)
        self.assertListEqual(totals, [42.0 * 2, 79.0 * 2])
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(len(line), 2)
            self.assertListEqual(line, patched_build_account.return_value)

    def test__get_root_sections(self):
        Section = self.env['consolidation.group']
        root_s = Section.create({'name': 'bluh', 'chart_id': self.chart.id})
        Section.create({'name': 'bluh', 'parent_id': root_s.id, 'chart_id': self.chart.id})
        Section.create({'name': 'bluh', 'parent_id': root_s.id, 'chart_id': self.chart.id})
        self.assertEqual(root_s, self.builder._get_root_sections({}, chart_ids=[self.chart.id]))

    def test__get_orphan_accounts(self):
        Section = self.env['consolidation.group']
        Account = self.env['consolidation.account']
        s = Section.create({'name': 'bluh', 'chart_id': self.chart.id})
        account1 = self._create_consolidation_account()
        account2 = self._create_consolidation_account()
        Account.browse([account1.id, account2.id]).write({'group_id': s.id})
        self.assertEqual(len(self.builder._get_orphan_accounts({}, chart_ids=[self.chart.id])), 0)
        orphan_account = self._create_consolidation_account()
        self.assertEqual(orphan_account, self.builder._get_orphan_accounts({}, chart_ids=[self.chart.id]))


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestComparisonBuilder(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()
        self.ap = self._create_analysis_period(start_date="2019-02-01", end_date="2019-02-28")
        self.builder = ComparisonBuilder(self.env, self.ap._format_value)

    def test__get_params(self):
        ap_ids = [self.ap.id]
        res = self.builder._get_params(ap_ids, {})
        self.assertEqual(len(res), 4)
        self.assertIn('chart_ids', res)
        self.assertIn('cols_amount', res)
        self.assertIn('include_percentage', res)
        self.assertIn('period_ids', res)
        self.assertListEqual(res['chart_ids'], [self.chart.id])
        self.assertEqual(res['cols_amount'], len(ap_ids))
        self.assertFalse(res['include_percentage'])
        self.assertListEqual(res['period_ids'], ap_ids)

    def test__output_will_be_empty(self):
        self.assertTrue(self.builder._output_will_be_empty([], {}))
        self.assertFalse(self.builder._output_will_be_empty(['bla'], {}))

    def test__compute_account_totals(self):
        Journal = self.env['consolidation.journal']
        account = self._create_consolidation_account()
        periods = [
            self.ap,
            self._create_analysis_period(start_date="2019-01-01", end_date="2019-01-31")
        ]
        for i, period in enumerate(periods):
            Journal.create({
                'name': 'blah',
                'period_id': period.id,
                'chart_id': self.chart.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': account.id,
                        'currency_amount': 42.0 * (i + 1),
                        'amount': 42.0 * (i + 1),
                    }),
                    (0, 0, {
                        'account_id': account.id,
                        'currency_amount': 4200.42 * (i + 1),
                        'amount': 4200.42 * (i + 1)
                    }),
                ]
            })

        expected = [4242.42, 8484.84]
        actual = self.builder._compute_account_totals(account, period_ids=[p.id for p in periods])
        self.assertListEqual(expected, actual)

    def test__get_default_line_totals(self):
        combinations = (
            (self.builder._get_default_line_totals({}), []),
            (self.builder._get_default_line_totals({}, cols_amount=0), []),
            (self.builder._get_default_line_totals({}, cols_amount=1), [0.0]),
            (self.builder._get_default_line_totals({}, cols_amount=2), [0.0, 0.0]),
            (self.builder._get_default_line_totals({}, period_ids=[]), []),
            (self.builder._get_default_line_totals({}, period_ids=[1]), [0.0]),
            (self.builder._get_default_line_totals({}, period_ids=[1, 1]), [0.0, 0.0]),
            (self.builder._get_default_line_totals({}, cols_amount=1, period_ids=[1, 1]), [0.0])
        )
        for res, expected in combinations:
            self.assertEqual(res, expected)

    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler.section_line_should_be_added',
           return_value=True)
    @patch('odoo.addons.account_consolidation.report.handler.show_zero.ShowZeroHandler.account_line_should_be_added',
           return_value=True)
    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._compute_account_totals')
    def test__build_section_line_and_format_account_line(self, patched_account_totals, patched_account_added,
                                                         patched_section_added):
        patched_account_totals.return_value = [1000.0, -2000.0]
        section = self.env['consolidation.group'].create({
            'name': 'BLUH',
            'chart_id': self.chart.id,
            'child_ids': [(0, 0, {'name': 'BLUH CHILD', 'chart_id': self.chart.id})]
        })
        section.child_ids.write({
            'account_ids': [(0, 0, {
                'name': 'BLUH CHILD Acccountu',
                'currency_mode': 'end',
                'chart_id': self.chart.id,
            })]
        })
        options = self.report.get_options({'unfold_all': True})

        section_1_id = self.report._get_generic_line_id(None, None, 'section_%s' % section.id)
        section_2_id = self.report._get_generic_line_id(None, None, 'section_%s' % section.child_ids[0].id, parent_line_id=section_1_id)
        account_line_id = self.report._get_generic_line_id(None, None, section.child_ids[0].account_ids[0].id, parent_line_id=section_2_id)

        expected = [
            {
                'id': section_1_id,
                'name': section.name,
                'level': 0,
                'unfoldable': True,
                'unfolded': True,
                'columns': [
                    {
                        'name': f'1,000.00{NON_BREAKING_SPACE}€',
                        'no_format': 1000.0,
                        'figure_type': 'monetary',
                        'is_zero': False,
                        'class': 'number',
                    },
                    {
                        'name': f'-2,000.00{NON_BREAKING_SPACE}€',
                        'no_format': -2000.0,
                        'figure_type': 'monetary',
                        'is_zero': False,
                        'class': 'number',
                    }
                ]
            },
            {
                'id': section_2_id,
                'name': section.child_ids[0].name,
                'level': 3,
                'unfoldable': True,
                'unfolded': True,
                'parent_id': section_1_id,
                'columns': [
                    {
                        'name': f'1,000.00{NON_BREAKING_SPACE}€',
                        'no_format': 1000.0,
                        'figure_type': 'monetary',
                        'is_zero': False,
                        'class': 'number',
                    },
                    {
                        'name': f'-2,000.00{NON_BREAKING_SPACE}€',
                        'no_format': -2000.0,
                        'figure_type': 'monetary',
                        'is_zero': False,
                        'class': 'number',
                    }
                ]
            },
            {
                'id': account_line_id,
                'name': '%s' % section.child_ids[0].account_ids[0].display_name,
                'title_hover': '%s (Closing Rate Currency Conversion Method)' %
                               section.child_ids[0].account_ids[0].display_name,
                'columns': [
                    {
                        'name': f'1,000.00{NON_BREAKING_SPACE}€',
                        'no_format': 1000.0,
                        'figure_type': 'monetary',
                        'class': 'number',
                        'is_zero': False,
                        'auditable': True,
                    },
                    {
                        'name': f'-2,000.00{NON_BREAKING_SPACE}€',
                        'no_format': -2000.0,
                        'figure_type': 'monetary',
                        'class': 'number',
                        'is_zero': False,
                        'auditable': False,
                    }
                ],
                'level': 5,
                'parent_id': section_2_id,
            }
        ]
        section_totals, section_line = self.builder._build_section_line(section, 0, options, include_percentage=False)
        self.assertListEqual(section_line, expected)

    def test__build_section_line_no_children_no_accounts(self):
        level = 0
        section = self.env['consolidation.group'].create({
            'name': 'BLUH',
            'chart_id': self.chart.id,
        })
        options = self.report.get_options({'unfold_all': False})
        section_totals, section_line = self.builder._build_section_line(section, level, options, cols_amount=2, include_percentage=False)
        expected = [{
            'id': self.report._get_generic_line_id(None, None, 'section_%s' % section.id),
            'name': 'BLUH',
            'level': level,
            'unfoldable': True,
            'unfolded': False,
            'columns': [
                {'name': f'0.00{NON_BREAKING_SPACE}€', 'no_format': 0.0, 'figure_type': 'monetary', 'is_zero': True, 'class': 'number muted'},
                {'name': f'0.00{NON_BREAKING_SPACE}€', 'no_format': 0.0, 'figure_type': 'monetary', 'is_zero': True, 'class': 'number muted'},
            ]
        }]
        self.assertListEqual(expected, section_line)
        section_totals, section_line = self.builder._build_section_line(section, level, options, cols_amount=2,
                                                                        include_percentage=False)
        self.assertListEqual(expected, section_line)

        # SHOULD BE UNFOLDED FOR THE TWO EXAMPLES BELOW
        expected[0]['unfolded'] = True

        options['unfold_all'] = True
        section_totals, section_line = self.builder._build_section_line(section, level, options, cols_amount=2,
                                                                        include_percentage=False)
        self.assertListEqual(expected, section_line)

        options['unfold_all'] = False
        options['unfolded_lines'] = [self.report._get_generic_line_id(None, None, 'section_%s' % section.id)]
        section_totals, section_line = self.builder._build_section_line(section, level, options, cols_amount=2,
                                                                        include_percentage=False)
        self.assertListEqual(expected, section_line)

    def test__build_percentage_column(self):
        test_values = [
            (0, 200.0, 'n/a', None),
            (1000.0, 200.0, -80.0, 'number color-red'),
            (42.0, 462.0, 1000.0, 'number color-green'),
            (-1000.0, 1000.0, 200.0, 'number color-green'),
            (2000.0, -4000.0, -300.0, 'number color-red'),
            (200, 0, -100.0, 'number color-red'),
        ]
        for orig_value, now_value, exp_percent, exp_class in test_values:
            perc_column = ComparisonBuilder._build_percentage_column(orig_value, now_value)
            self.assertIn('name', perc_column)
            # NO FORMAT NAME
            if exp_percent != 'n/a':
                self.assertIn('no_format', perc_column)
                if isinstance(exp_percent, float):
                    self.assertAlmostEqual(perc_column['no_format'], exp_percent)
                else:
                    self.assertEqual(perc_column['no_format'], exp_percent)
            else:
                self.assertNotIn('no_format', perc_column)

            # CLASS
            if exp_class is not None:
                self.assertIn('class', perc_column)
                self.assertEqual(perc_column['class'], exp_class)
            else:
                self.assertNotIn('class', perc_column)

    @patch('odoo.addons.account_consolidation.report.builder.comparison.ComparisonBuilder._build_percentage_column',
           return_value={'name': '0 %', 'no_format': 0})
    def test__build_total_line(self, patched_bpc):
        other_chart = self.env['consolidation.chart'].create({
            'name': 'Other chart',
            'currency_id': self.env['res.currency'].search([('symbol', '=', '$')])[0].id
        })

        totals = [0.0, 1500000.0, -2000.0]
        # NO PERCENTAGE
        # €
        euro_exp = {'id': self.report._get_generic_line_id(None, None, 'grouped_accounts_total'),
                    'name': 'Total', 'class': 'total', 'level': 0,
                    'columns': [{'name': f'0.00{NON_BREAKING_SPACE}€', 'figure_type': 'monetary', 'no_format': 0.0, 'class': 'number'},
                                {'name': f'1,500,000.00{NON_BREAKING_SPACE}€', 'figure_type': 'monetary', 'no_format': 1500000.0, 'class': 'number text-danger'},
                                {'name': f'-2,000.00{NON_BREAKING_SPACE}€', 'figure_type': 'monetary', 'no_format': -2000.0, 'class': 'number text-danger'}]}
        options = self.report.get_options()
        euro_total_line = self.builder._build_total_line(totals, options, include_percentage=False)
        self.assertDictEqual(euro_total_line, euro_exp)
        # $
        ap_usd = self._create_analysis_period(chart=other_chart)
        us_builder = ComparisonBuilder(self.env, ap_usd._format_value)
        usd_total_line = us_builder._build_total_line(totals, options, include_percentage=False)

        usd_exp = {'id': self.report._get_generic_line_id(None, None, 'grouped_accounts_total'),
                   'name': 'Total', 'class': 'total', 'level': 0,
                   'columns': [{'name': f'${NON_BREAKING_SPACE}0.00', 'figure_type': 'monetary', 'no_format': 0.0, 'class': 'number'},
                               {'name': f'${NON_BREAKING_SPACE}1,500,000.00', 'figure_type': 'monetary', 'no_format': 1500000.0, 'class': 'number text-danger'},
                               {'name': f'${NON_BREAKING_SPACE}-2,000.00', 'figure_type': 'monetary', 'no_format': -2000.0, 'class': 'number text-danger'}]}
        self.assertDictEqual(usd_total_line, usd_exp)
        patched_bpc.assert_not_called()
        # WITH PERCENTAGE
        totals = [0.0, -2000.0]
        euro_prct_total_line = self.builder._build_total_line(totals, options, include_percentage=True)
        euro_exp_prct = {'id': self.report._get_generic_line_id(None, None, 'grouped_accounts_total'),
                         'name': 'Total', 'class': 'total', 'level': 0,
                         'columns': [{'name': f'0.00{NON_BREAKING_SPACE}€', 'figure_type': 'monetary', 'no_format': 0.0, 'class': 'number'},
                                     {'name': f'-2,000.00{NON_BREAKING_SPACE}€', 'figure_type': 'monetary', 'no_format': -2000.0, 'class': 'number text-danger'},
                                     patched_bpc.return_value]}
        self.assertDictEqual(euro_prct_total_line, euro_exp_prct)


@tagged('post_install', '-at_install', 'trial_balance_report')
class TestDefaultBuilder(AccountConsolidationTestCase):
    def setUp(self):
        super().setUp()

        def create_journal(amount1, amount2):
            return Journal.create({
                'name': 'blah',
                'period_id': self.ap.id,
                'chart_id': self.chart.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': self.consolidation_account.id,
                        'currency_amount': amount1,
                        'amount': amount1,
                    }),
                    (0, 0, {
                        'account_id': self.consolidation_account.id,
                        'currency_amount': amount2,
                        'amount': amount2,
                    })
                ]
            })

        Journal = self.env['consolidation.journal']
        self.ap = self._create_analysis_period(start_date="2019-02-01", end_date="2019-02-28")
        self.consolidation_account = self._create_consolidation_account(name='n' * 45)  # Using a long name
        journals = create_journal(42, 4200.40), create_journal(1989.0, 1912.0)
        self.journals = Journal.browse((j.id for j in journals))
        self.builder = DefaultBuilder(self.env, self.ap._format_value, self.journals)

    def test__get_params(self):
        res = self.builder._get_params([self.ap.id], {})
        self.assertEqual(len(res), 3)
        self.assertIn('chart_ids', res)
        self.assertIn('cols_amount', res)
        self.assertIn('period_ids', res)
        self.assertListEqual(res['chart_ids'], [self.chart.id])
        self.assertEqual(res['cols_amount'], len(self.journals) + 1)
        self.assertListEqual(res['period_ids'], [self.ap.id])

    def test__compute_account_totals(self):
        res = self.builder._compute_account_totals(self.consolidation_account)
        expected = [4242.4, 3901.0, 8143.4]
        self.assertEqual(res, expected)

    def test__format_account_line(self):
        level = 2
        totals = [12.0, 13.14]
        line = self.builder._format_account_line(self.consolidation_account, None, level, totals, self.report.get_options())
        account_name = self.consolidation_account.name
        account_currency_name = self.consolidation_account.get_display_currency_mode()
        expected = {
            'id': self.report._get_generic_line_id(None, None, self.consolidation_account.id),
            'name': account_name[:40] + '...',  # Long names should be shortened
            'title_hover': "%s (%s Currency Conversion Method)" % (account_name, account_currency_name),
            'columns': [{
                'name': self.builder.value_formatter(t),
                'no_format': t,
                'figure_type': 'monetary',
                'class': 'number',
                'is_zero': False,
                'auditable': True,
                'journal_id': False  # False as no company period id is set on journals
            } for t in totals],
            'level': 2,
        }
        expected['columns'][-1]['auditable'] = False

        self.assertDictEqual(expected, line)

    def test__get_default_line_totals(self):
        combinations = (
            (self.builder._get_default_line_totals({}), [0.0, 0.0]),
            (self.builder._get_default_line_totals({}, cols_amount=0), []),
            (self.builder._get_default_line_totals({}, cols_amount=1), [0.0]),
            (self.builder._get_default_line_totals({}, cols_amount=2), [0.0, 0.0]),
        )
        for res, expected in combinations:
            self.assertEqual(res, expected)
