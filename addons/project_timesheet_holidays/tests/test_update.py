# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, timedelta

from odoo import fields

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateTimesheetHolidays(TestUpdateEmployeesCommon):

    def test_employee_with_public_holidays_timesheet_is_not_light_user(self):
        today = fields.Date.today()
        next_monday = today + timedelta(days=7 - today.weekday())
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'calendar_id': self.env.company.resource_calendar_id.id,
            'date_from': datetime.combine(next_monday, time(0, 0)),
            'date_to': datetime.combine(next_monday + timedelta(days=4), time(23, 59)),
        })
        before = self._count()
        employee = self.env['hr.employee'].create({'name': 'On Holiday'})
        self.assertTrue(
            self.env['account.analytic.line'].search_count([('employee_id', '=', employee.id)]),
            "Future public holiday timesheets should be generated for the new employee",
        )
        self.assertEqual(self._count(), before)
