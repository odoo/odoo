# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import odoo.tests

from datetime import datetime


@odoo.tests.tagged('post_install', '-at_install')
class TestFiscalPosition(AccountingTestCase):

    def check_compute_fiscal_year(self, company, date, expected_date_from, expected_date_to):
        '''Compute the fiscal year at a certain date for the company passed as parameter.
        Then, check if the result matches the 'expected_date_from'/'expected_date_to' dates.

        :param company: The company.
        :param date: The date belonging to the fiscal year.
        :param expected_date_from: The expected date_from after computation.
        :param expected_date_to: The expected date_to after computation.
        '''
        current_date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        res = company.compute_fiscalyear_dates(current_date)
        self.assertEqual(res['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT), expected_date_from)
        self.assertEqual(res['date_to'].strftime(DEFAULT_SERVER_DATE_FORMAT), expected_date_to)

    def test_default_fiscal_year(self):
        '''Basic case with a fiscal year xxxx-01-01 - xxxx-12-31.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        self.check_compute_fiscal_year(
            company,
            '2017-12-31',
            '2017-01-01',
            '2017-12-31',
        )

        self.check_compute_fiscal_year(
            company,
            '2017-01-01',
            '2017-01-01',
            '2017-12-31',
        )

    def test_leap_fiscal_year_1(self):
        '''Case with a leap year ending the 29 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 29
        company.fiscalyear_last_month = 2

        self.check_compute_fiscal_year(
            company,
            '2016-02-29',
            '2015-03-01',
            '2016-02-29',
        )

    def test_leap_fiscal_year_2(self):
        '''Case with a next leap year ending the 29 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 29
        company.fiscalyear_last_month = 2

        self.check_compute_fiscal_year(
            company,
            '2015-03-01',
            '2015-03-01',
            '2016-02-29',
        )

    def test_leap_fiscal_year_3(self):
        '''Case with a leap year ending the 28 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 28
        company.fiscalyear_last_month = 2

        self.check_compute_fiscal_year(
            company,
            '2016-03-01',
            '2016-02-29',
            '2017-02-28',
        )

    def test_custom_fiscal_year_1(self):
        '''Case with a custom fiscal year covering the six first months of the year.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        self.env['account.fiscal.year'].create({
            'name': '6 month 2017',
            'date_from': '2017-01-01',
            'date_to': '2017-05-31',
            'company_id': company.id,
        })

        self.check_compute_fiscal_year(
            company,
            '2017-11-01',
            '2017-06-01',
            '2017-12-31',
        )

    def test_custom_fiscal_year_2(self):
        '''Case with a date included in a custom fiscal year.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        self.env['account.fiscal.year'].create({
            'name': '6 month 2017',
            'date_from': '2017-01-01',
            'date_to': '2017-05-31',
            'company_id': company.id,
        })

        self.check_compute_fiscal_year(
            company,
            '2017-02-01',
            '2017-01-01',
            '2017-05-31',
        )

    def test_custom_fiscal_year_3(self):
        '''Case with a date in a gap between two custom fiscal years.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        self.env['account.fiscal.year'].create({
            'name': '6 month 2017',
            'date_from': '2017-01-01',
            'date_to': '2017-05-31',
            'company_id': company.id,
        })

        self.env['account.fiscal.year'].create({
            'name': 'last 3 month 2017',
            'date_from': '2017-10-01',
            'date_to': '2017-12-31',
            'company_id': company.id,
        })

        self.check_compute_fiscal_year(
            company,
            '2017-07-01',
            '2017-06-01',
            '2017-09-30',
        )
