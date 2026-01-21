# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrLeaveType(TestHrHolidaysCommon):

    def test_time_type(self):
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            leave_type.allow_request_on_top = True

        worked_leave_type = self.env['hr.leave.type'].create({
            'name': 'Worked Time',
            'time_type': 'other',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            worked_leave_type.elligible_for_accrual_rate = False

        leave_0 = self.env['hr.leave'].create({
            'name': 'Remote Work',
            'employee_id': employee.id,
            'holiday_status_id': worked_leave_type.id,
            'request_date_from': '2025-09-01',  # Monday
            'request_date_to': '2025-09-05',
        })
        leave_0.action_approve()
        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_0.id)]).time_type,
            'other',
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertFalse(employee.is_absent)

        with self.assertRaises(ValidationError):
            leave_1 = self.env['hr.leave'].create({
                'name': 'Doctor Appointment',
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2025-09-03',
                'request_date_to': '2025-09-03',
        })

        worked_leave_type.allow_request_on_top = True
        leave_1 = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': '2025-09-03',
            'request_date_to': '2025-09-03',
        })
        leave_1.action_approve()

        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_1.id)]).time_type,
            'leave'
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertTrue(employee.is_absent)

    def test_type_creation_right(self):
        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.env['hr.leave.type'].with_user(self.user_hruser_id).create({
                'name': 'UserCheats',
                'requires_allocation': False,
                'request_unit': 'day',
                'unit_of_measure': 'day',
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
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            })

        self.env['hr.leave.allocation'].sudo().create({
            'state': 'confirm',
            'holiday_status_id': leave_type.id,
            'employee_id': employee.id,
            'date_from': '2024-08-19',
            'date_to': '2024-08-20',
        }).action_approve()

        leave_types = self.env['hr.leave.type'].with_context(
            default_date_from='2024-08-20 21:00:00',
            default_date_to='2024-08-21 09:00:00',
            tz='Pacific/Saipan',
            employee_id=employee.id,
            ).search([('has_valid_allocation', '=', True)], limit=1)

        self.assertFalse(leave_types, "Got valid leaves outside vaild period")

    def test_calendar_duration_excluding_public_holidays(self):
        """Test calendar duration calculation excluding public holidays"""

        calendar_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Time Off (Exclude PH)',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'include_public_holidays_in_duration': False,
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 6, 3, 0, 0, 0),
            'date_to': datetime(2024, 6, 3, 23, 59, 59),
            'calendar_id': False,
            'company_id': self.env.company.id,
        })

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': calendar_leave_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 6, "Duration should exclude 1 public holiday, resulting in 6 days")
        self.assertEqual(hours, 48, "Duration should be 6 * 8 hours when excluding public holidays")

    def test_calendar_duration_including_public_holidays(self):
        """Test calendar duration calculation including public holidays"""

        calendar_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Time Off (Include PH)',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'include_public_holidays_in_duration': True,
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 6, 3, 0, 0, 0),
            'date_to': datetime(2024, 6, 3, 23, 59, 59),
            'calendar_id': False,
            'company_id': self.env.company.id,
        })

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': calendar_leave_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 7, "Duration should include all 7 days even with public holiday")
        self.assertEqual(hours, 56, "Duration should be 7 * 8 hours when including public holidays")

    def test_count_days_as_working_days(self):
        """Test duration calculation when count_days_as is worked days"""
        working_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Time Off',
            'requires_allocation': False,
            'count_days_as': 'working',
        })
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': working_leave_type.id,
            'request_date_from': date(2024, 6, 1),
            'request_date_to': date(2024, 6, 7),
        })

        days, hours = leave._get_durations()[leave.id]
        self.assertEqual(days, 5, "Working days should exclude weekends")
        self.assertEqual(hours, 40, "Working hours should be 5 * 8 hours")

    def test_change_count_days_as(self):
        """Changing count_days_as after leave is validated should raise ValidationError"""
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Time Off',
            'requires_allocation': False,
            'count_days_as': 'working',
        })

        # Change before any leave: should be allowed
        leave_type.count_days_as = 'calendar'

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2024, 7, 1),
            'request_date_to': date(2024, 7, 5),
        })
        leave.action_approve()

        with self.assertRaises(ValidationError):
            leave_type.count_days_as = 'working'
