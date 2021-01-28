# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase
from odoo.fields import Datetime, Date

# override: _get_new_resource_leave_values --> calendar enterprise

class TestWorkEntryLeave(TestWorkEntryHolidaysBase):


    @classmethod
    def setUpClass(cls):
        super(TestWorkEntryLeave, cls).setUpClass()

    def test_work_entry_company_values(self):
        date_from = datetime(2021, 2, 5, 8, 0, 0)
        leave = self.create_leave(date_from=date_from, date_to=date_from+relativedelta(days=5))
        calendar = leave._get_calendar()
        self.assertTrue(calendar.id in [leave.employee_id.resource_calendar_id.id, self.env.company.resource_calendar_id.id],
                        "The leave calendar should be the employee or company one")

        result = leave._get_number_of_days(date_from=leave.date_from, date_to=leave.date_to, employee_id=leave.employee_id.id)
        self.assertEqual(result['days'], 3.0, "The leave should be 3 open days ")
        self.assertEqual(result['hours'], 24, "The leave should be 24 hours")

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
        work_entry.write({'leave_id': leave.id, 'employee_id':  leave.employee_id.id})
        leave._refused_work_entry(work_entry)
        self.assertFalse(work_entry.leave_id, "The work entry should not have leave_id after refusal")
        self.assertNotEqual(work_entry.work_entry_type_id.id, leave.holiday_status_id.work_entry_type_id.id,
                            "The work entry type should be attendance after a refusal")


    def test_get_work_entry_values(self):
        # Take an holiday from 5 in the morning but the company working hours starts at 7
        date_from = datetime(2021, 2, 2, 5, 0, 0)
        leave = self.create_leave(date_from=date_from, date_to=date_from + relativedelta(days=1))
        result = leave._get_work_entry_values()
        starts = list(map(lambda w: w['date_start'], result))
        stops = list(map(lambda w: w['date_stop'], result))
        self.assertEqual(starts, [datetime(2021, 2, 2, 7, 0, 0), datetime(2021, 2, 2, 12, 0, 0)])
        self.assertEqual(stops, [datetime(2021, 2, 2, 11, 0, 0), datetime(2021, 2, 2, 16, 0, 0)])
