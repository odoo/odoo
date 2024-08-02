# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import AccessError

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveType(TestHrHolidaysCommon):

    def test_time_type(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'no',
        })

        leave_1 = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': leave_type.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })
        leave_1.action_approve()

        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_1.id)]).time_type,
            'leave'
        )

    def test_type_creation_right(self):
        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.env['hr.leave.type'].with_user(self.user_hruser_id).create({
                'name': 'UserCheats',
                'requires_allocation': 'no',
            })

    def test_users_tz_shift_back(self):
        """This test follows closely related bug report and simulates its situation.
        We're located in Saipan (GMT+10) and we allocate some employee a leave from 19Aug-20Aug.
        Then we simulate opening the employee's calendar and attempting to allocate 21August.
        We should not get any valid allocation there as is it outsite of valid alocation period.

        2024-08-19      2024-08-20        2024-08-21
        ────┬─────────────────┬─────────────────┬─────►
            └─────────────────┘             requested
          Valid allocation period              day
        """
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        leave_type = self.env['hr.leave.type'].create({'name': 'Test Leave'})

        self.env['hr.leave.allocation'].sudo().create({
            'state': 'confirm',
            'holiday_status_id': leave_type.id,
            'employee_id': employee.id,
            'date_from': '2024-08-19',
            'date_to': '2024-08-20',
        }).action_validate()

        leave_types = self.env['hr.leave.type'].with_context(
            default_date_from='2024-08-20 21:00:00',
            default_date_to='2024-08-21 09:00:00',
            tz='Pacific/Saipan',
            employee_id=employee.id,
            ).search([('has_valid_allocation', '=', True)], limit=1)

        self.assertFalse(leave_types, "Got valid leaves outside vaild period")
