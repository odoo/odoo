# -*- coding: utf-8 -*-
import datetime
from odoo.tests import tagged
from odoo import fields
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools import date_utils
from odoo.tools.misc import formatLang, format_date

from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountReportsFilters(AccountingTestCase):
    def _assert_filter_date(self, filter_date, expected_date_values):
        ''' Initialize the 'date' key in the report options and then, assert the result matches the expectations.

        :param filter_date:             The filter_date report values.
        :param expected_date_values:    The expected results for the options['date'] as a dict.
        '''
        report = self.env['account.report']
        report.filter_date = filter_date

        options = {}
        report._init_filter_date(options)

        self.assertDictEqual(options['date'], expected_date_values)

    def _assert_filter_comparison(self, filter_date, filter_comparison, expected_period_values):
        ''' Initialize the 'date'/'comparison' keys in the report options and then, assert the result matches the
        expectations.

        :param filter_date:             The filter_date report values.
        :param filter_comparison:       The filter_comparison report values.
        :param expected_period_values: The expected results for options['comparison']['periods'] as a list of dicts.
        '''
        report = self.env['account.report']
        report.filter_date = filter_date
        report.filter_comparison = filter_comparison

        options = {}
        report._init_filter_date(options)
        report._init_filter_comparison(options)

        self.assertEquals(len(options['comparison']['periods']), len(expected_period_values))

        for i, expected_values in enumerate(expected_period_values):
            self.assertDictEqual(options['comparison']['periods'][i], expected_values)

    ####################################################
    # DATES RANGE
    ####################################################

    def test_filter_date_month_range(self):
        ''' Test the filter_date with 'this_month'/'last_month' in 'range' mode.'''
        def get_month_string(date):
            return format_date(self.env, fields.Date.to_string(date), date_format='MMM YYYY')

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            month_df, month_dt = date_utils.get_month(fields.Date.today())
            month_df_period_1, month_dt_period_1 = date_utils.get_month(month_dt - relativedelta(months=1))
            month_df_period_2, month_dt_period_2 = date_utils.get_month(month_dt - relativedelta(months=2))
            month_df_year_1, month_dt_year_1 = date_utils.get_month(month_dt - relativedelta(years=1))
            month_df_year_2, month_dt_year_2 = date_utils.get_month(month_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_month', 'mode': 'range'},
                {
                    'string': get_month_string(month_dt),
                    'period_type': 'month',
                    'mode': 'range',
                    'filter': 'this_month',
                    'date_from': fields.Date.to_string(month_df),
                    'date_to': fields.Date.to_string(month_dt),
                },
            )

            self._assert_filter_date(
                {'filter': 'last_month', 'mode': 'range'},
                {
                    'string': get_month_string(month_dt_period_1),
                    'period_type': 'month',
                    'mode': 'range',
                    'filter': 'last_month',
                    'date_from': fields.Date.to_string(month_df_period_1),
                    'date_to': fields.Date.to_string(month_dt_period_1),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_month', 'mode': 'range'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_month_string(month_dt_period_1),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(month_df_period_1),
                        'date_to': fields.Date.to_string(month_dt_period_1),
                    },
                    {
                        'string': get_month_string(month_dt_period_2),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(month_df_period_2),
                        'date_to': fields.Date.to_string(month_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_month', 'mode': 'range'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_month_string(month_dt_year_1),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(month_df_year_1),
                        'date_to': fields.Date.to_string(month_dt_year_1),
                    },
                    {
                        'string': get_month_string(month_dt_year_2),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(month_df_year_2),
                        'date_to': fields.Date.to_string(month_dt_year_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_month', 'mode': 'range'},
                {
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(month_df_year_1),
                    'date_to': fields.Date.to_string(month_dt_year_1)},
                [
                    {
                        'string': get_month_string(month_dt_year_1),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(month_df_year_1),
                        'date_to': fields.Date.to_string(month_dt_year_1),
                    },
                ],
            )

    def test_filter_date_quarter_range(self):
        ''' Test the filter_date with 'this_quarter'/'last_quarter' in 'range' mode.'''
        def get_quarter_string(date):
            quarter_names = get_quarter_names('abbreviated', locale='en_US')
            return u'%s\N{NO-BREAK SPACE}%s' % (quarter_names[date_utils.get_quarter_number(date)], date.year)

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            quarter_df, quarter_dt = date_utils.get_quarter(fields.Date.today())
            quarter_df_period_1, quarter_dt_period_1 = date_utils.get_quarter(quarter_dt - relativedelta(months=3))
            quarter_df_period_2, quarter_dt_period_2 = date_utils.get_quarter(quarter_dt - relativedelta(months=6))
            quarter_df_year_1, quarter_dt_year_1 = date_utils.get_quarter(quarter_dt - relativedelta(years=1))
            quarter_df_year_2, quarter_dt_year_2 = date_utils.get_quarter(quarter_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_quarter', 'mode': 'range'},
                {
                    'string': get_quarter_string(quarter_dt),
                    'period_type': 'quarter',
                        'mode': 'range',
                    'filter': 'this_quarter',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
            )

            self._assert_filter_date(
                {'filter': 'last_quarter', 'mode': 'range'},
                {
                    'string': get_quarter_string(quarter_dt_period_1),
                    'period_type': 'quarter',
                    'mode': 'range',
                    'filter': 'last_quarter',
                    'date_from': fields.Date.to_string(quarter_df_period_1),
                    'date_to': fields.Date.to_string(quarter_dt_period_1),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_quarter', 'mode': 'range'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_quarter_string(quarter_dt_period_1),
                        'period_type': 'quarter',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarter_df_period_1),
                        'date_to': fields.Date.to_string(quarter_dt_period_1),
                    },
                    {
                        'string': get_quarter_string(quarter_dt_period_2),
                        'period_type': 'quarter',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarter_df_period_2),
                        'date_to': fields.Date.to_string(quarter_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_quarter', 'mode': 'range'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_quarter_string(quarter_dt_year_1),
                        'period_type': 'quarter',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarter_df_year_1),
                        'date_to': fields.Date.to_string(quarter_dt_year_1),
                    },
                    {
                        'string': get_quarter_string(quarter_dt_year_2),
                        'period_type': 'quarter',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarter_df_year_2),
                        'date_to': fields.Date.to_string(quarter_dt_year_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_quarter', 'mode': 'range'},
                {
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(quarter_df_year_1),
                    'date_to': fields.Date.to_string(quarter_dt_year_1)},
                [
                    {
                        'string': get_quarter_string(quarter_dt_year_1),
                        'period_type': 'quarter',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarter_df_year_1),
                        'date_to': fields.Date.to_string(quarter_dt_year_1),
                    },
                ],
            )

    def test_filter_date_fiscalyear_range_full_year(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode when the fiscal year ends the 12-31.'''
        def get_year_string(date):
            return date.strftime('%Y')

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            year_df, year_dt = date_utils.get_fiscal_year(fields.Date.today())
            year_df_period_1, year_dt_period_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1))
            year_df_period_2, year_dt_period_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2))
            year_df_year_1, year_dt_year_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1))
            year_df_year_2, year_dt_year_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'string': get_year_string(year_dt),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            self._assert_filter_date(
                {'filter': 'last_year', 'mode': 'range'},
                {
                    'string': get_year_string(year_dt_period_1),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'last_year',
                    'date_from': fields.Date.to_string(year_df_period_1),
                    'date_to': fields.Date.to_string(year_dt_period_1),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_period_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_period_1),
                        'date_to': fields.Date.to_string(year_dt_period_1),
                    },
                    {
                        'string': get_year_string(year_dt_period_2),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_period_2),
                        'date_to': fields.Date.to_string(year_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                    {
                        'string': get_year_string(year_dt_year_2),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_2),
                        'date_to': fields.Date.to_string(year_dt_year_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(year_df_year_1),
                    'date_to': fields.Date.to_string(year_dt_year_1)},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                ],
            )

    def test_filter_date_fiscalyear_range_overlap_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode when the fiscal year overlaps 2 years.'''
        def get_year_string(date):
            return '%s - %s' % (date.year - 1, date.year)

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            self.env.company.fiscalyear_last_day = 30
            self.env.company.fiscalyear_last_month = '6'
            year_df, year_dt = date_utils.get_fiscal_year(fields.Date.today(), day=30, month=6)
            year_df_period_1, year_dt_period_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1), day=30, month=6)
            year_df_period_2, year_dt_period_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2), day=30, month=6)
            year_df_year_1, year_dt_year_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1), day=30, month=6)
            year_df_year_2, year_dt_year_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2), day=30, month=6)

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'string': get_year_string(year_dt),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            self._assert_filter_date(
                {'filter': 'last_year', 'mode': 'range'},
                {
                    'string': get_year_string(year_dt_period_1),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'last_year',
                    'date_from': fields.Date.to_string(year_df_period_1),
                    'date_to': fields.Date.to_string(year_dt_period_1),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_period_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_period_1),
                        'date_to': fields.Date.to_string(year_dt_period_1),
                    },
                    {
                        'string': get_year_string(year_dt_period_2),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_period_2),
                        'date_to': fields.Date.to_string(year_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                    {
                        'string': get_year_string(year_dt_year_2),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_2),
                        'date_to': fields.Date.to_string(year_dt_year_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(year_df_year_1),
                    'date_to': fields.Date.to_string(year_dt_year_1)},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                ],
            )

    def test_filter_date_fiscalyear_range_custom_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode with custom account.fiscal.year records.'''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            # Create a custom fiscal year for the nine previous quarters.
            today = fields.Date.today()
            quarters = []
            for i in range(9):
                quarters.append(date_utils.get_quarter(today - relativedelta(months=i * 3)))
                self.env['account.fiscal.year'].create({
                    'name': 'custom %s' % i,
                    'date_from': fields.Date.to_string(quarters[-1][0]),
                    'date_to': fields.Date.to_string(quarters[-1][1]),
                    'company_id': self.env.company.id,
                })

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'string': 'custom 0',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(quarters[0][0]),
                    'date_to': fields.Date.to_string(quarters[0][1]),
                },
            )

            self._assert_filter_date(
                {'filter': 'last_year', 'mode': 'range'},
                {
                    'string': 'custom 1',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'last_year',
                    'date_from': fields.Date.to_string(quarters[1][0]),
                    'date_to': fields.Date.to_string(quarters[1][1]),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': 'custom 1',
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarters[1][0]),
                        'date_to': fields.Date.to_string(quarters[1][1]),
                    },
                    {
                        'string': 'custom 2',
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarters[2][0]),
                        'date_to': fields.Date.to_string(quarters[2][1]),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': 'custom 4',
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarters[4][0]),
                        'date_to': fields.Date.to_string(quarters[4][1]),
                    },
                    {
                        'string': 'custom 8',
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarters[8][0]),
                        'date_to': fields.Date.to_string(quarters[8][1]),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'range'},
                {
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(quarters[1][0]),
                    'date_to': fields.Date.to_string(quarters[1][1])},
                [
                    {
                        'string': 'custom 1',
                        'period_type': 'fiscalyear',
                        'mode': 'range',
                        'date_from': fields.Date.to_string(quarters[1][0]),
                        'date_to': fields.Date.to_string(quarters[1][1]),
                    },
                ],
            )

    def test_filter_date_custom_range(self):
        ''' Test the filter_date with a custom dates range.'''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': '2018-01-01',
                    'date_to': '2018-01-15',
                },
                {
                    'string': 'From %s\nto  %s' % (format_date(self.env, '2018-01-01'), format_date(self.env, '2018-01-15')),
                    'period_type': 'custom',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': '2018-01-01',
                    'date_to': '2018-01-15',
                },
            )

            self._assert_filter_comparison(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': '2018-01-01',
                    'date_to': '2018-01-15',
                },
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': format_date(self.env, '2017-12-31', date_format='MMM YYYY'),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': '2017-12-01',
                        'date_to': '2017-12-31',
                    },
                    {
                        'string': format_date(self.env, '2017-11-30', date_format='MMM YYYY'),
                        'period_type': 'month',
                        'mode': 'range',
                        'date_from': '2017-11-01',
                        'date_to': '2017-11-30',
                    },
                ],
            )

            self._assert_filter_comparison(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': '2018-01-01',
                    'date_to': '2018-01-15',
                },
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': 'From %s\nto  %s' % (format_date(self.env, '2017-01-01'), format_date(self.env, '2017-01-15')),
                        'period_type': 'custom',
                        'mode': 'range',
                        'date_from': '2017-01-01',
                        'date_to': '2017-01-15',
                    },
                    {
                        'string': 'From %s\nto  %s' % (format_date(self.env, '2016-01-01'), format_date(self.env, '2016-01-15')),
                        'period_type': 'custom',
                        'mode': 'range',
                        'date_from': '2016-01-01',
                        'date_to': '2016-01-15',
                    },
                ],
            )

    def test_filter_date_custom_range_recognition(self):
        ''' Test the period is well recognized when dealing with custom dates range.
        It means date_from = '2018-01-01', date_to = '2018-12-31' must be considered as a full year.
        '''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            today = fields.Date.today()

            month_df, month_dt = date_utils.get_month(today)
            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': fields.Date.to_string(month_df),
                    'date_to': fields.Date.to_string(month_dt),
                },
                {
                    'string': format_date(self.env, fields.Date.to_string(month_dt), date_format='MMM YYYY'),
                    'period_type': 'month',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(month_df),
                    'date_to': fields.Date.to_string(month_dt),
                },
            )

            quarter_df, quarter_dt = date_utils.get_quarter(today)
            quarter_names = get_quarter_names('abbreviated', locale='en_US')
            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
                {
                    'string': u'%s\N{NO-BREAK SPACE}%s' % (quarter_names[date_utils.get_quarter_number(quarter_dt)], quarter_dt.year),
                    'period_type': 'quarter',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
            )

            year_df, year_dt = date_utils.get_fiscal_year(today)
            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
                {
                    'string': year_dt.strftime('%Y'),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            self.env.company.fiscalyear_last_day = 30
            self.env.company.fiscalyear_last_month = '6'
            year_df, year_dt = date_utils.get_fiscal_year(today, day=30, month=6)
            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
                {
                    'string': '%s - %s' % (year_dt.year - 1, year_dt.year),
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            quarter_df, quarter_dt = date_utils.get_quarter(today)
            self.env['account.fiscal.year'].create({
                'name': 'custom 0',
                'date_from': fields.Date.to_string(quarter_df),
                'date_to': fields.Date.to_string(quarter_dt),
                'company_id': self.env.company.id,
            })
            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'range',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
                {
                    'string': 'custom 0',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'filter': 'custom',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
            )

    ####################################################
    # SINGLE DATE
    ####################################################

    def test_filter_date_today_single(self):
        ''' Test the filter_date with 'today' in 'single' mode.'''
        def get_month_string(date):
            return 'As of %s' % (format_date(self.env, fields.Date.to_string(date)))

        frozen_today = datetime.date(2019, 2, 22)
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            today = fields.Date.today()
            month_df, month_dt = date_utils.get_month(today)
            month_df_period_1, month_dt_period_1 = date_utils.get_month(month_dt - relativedelta(months=1))
            month_df_period_2, month_dt_period_2 = date_utils.get_month(month_dt - relativedelta(months=2))
            today_year_1 = today - relativedelta(years=1)
            month_df_year_1, month_dt_year_1 = date_utils.get_month(today_year_1)
            today_year_2 = today - relativedelta(years=2)
            month_df_year_2, month_dt_year_2 = date_utils.get_month(today_year_2)

            self._assert_filter_date(
                {'filter': 'today', 'mode': 'single'},
                {
                    'string': get_month_string(today),
                    'period_type': 'today',
                    'mode': 'single',
                    'filter': 'today',
                    'date_from': fields.Date.to_string(month_df),
                    'date_to': fields.Date.to_string(today),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'today', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_month_string(month_dt_period_1),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_period_1),
                        'date_to': fields.Date.to_string(month_dt_period_1),
                    },
                    {
                        'string': get_month_string(month_dt_period_2),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_period_2),
                        'date_to': fields.Date.to_string(month_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'today', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_month_string(today_year_1),
                        'period_type': 'today',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_year_1),
                        'date_to': fields.Date.to_string(today_year_1),
                    },
                    {
                        'string': get_month_string(today_year_2),
                        'period_type': 'today',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_year_2),
                        'date_to': fields.Date.to_string(today_year_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'today', 'mode': 'single'},
                {
                    'filter': 'custom',
                    'date_to': fields.Date.to_string(month_dt_year_1)},
                [
                    {
                        'string': get_month_string(month_dt_year_1),
                        'period_type': 'custom',
                        'mode': 'single',
                        'date_from': False,
                        'date_to': fields.Date.to_string(month_dt_year_1),
                    },
                ],
            )

    def test_filter_date_month_single(self):
        ''' Test the filter_date with 'this_month'/'last_month' in 'single' mode.'''
        def get_month_string(date):
            return 'As of %s' % (format_date(self.env, fields.Date.to_string(date)))

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            month_df, month_dt = date_utils.get_month(fields.Date.today())
            month_df_period_1, month_dt_period_1 = date_utils.get_month(month_dt - relativedelta(months=1))
            month_df_period_2, month_dt_period_2 = date_utils.get_month(month_dt - relativedelta(months=2))
            month_df_year_1, month_dt_year_1 = date_utils.get_month(month_dt - relativedelta(years=1))
            month_df_year_2, month_dt_year_2 = date_utils.get_month(month_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_month', 'mode': 'single'},
                {
                    'string': get_month_string(month_dt),
                    'period_type': 'month',
                    'mode': 'single',
                    'filter': 'this_month',
                    'date_from': fields.Date.to_string(month_df),
                    'date_to': fields.Date.to_string(month_dt),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_month', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_month_string(month_dt_period_1),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_period_1),
                        'date_to': fields.Date.to_string(month_dt_period_1),
                    },
                    {
                        'string': get_month_string(month_dt_period_2),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_period_2),
                        'date_to': fields.Date.to_string(month_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_month', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_month_string(month_dt_year_1),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_year_1),
                        'date_to': fields.Date.to_string(month_dt_year_1),
                    },
                    {
                        'string': get_month_string(month_dt_year_2),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(month_df_year_2),
                        'date_to': fields.Date.to_string(month_dt_year_2),
                    },
                ],
            )

    def test_filter_date_quarter_single(self):
        ''' Test the filter_date with 'this_quarter'/'last_quarter' in 'single' mode.'''
        def get_quarter_string(date):
            return 'As of %s' % (format_date(self.env, fields.Date.to_string(date)))

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            quarter_df, quarter_dt = date_utils.get_quarter(fields.Date.today())
            quarter_df_period_1, quarter_dt_period_1 = date_utils.get_quarter(quarter_dt - relativedelta(months=3))
            quarter_df_period_2, quarter_dt_period_2 = date_utils.get_quarter(quarter_dt - relativedelta(months=6))
            quarter_df_year_1, quarter_dt_year_1 = date_utils.get_quarter(quarter_dt - relativedelta(years=1))
            quarter_df_year_2, quarter_dt_year_2 = date_utils.get_quarter(quarter_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_quarter', 'mode': 'single'},
                {
                    'string': get_quarter_string(quarter_dt),
                    'period_type': 'quarter',
                    'mode': 'single',
                    'filter': 'this_quarter',
                    'date_from': fields.Date.to_string(quarter_df),
                    'date_to': fields.Date.to_string(quarter_dt),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_quarter', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_quarter_string(quarter_dt_period_1),
                        'period_type': 'quarter',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarter_df_period_1),
                        'date_to': fields.Date.to_string(quarter_dt_period_1),
                    },
                    {
                        'string': get_quarter_string(quarter_dt_period_2),
                        'period_type': 'quarter',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarter_df_period_2),
                        'date_to': fields.Date.to_string(quarter_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_quarter', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_quarter_string(quarter_dt_year_1),
                        'period_type': 'quarter',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarter_df_year_1),
                        'date_to': fields.Date.to_string(quarter_dt_year_1),
                    },
                    {
                        'string': get_quarter_string(quarter_dt_year_2),
                        'period_type': 'quarter',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarter_df_year_2),
                        'date_to': fields.Date.to_string(quarter_dt_year_2),
                    },
                ],
            )

    def test_filter_date_fiscalyear_single_full_year(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode when the fiscal year ends the 12-31.'''
        def get_year_string(date):
            return 'As of %s' % (format_date(self.env, fields.Date.to_string(date)))

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            year_df, year_dt = date_utils.get_fiscal_year(fields.Date.today())
            year_df_period_1, year_dt_period_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1))
            year_df_period_2, year_dt_period_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2))
            year_df_year_1, year_dt_year_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1))
            year_df_year_2, year_dt_year_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2))

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'single'},
                {
                    'string': get_year_string(year_dt),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_period_1),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_period_1),
                        'date_to': fields.Date.to_string(year_dt_period_1),
                    },
                    {
                        'string': get_year_string(year_dt_period_2),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_period_2),
                        'date_to': fields.Date.to_string(year_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                    {
                        'string': get_year_string(year_dt_year_2),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_year_2),
                        'date_to': fields.Date.to_string(year_dt_year_2),
                    },
                ],
            )

    def test_filter_date_fiscalyear_single_overlap_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode when the fiscal year overlaps 2 years.'''
        def get_year_string(date):
            return 'As of %s' % (format_date(self.env, fields.Date.to_string(date)))

        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            self.env.company.fiscalyear_last_day = 30
            self.env.company.fiscalyear_last_month = '6'
            year_df, year_dt = date_utils.get_fiscal_year(fields.Date.today(), day=30, month=6)
            year_df_period_1, year_dt_period_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1), day=30, month=6)
            year_df_period_2, year_dt_period_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2), day=30, month=6)
            year_df_year_1, year_dt_year_1 = date_utils.get_fiscal_year(year_dt - relativedelta(years=1), day=30, month=6)
            year_df_year_2, year_dt_year_2 = date_utils.get_fiscal_year(year_dt - relativedelta(years=2), day=30, month=6)

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'single'},
                {
                    'string': get_year_string(year_dt),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(year_df),
                    'date_to': fields.Date.to_string(year_dt),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_period_1),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_period_1),
                        'date_to': fields.Date.to_string(year_dt_period_1),
                    },
                    {
                        'string': get_year_string(year_dt_period_2),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_period_2),
                        'date_to': fields.Date.to_string(year_dt_period_2),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': get_year_string(year_dt_year_1),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_year_1),
                        'date_to': fields.Date.to_string(year_dt_year_1),
                    },
                    {
                        'string': get_year_string(year_dt_year_2),
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(year_df_year_2),
                        'date_to': fields.Date.to_string(year_dt_year_2),
                    },
                ],
            )

    def test_filter_date_fiscalyear_single_custom_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode with custom account.fiscal.year records.'''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            # Create a custom fiscal year for the nine previous quarters.
            today = fields.Date.today()
            quarters = []
            for i in range(9):
                quarters.append(date_utils.get_quarter(today - relativedelta(months=i * 3)))
                self.env['account.fiscal.year'].create({
                    'name': 'custom %s' % i,
                    'date_from': fields.Date.to_string(quarters[-1][0]),
                    'date_to': fields.Date.to_string(quarters[-1][1]),
                    'company_id': self.env.company.id,
                })

            self._assert_filter_date(
                {'filter': 'this_year', 'mode': 'single'},
                {
                    'string': 'custom 0',
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'filter': 'this_year',
                    'date_from': fields.Date.to_string(quarters[0][0]),
                    'date_to': fields.Date.to_string(quarters[0][1]),
                },
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': 'custom 1',
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarters[1][0]),
                        'date_to': fields.Date.to_string(quarters[1][1]),
                    },
                    {
                        'string': 'custom 2',
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarters[2][0]),
                        'date_to': fields.Date.to_string(quarters[2][1]),
                    },
                ],
            )

            self._assert_filter_comparison(
                {'filter': 'this_year', 'mode': 'single'},
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': 'custom 4',
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarters[4][0]),
                        'date_to': fields.Date.to_string(quarters[4][1]),
                    },
                    {
                        'string': 'custom 8',
                        'period_type': 'fiscalyear',
                        'mode': 'single',
                        'date_from': fields.Date.to_string(quarters[8][0]),
                        'date_to': fields.Date.to_string(quarters[8][1]),
                    },
                ],
            )

    def test_filter_date_custom_single(self):
        ''' Test the filter_date with a custom date in 'single' mode.'''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):

            self._assert_filter_date(
                {
                    'filter': 'custom',
                    'mode': 'single',
                    'date_to': '2018-01-15',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2018-01-15'),
                    'period_type': 'custom',
                    'mode': 'single',
                    'filter': 'custom',
                    'date_from': '2018-01-01',
                    'date_to': '2018-01-15',
                },
            )

            self._assert_filter_comparison(
                {
                    'filter': 'custom',
                    'mode': 'single',
                    'date_to': '2018-01-15',
                },
                {'filter': 'previous_period', 'number_period': 2},
                [
                    {
                        'string': 'As of %s' % format_date(self.env, '2017-12-31'),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': '2017-12-01',
                        'date_to': '2017-12-31',
                    },
                    {
                        'string': 'As of %s' % format_date(self.env, '2017-11-30'),
                        'period_type': 'month',
                        'mode': 'single',
                        'date_from': '2017-11-01',
                        'date_to': '2017-11-30',
                    },
                ],
            )

            self._assert_filter_comparison(
                {
                    'filter': 'custom',
                    'mode': 'single',
                    'date_to': '2018-01-15',
                },
                {'filter': 'same_last_year', 'number_period': 2},
                [
                    {
                        'string': 'As of %s' % format_date(self.env, '2017-01-15'),
                        'period_type': 'custom',
                        'mode': 'single',
                        'date_from': '2017-01-01',
                        'date_to': '2017-01-15',
                    },
                    {
                        'string': 'As of %s' % format_date(self.env, '2016-01-15'),
                        'period_type': 'custom',
                        'mode': 'single',
                        'date_from': '2016-01-01',
                        'date_to': '2016-01-15',
                    },
                ],
            )
