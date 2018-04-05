# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase

import odoo.tests

from odoo.tools.datetime import datetime


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
        current_date = date
        res = company.compute_fiscalyear_dates(current_date)
        self.assertEqual(res['date_from'], expected_date_from)
        self.assertEqual(res['date_to'], expected_date_to)

    def test_default_fiscal_year(self):
        '''Basic case with a fiscal year xxxx-01-01 - xxxx-12-31.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        self.check_compute_fiscal_year(
            company,
            datetime(2017, 12, 31),
            datetime(2017, 1, 1),
            datetime(2017, 12, 31),
        )

        self.check_compute_fiscal_year(
            company,
            datetime(2017, 1, 1),
            datetime(2017, 1, 1),
            datetime(2017, 12, 31),
        )

    def test_leap_fiscal_year_1(self):
        '''Case with a leap year ending the 29 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 29
        company.fiscalyear_last_month = 2

        self.check_compute_fiscal_year(
            company,
            datetime(2016, 2, 29),
            datetime(2015, 3, 1),
            datetime(2016, 2, 29),
        )

        self.check_compute_fiscal_year(
            company,
            datetime(2015, 3, 1),
            datetime(2015, 3, 1),
            datetime(2016, 2, 29),
        )

    def test_leap_fiscal_year_2(self):
        '''Case with a leap year ending the 28 February.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 28
        company.fiscalyear_last_month = 2

        self.check_compute_fiscal_year(
            company,
            datetime(2016, 3, 1),
            datetime(2016, 2, 29),
            datetime(2017, 2, 28),
        )

    def test_custom_fiscal_year(self):
        '''Case with custom fiscal years.'''
        company = self.env.ref('base.main_company')
        company.fiscalyear_last_day = 31
        company.fiscalyear_last_month = 12

        # Create custom fiscal year covering the 6 first months of 2017.
        self.env['account.fiscal.year'].create({
            'name': '6 month 2017',
            'date_from': datetime(2017, 1, 1),
            'date_to': datetime(2017, 5, 31),
            'company_id': company.id,
        })

        # Check before the custom fiscal year).
        self.check_compute_fiscal_year(
            company,
            datetime(2017, 2, 1),
            datetime(2017, 1, 1),
            datetime(2017, 5, 31),
        )

        # Check after the custom fiscal year.
        self.check_compute_fiscal_year(
            company,
            datetime(2017, 11, 1),
            datetime(2017, 6, 1),
            datetime(2017, 12, 31),
        )

        # Create custom fiscal year covering the 3 last months of 2017.
        self.env['account.fiscal.year'].create({
            'name': 'last 3 month 2017',
            'date_from': datetime(2017, 10, 1),
            'date_to': datetime(2017, 12, 31),
            'company_id': company.id,
        })

        # Check inside the custom fiscal years.
        self.check_compute_fiscal_year(
            company,
            datetime(2017, 7, 1),
            datetime(2017, 6, 1),
            datetime(2017, 9, 30),
        )
