# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase

from odoo import fields

class TestFiscalPosition(AccountingTestCase):

    def check_compute_fiscal_year(self, company, date, expected_date_from, expected_date_to):
        '''Compute the fiscal year at a certain date for the company passed as parameter.
        Then, check if the result matches the 'expected_date_from'/'expected_date_to' dates.

        :param company: The company.
        :param date: The date belonging to the fiscal year.
        :param expected_date_from: The expected date_from after computation.
        :param expected_date_to: The expected date_to after computation.
        '''
        current_date = fields.Date.from_string(date)
        res = company.compute_fiscalyear_dates(current_date)
        self.assertEqual(res['date_from'], fields.Date.from_string(expected_date_from))
        self.assertEqual(res['date_to'], fields.Date.from_string(expected_date_to))

    def test_default_fiscal_year(self):
        '''Basic case with a fiscal year xxxx-01-01 - xxxx-12-31.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = '12'

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

        self.check_compute_fiscal_year(
            company,
            '2017-10-15',
            '2017-01-01',
            '2017-12-31',
        )

    def test_leap_fiscal_year_1(self):
        '''Case with a leap year ending the 29 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 29
        company.fiscalyear_last_month = '2'

        self.check_compute_fiscal_year(
            company,
            '2016-02-29',
            '2015-03-01',
            '2016-02-29',
        )

        self.check_compute_fiscal_year(
            company,
            '2015-03-01',
            '2015-03-01',
            '2016-02-29',
        )

        self.check_compute_fiscal_year(
            company,
            '2015-10-15',
            '2015-03-01',
            '2016-02-29',
        )

    def test_leap_fiscal_year_2(self):
        '''Case with a leap year ending the 28 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 28
        company.fiscalyear_last_month = '2'

        self.check_compute_fiscal_year(
            company,
            '2016-02-29',
            '2015-03-01',
            '2016-02-29',
        )

        self.check_compute_fiscal_year(
            company,
            '2016-03-01',
            '2016-03-01',
            '2017-02-28',
        )

        self.check_compute_fiscal_year(
            company,
            '2015-03-15',
            '2015-03-01',
            '2016-02-29',
        )