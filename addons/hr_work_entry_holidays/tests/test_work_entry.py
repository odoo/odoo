# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tests.common import tagged
from odoo.fields import Date, Datetime
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry')
class TestWorkeEntryHolidaysWorkEntry(TestWorkEntryHolidaysBase):

    # def _set_current_contract(self, vals_list):
    #     # We patch the create function to not use the override of hr_work_entry_contract
    #     return vals_list

    def setUp(self):
        super(TestWorkeEntryHolidaysWorkEntry, self).setUp()
        self.tz = pytz.timezone(self.richard_emp.tz)
        self.start = datetime(2015, 11, 1, 1, 0, 0)
        self.end = datetime(2015, 11, 30, 23, 59, 59)
        self.resource_calendar_id = self.env['resource.calendar'].create({'name': 'Zboub'})
        self.richard_emp.resource_calendar_id = self.resource_calendar_id

    def test_work_entry_get_duration(self):
        date_from = datetime(2021, 2, 5, 8, 0, 0)
        leave = self.create_leave(date_from=date_from, date_to=date_from + relativedelta(days=5))
        # I create a contract for "Richard"
        self.env['hr.contract'].create({
            'date_end': Datetime.today() + relativedelta(years=2),
            'date_start': Date.to_date('2016-01-01'),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'employee_id': self.richard_emp.id,
            'state': 'open',
        })
        work_entry = self.create_work_entry(datetime(2021, 2, 2, 9, 0), datetime(2021, 2, 2, 12, 0))
        result = work_entry._get_duration(leave.date_from, leave.date_to)
        self.assertEqual(result, 120.0, "The work entry duration should be equal to 120.0 (5 x 24h)")
