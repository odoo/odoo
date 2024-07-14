# -*- coding: utf-8 -*-
# pylint: disable=C0326
import odoo.tests

from odoo.tests import tagged
from odoo import Command, fields
from .common import TestAccountReportsCommon
from odoo.tools import date_utils
from odoo.tools.misc import formatLang, format_date

from dateutil.relativedelta import relativedelta
from unittest.mock import patch
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestAccountReportsFilters(TestAccountReportsCommon, odoo.tests.HttpCase):

    def _assert_filter_date(self, report, previous_options, expected_date_values):
        """ Initializes and checks the 'date' option computed for the provided report and previous_options
        """
        options = report.get_options(previous_options)
        self.assertDictEqual(options['date'], expected_date_values)

    def _assert_filter_comparison(self, report, previous_options, expected_period_values):
        """ Initializes and checks the 'comparison' option computed for the provided report and previous_options
        """
        options = report.get_options(previous_options)

        self.assertEqual(len(options['comparison']['periods']), len(expected_period_values))

        for i, expected_values in enumerate(expected_period_values):
            self.assertDictEqual(options['comparison']['periods'][i], expected_values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.single_date_report = cls.env['account.report'].create({
            'name': "Single Date Report",
            'filter_period_comparison': True,
            'filter_date_range': False,
        })

        cls.date_range_report = cls.env['account.report'].create({
            'name': "Date Range Report",
            'filter_period_comparison': True,
        })

    ####################################################
    # DATES RANGE
    ####################################################

    @freeze_time('2017-12-31')
    def test_filter_date_month_range(self):
        ''' Test the filter_date with 'this_month'/'last_month' in 'range' mode.'''
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'this_month', 'mode': 'range'}},
            {
                'string': 'Dec 2017',
                'period_type': 'month',
                'mode': 'range',
                'filter': 'this_month',
                'date_from': '2017-12-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'last_month', 'mode': 'range'}},
            {
                'string': 'Nov 2017',
                'period_type': 'month',
                'mode': 'range',
                'filter': 'last_month',
                'date_from': '2017-11-01',
                'date_to': '2017-11-30',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_month', 'mode': 'range'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'Nov 2017',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2017-11-01',
                    'date_to': '2017-11-30',
                },
                {
                    'string': 'Oct 2017',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2017-10-01',
                    'date_to': '2017-10-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_month', 'mode': 'range'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'Dec 2016',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2016-12-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'Dec 2015',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2015-12-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_month', 'mode': 'range'}, 'comparison':{'filter': 'custom', 'date_from': '2016-12-01', 'date_to': '2016-12-31'}},
            [
                {
                    'string': 'Dec 2016',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2016-12-01',
                    'date_to': '2016-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_quarter_range(self):
        ''' Test the filter_date with 'this_quarter'/'last_quarter' in 'range' mode.'''
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'this_quarter', 'mode': 'range'}},
            {
                'string': 'Q4\N{NO-BREAK SPACE}2017',
                'period_type': 'quarter',
                'mode': 'range',
                'filter': 'this_quarter',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'last_quarter', 'mode': 'range'}},
            {
                'string': 'Q3\N{NO-BREAK SPACE}2017',
                'period_type': 'quarter',
                'mode': 'range',
                'filter': 'last_quarter',
                'date_from': '2017-07-01',
                'date_to': '2017-09-30',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_quarter', 'mode': 'range'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'Q3\N{NO-BREAK SPACE}2017',
                    'period_type': 'quarter',
                    'mode': 'range',
                    'date_from': '2017-07-01',
                    'date_to': '2017-09-30',
                },
                {
                    'string': 'Q2\N{NO-BREAK SPACE}2017',
                    'period_type': 'quarter',
                    'mode': 'range',
                    'date_from': '2017-04-01',
                    'date_to': '2017-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_quarter', 'mode': 'range'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'Q4\N{NO-BREAK SPACE}2016',
                    'period_type': 'quarter',
                    'mode': 'range',
                    'date_from': '2016-10-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'Q4\N{NO-BREAK SPACE}2015',
                    'period_type': 'quarter',
                    'mode': 'range',
                    'date_from': '2015-10-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_quarter', 'mode': 'range'}, 'comparison': {'filter': 'custom', 'date_from': '2016-10-01', 'date_to': '2016-12-31'}},
            [
                {
                    'string': 'Q4\N{NO-BREAK SPACE}2016',
                    'period_type': 'quarter',
                    'mode': 'range',
                    'date_from': '2016-10-01',
                    'date_to': '2016-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_range_full_year(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode when the fiscal year ends the 12-31.'''
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}},
            {
                'string': '2017',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'this_year',
                'date_from': '2017-01-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'last_year', 'mode': 'range'}},
            {
                'string': '2016',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'last_year',
                'date_from': '2016-01-01',
                'date_to': '2016-12-31',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': '2016',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': '2015',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': '2016',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': '2015',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'custom', 'date_from': '2016-01-01', 'date_to': '2016-12-31'}},
            [
                {
                    'string': '2016',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_range_overlap_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode when the fiscal year overlaps 2 years.'''
        self.env.company.fiscalyear_last_day = 30
        self.env.company.fiscalyear_last_month = '6'

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}},
            {
                'string': '2017 - 2018',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'this_year',
                'date_from': '2017-07-01',
                'date_to': '2018-06-30',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'last_year', 'mode': 'range'}},
            {
                'string': '2016 - 2017',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'last_year',
                'date_from': '2016-07-01',
                'date_to': '2017-06-30',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': '2016 - 2017',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-07-01',
                    'date_to': '2017-06-30',
                },
                {
                    'string': '2015 - 2016',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2015-07-01',
                    'date_to': '2016-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': '2016 - 2017',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-07-01',
                    'date_to': '2017-06-30',
                },
                {
                    'string': '2015 - 2016',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2015-07-01',
                    'date_to': '2016-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'custom', 'date_from': '2016-07-01', 'date_to': '2017-06-30'}},
            [
                {
                    'string': '2016 - 2017',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-07-01',
                    'date_to': '2017-06-30',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_range_custom_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'range' mode with custom account.fiscal.year records.'''
        # Create a custom fiscal year for the nine previous quarters.
        today = fields.Date.from_string('2017-12-31')
        for i in range(9):
            quarter_df, quarter_dt = date_utils.get_quarter(today - relativedelta(months=i * 3))
            self.env['account.fiscal.year'].create({
                'name': 'custom %s' % i,
                'date_from': fields.Date.to_string(quarter_df),
                'date_to': fields.Date.to_string(quarter_dt),
                'company_id': self.env.company.id,
            })

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}},
            {
                'string': 'custom 0',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'this_year',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'last_year', 'mode': 'range'}},
            {
                'string': 'custom 1',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'last_year',
                'date_from': '2017-07-01',
                'date_to': '2017-09-30',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'custom 1',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2017-07-01',
                    'date_to': '2017-09-30',
                },
                {
                    'string': 'custom 2',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2017-04-01',
                    'date_to': '2017-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'custom 4',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2016-10-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'custom 8',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2015-10-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
        self.date_range_report,
            {'date': {'filter': 'this_year', 'mode': 'range'}, 'comparison': {'filter': 'custom', 'date_from': '2017-07-01', 'date_to': '2017-09-30'}},
            [
                {
                    'string': 'custom 1',
                    'period_type': 'fiscalyear',
                    'mode': 'range',
                    'date_from': '2017-07-01',
                    'date_to': '2017-09-30',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_custom_range(self):
        ''' Test the filter_date with a custom dates range.'''
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-01-01', 'date_to': '2017-01-15'}},
            {
                'string': 'From %s\nto  %s' % (format_date(self.env, '2017-01-01'), format_date(self.env, '2017-01-15')),
                'period_type': 'custom',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2017-01-01',
                'date_to': '2017-01-15',
            },
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {
                'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-01-01', 'date_to': '2017-01-15'},
                'comparison': {'filter': 'previous_period', 'number_period': 2},
            },
            [
                {
                    'string': 'Dec 2016',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2016-12-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'Nov 2016',
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': '2016-11-01',
                    'date_to': '2016-11-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.date_range_report,
            {
                'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-01-01', 'date_to': '2017-01-15'},
                'comparison': {'filter': 'same_last_year', 'number_period': 2},
            },
            [
                {
                    'string': 'From %s\nto  %s' % (format_date(self.env, '2016-01-01'), format_date(self.env, '2016-01-15')),
                    'period_type': 'custom',
                    'mode': 'range',
                    'date_from': '2016-01-01',
                    'date_to': '2016-01-15',
                },
                {
                    'string': 'From %s\nto  %s' % (format_date(self.env, '2015-01-01'), format_date(self.env, '2015-01-15')),
                    'period_type': 'custom',
                    'mode': 'range',
                    'date_from': '2015-01-01',
                    'date_to': '2015-01-15',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_custom_range_recognition(self):
        ''' Test the period is well recognized when dealing with custom dates range.
        It means date_from = '2018-01-01', date_to = '2018-12-31' must be considered as a full year.
        '''
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-12-01', 'date_to': '2017-12-31'}},
            {
                'string': 'Dec 2017',
                'period_type': 'month',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2017-12-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-10-01', 'date_to': '2017-12-31'}},
            {
                'string': 'Q4\N{NO-BREAK SPACE}2017',
                'period_type': 'quarter',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-01-01', 'date_to': '2017-12-31'}},
            {
                'string': '2017',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2017-01-01',
                'date_to': '2017-12-31',
            },
        )

        self.env.company.fiscalyear_last_day = 30
        self.env.company.fiscalyear_last_month = '6'
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2016-07-01', 'date_to': '2017-06-30'}},
            {
                'string': '2016 - 2017',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2016-07-01',
                'date_to': '2017-06-30',
            },
        )

        self.env['account.fiscal.year'].create({
            'name': 'custom 0',
            'date_from': '2017-10-01',
            'date_to': '2017-12-31',
            'company_id': self.env.company.id,
        })
        self._assert_filter_date(
            self.date_range_report,
            {'date': {'filter': 'custom', 'mode': 'range', 'date_from': '2017-10-01', 'date_to': '2017-12-31'}},
            {
                'string': 'custom 0',
                'period_type': 'fiscalyear',
                'mode': 'range',
                'filter': 'custom',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

    ####################################################
    # SINGLE DATE
    ####################################################

    @freeze_time('2017-12-30')
    def test_filter_date_today_single(self):
        ''' Test the filter_date with 'today' in 'single' mode.'''
        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'today', 'mode': 'single'}},
            {
                'string': 'As of %s' % format_date(self.env, '2017-12-30'),
                'period_type': 'today',
                'mode': 'single',
                'filter': 'today',
                'date_from': '2017-01-01',
                'date_to': '2017-12-30',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'today', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'today', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-30'),
                    'period_type': 'today',
                    'mode': 'single',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-30'),
                    'period_type': 'today',
                    'mode': 'single',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'today', 'mode': 'single'}, 'comparison': {'filter': 'custom', 'date_to': '2016-12-31'}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'custom',
                    'mode': 'single',
                    'date_from': False,
                    'date_to': '2016-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_month_single(self):
        ''' Test the filter_date with 'this_month'/'last_month' in 'single' mode.'''
        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'this_month', 'mode': 'single'}},
            {
                'string': 'As of %s' % format_date(self.env, '2017-12-31'),
                'period_type': 'month',
                'mode': 'single',
                'filter': 'this_month',
                'date_from': '2017-12-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_month', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2017-11-30'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2017-11-01',
                    'date_to': '2017-11-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2017-10-31'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2017-10-01',
                    'date_to': '2017-10-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_month', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2016-12-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-31'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2015-12-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_quarter_single(self):
        ''' Test the filter_date with 'this_quarter'/'last_quarter' in 'single' mode.'''
        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'this_quarter', 'mode': 'single'}},
            {
                'string': 'As of %s' % format_date(self.env, '2017-12-31'),
                'period_type': 'quarter',
                'mode': 'single',
                'filter': 'this_quarter',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_quarter', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2017-09-30'),
                    'period_type': 'quarter',
                    'mode': 'single',
                    'date_from': '2017-07-01',
                    'date_to': '2017-09-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2017-06-30'),
                    'period_type': 'quarter',
                    'mode': 'single',
                    'date_from': '2017-04-01',
                    'date_to': '2017-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_quarter', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'quarter',
                    'mode': 'single',
                    'date_from': '2016-10-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-31'),
                    'period_type': 'quarter',
                    'mode': 'single',
                    'date_from': '2015-10-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_single_full_year(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode when the fiscal year ends the 12-31.'''
        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}},
            {
                'string': 'As of %s' % format_date(self.env, '2017-12-31'),
                'period_type': 'fiscalyear',
                'mode': 'single',
                'filter': 'this_year',
                'date_from': '2017-01-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2016-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-01-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2015-12-31'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-01-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_single_overlap_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode when the fiscal year overlaps 2 years.'''
        self.env.company.fiscalyear_last_day = 30
        self.env.company.fiscalyear_last_month = '6'

        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}},
            {
                'string': 'As of %s' % format_date(self.env, '2018-06-30'),
                'period_type': 'fiscalyear',
                'mode': 'single',
                'filter': 'this_year',
                'date_from': '2017-07-01',
                'date_to': '2018-06-30',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2017-06-30'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-07-01',
                    'date_to': '2017-06-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2016-06-30'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-07-01',
                    'date_to': '2016-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2017-06-30'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-07-01',
                    'date_to': '2017-06-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2016-06-30'),
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-07-01',
                    'date_to': '2016-06-30',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_fiscalyear_single_custom_years(self):
        ''' Test the filter_date with 'this_year'/'last_year' in 'single' mode with custom account.fiscal.year records.'''
        # Create a custom fiscal year for the nine previous quarters.
        today = fields.Date.from_string('2017-12-31')
        for i in range(9):
            quarter_df, quarter_dt = date_utils.get_quarter(today - relativedelta(months=i * 3))
            self.env['account.fiscal.year'].create({
                'name': 'custom %s' % i,
                'date_from': fields.Date.to_string(quarter_df),
                'date_to': fields.Date.to_string(quarter_dt),
                'company_id': self.env.company.id,
            })

        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}},
            {
                'string': 'custom 0',
                'period_type': 'fiscalyear',
                'mode': 'single',
                'filter': 'this_year',
                'date_from': '2017-10-01',
                'date_to': '2017-12-31',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'custom 1',
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2017-07-01',
                    'date_to': '2017-09-30',
                },
                {
                    'string': 'custom 2',
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2017-04-01',
                    'date_to': '2017-06-30',
                },
            ],
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'this_year', 'mode': 'single'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
            [
                {
                    'string': 'custom 4',
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2016-10-01',
                    'date_to': '2016-12-31',
                },
                {
                    'string': 'custom 8',
                    'period_type': 'fiscalyear',
                    'mode': 'single',
                    'date_from': '2015-10-01',
                    'date_to': '2015-12-31',
                },
            ],
        )

    @freeze_time('2017-12-31')
    def test_filter_date_custom_single(self):
        ''' Test the filter_date with a custom date in 'single' mode.'''
        self._assert_filter_date(
            self.single_date_report,
            {'date': {'filter': 'custom', 'mode': 'single', 'date_to': '2018-01-15'}},
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
            self.single_date_report,
            {'date': {'filter': 'custom', 'mode': 'single', 'date_to': '2018-01-15'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
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
            self.single_date_report,
            {'date': {'filter': 'custom', 'mode': 'single', 'date_to': '2018-01-15'}, 'comparison': {'filter': 'same_last_year', 'number_period': 2}},
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

    @freeze_time('2021-09-01')
    def test_filter_date_custom_single_period_type_month(self):
        ''' Test the filter_date with a custom date in 'single' mode.'''
        self._assert_filter_date(
            self.single_date_report,
            {
                'date': {
                    'period_type': 'today',
                    'mode': 'single',
                    'date_from': '2021-09-01',
                    'date_to': '2019-07-18',
                    'filter': 'custom',
                }
            },
            {
                'string': 'As of %s' % format_date(self.env, '2019-07-18'),
                'period_type': 'custom',
                'mode': 'single',
                'filter': 'custom',
                'date_from': '2019-07-01',
                'date_to': '2019-07-18',
            },
        )

        self._assert_filter_comparison(
            self.single_date_report,
            {'date': {'filter': 'custom', 'mode': 'single', 'date_to': '2019-07-18'}, 'comparison': {'filter': 'previous_period', 'number_period': 2}},
            [
                {
                    'string': 'As of %s' % format_date(self.env, '2019-06-30'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2019-06-01',
                    'date_to': '2019-06-30',
                },
                {
                    'string': 'As of %s' % format_date(self.env, '2019-05-31'),
                    'period_type': 'month',
                    'mode': 'single',
                    'date_from': '2019-05-01',
                    'date_to': '2019-05-31',
                },
            ],
        )

    ####################################################
    # User Defined Filters on Journal Items
    ####################################################

    @freeze_time('2023-09-01')
    def test_filter_aml_ir_filters(self):
        # Test user-defined filter set on journal items used as report options

        filter_record = self.env['ir.filters'].create({
            'model_id': 'account.move.line',
            'user_id': self.uid,
            'name': 'To Check',
            'domain': '[("move_id.to_check", "=", True)]',
        })

        report = self.env['account.report'].create({
            'name': 'Test ir filters',
            'filter_aml_ir_filters': True,
            'root_report_id': self.env.ref("account_reports.profit_and_loss").id,
            'column_ids': [
                Command.create({
                    'name': 'Balance',
                    'expression_label': 'balance',
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': 'Line 1',
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'engine': 'domain',
                            'formula': '[("account_id.account_type", "=", "income")]',
                            'subformula': '-sum',
                        }),
                    ],
                }),
            ],
        })

        moves = (
                self.init_invoice("out_invoice", self.partner_a, "2023-09-01", amounts=[1000])
                + self.init_invoice("out_invoice", self.partner_a, "2023-09-01", amounts=[1000])
        )
        moves[0].to_check = True
        moves.action_post()

        options = self._generate_options(report, '2023-01-01', '2023-12-31')

        for opt in options['aml_ir_filters']:
            if opt['id'] == filter_record.id:
                opt['selected'] = True
                break

        # Ensure that only the move with the 'to_check' attribute is included in the report
        self.assertLinesValues(
            report._get_lines(options),
            #      Name   Balance
            [       0,      1],
            [
                ('Line 1', 1000)
            ],
            options
        )

    def test_hide_line_at_0_tour(self):
        report = self.env.ref('account_reports.balance_sheet')
        report.filter_hide_0_lines = 'optional'
        self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2020-0%s-15' % i,
            'invoice_date': '2020-0%s-15' % i,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        } for i in range(1, 4)]).action_post()

        self.start_tour("/web", 'account_reports_hide_0_lines', login=self.env.user.login)

    def test_rounding_unit_tour(self):
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000000.0,
                'tax_ids': [Command.set(self.tax_sale_a.ids)],
            })],
        }).action_post()

        self.start_tour("/web", 'account_reports_rounding_unit', login=self.env.user.login)

    def test_filter_multi_company(self):
        def _check_company_filter(allowed_companies, expected_companies, message=None, match_active=True):
            options = self.single_date_report.with_context(allowed_company_ids=allowed_companies.ids).get_options()
            computed_company_ids = self.env['account.report'].get_report_company_ids(options)
            if match_active:
                # Active company should match
                self.assertEqual(computed_company_ids[0], expected_companies[0].id, message)
            # Selected companies should match, whatever their order
            self.assertEqual(set(computed_company_ids), set(expected_companies.ids), message)

        main_company = self.company_data['company']
        main_company.vat = '123'
        branch_1 = self.env['res.company'].create({'name': "Branch 1", 'parent_id': main_company.id, 'vat': '123'})
        branch_1_1 = self.env['res.company'].create({'name': "Branch 1 sub-branch 1", 'parent_id': branch_1.id})
        branch_1_2 = self.env['res.company'].create({'name': "Branch 1 sub-branch 2", 'parent_id': branch_1.id, 'vat': '123'})
        branch_2 = self.env['res.company'].create({'name': "Branch 2", 'parent_id': main_company.id})
        branch_2_1 = self.env['res.company'].create({'name': "Branch 2 sub-branch 1", 'parent_id': branch_2.id})
        other_company = self.env['res.company'].create({'name': "Other company"})

        # Test 'disabled' filter, as well as 'tax_units' when no tax unit is defined and VAT is shared (they should behave in the same way)
        for company_filter in ('disabled', 'tax_units'):
            self.single_date_report.filter_multi_company = company_filter

            _check_company_filter(
                main_company + branch_1 + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
                main_company + branch_1 + branch_1_1 + branch_1_2 + branch_2 + branch_2_1,
                "The main company and all of its sub-branches should be selected",
            )
            _check_company_filter(
                branch_1 + main_company + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
                branch_1 + branch_1_1 + branch_1_2,
                "When the active company is a branch of another active company, it should only be selected with its sub-branches.",
            )
            _check_company_filter(
                main_company + branch_1 + branch_1_2 + branch_2_1 + other_company,
                main_company + branch_1 + branch_1_2 + branch_2_1,
                "Choosing a subset of branches in the company selector should keep that selection in the report.",
            )

        # Test 'selector' filter
        self.single_date_report.filter_multi_company = 'selector'

        _check_company_filter(
            branch_1,
            branch_1,
        )
        _check_company_filter(
            main_company + branch_1 + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
            main_company + branch_1 + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
        )
        _check_company_filter(
            branch_1 + main_company + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
            branch_1 + main_company + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
        )
        _check_company_filter(
            main_company + branch_1_1 + branch_1_2 + branch_2 + other_company,
            main_company + branch_1_1 + branch_1_2 + branch_2 + other_company,
        )

        # Test 'tax_units' filter, with no tax unit, and non-shared VAT numbers
        self.single_date_report.filter_multi_company = 'tax_units'
        branch_1_1.vat = '456'
        branch_2.vat = '789'

        _check_company_filter(
            main_company + branch_1_1 + branch_1_2 + branch_2 + branch_2_1 + other_company,
            main_company + branch_1_2,
            "Only the current company and its sub-branches sharing its vat number should be selected.",
        )

        _check_company_filter(
            branch_2 + main_company + branch_1_1 + branch_1_2  + branch_2_1 + other_company,
            branch_2 + branch_2_1,
            "Only the current company and its sub-branches sharing its vat number should be selected.",
        )

        # Test 'tax_units' filter, with an existing tax unit object
        self.single_date_report.availability_condition = 'country'
        self.single_date_report.country_id = self.env.ref('base.be')

        tax_unit = self.env['account.tax.unit'].create({
            'name': "Test Tax Unit",
            'country_id': self.single_date_report.country_id.id,
            'vat': 'BE0477472701',
            'company_ids': (main_company + branch_1_1 + branch_1_2 + branch_2 + other_company).ids,
            'main_company_id': main_company.id,
        })

        _check_company_filter(
            other_company + main_company + branch_1_1 + branch_1_2 + branch_2,
            other_company + main_company + branch_1_1 + branch_1_2 + branch_2,
            "Opening the report with a company selector matching the content of the tax unit should select this tax unit, keeping the companies.",
            match_active=False,
        )

        _check_company_filter(
            tax_unit.company_ids + branch_2_1,
            main_company + branch_1_2,
            "Opening the report with a company selector matching more than the content of the tax unit should not select the tax unit, "
            "but take the accessible branches with the same VAT number as the active company.",
        )

        _check_company_filter(
            main_company + branch_1_1 + branch_1_2 + branch_2,
            main_company + branch_1_2,
            "Opening the report with a company selector matching less than the content of the tax unit should select the active sub-branches "
            "with the same VAT as the active company.",
        )

        # Test 'tax_units' filter, with no tax unit, and no VAT number on branches (only one on main company)
        branch_1.vat = None
        branch_1_1.vat = None
        branch_1_2.vat = None
        branch_2.vat = None

        _check_company_filter(
            branch_2 + branch_2_1,
            branch_2 + branch_2_1,
            "When no VAT exists in the hierarchy; all companies should be considered as sharing the same VAT, and active companies should be kept.",
        )

        _check_company_filter(
            branch_2_1 + branch_2,
            branch_2_1 + branch_2,
            "When no VAT exists in the hierarchy; all companies should be considered as sharing the same VAT, and active companies should be kept.",
        )
