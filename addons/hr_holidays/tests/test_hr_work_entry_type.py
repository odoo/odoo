# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrWorkEntryType(TestHrHolidaysCommon):

    def test_count_as(self):
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})

        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Paid Time Off',
            'code': 'Paid Time Off',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            work_entry_type.allow_request_on_top = True

        worked_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Worked Time',
            'code': 'Worked Time',
            'count_as': 'working_time',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with self.assertRaises(ValidationError):
            worked_work_entry_type.elligible_for_accrual_rate = False

        leave_0 = self.env['hr.leave'].create({
            'name': 'Remote Work',
            'employee_id': employee.id,
            'work_entry_type_id': worked_work_entry_type.id,
            'request_date_from': '2025-09-01',  # Monday
            'request_date_to': '2025-09-05',
        })
        leave_0.action_approve()
        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_0.id)]).count_as,
            'working_time',
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertFalse(employee.is_absent)

        with self.assertRaises(ValidationError):
            leave_1 = self.env['hr.leave'].create({
                'name': 'Doctor Appointment',
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2025-09-03',
                'request_date_to': '2025-09-03',
        })

        worked_work_entry_type.allow_request_on_top = True
        leave_1 = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': '2025-09-03',
            'request_date_to': '2025-09-03',
        })
        leave_1.action_approve()

        self.assertEqual(
            self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave_1.id)]).count_as,
            'absence'
        )
        with freeze_time('2025-09-03 13:00:00'):
            employee._compute_leave_status()
            self.assertTrue(employee.is_absent)

    def test_type_creation_right(self):
        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.env['hr.work.entry.type'].with_user(self.user_hruser_id).create({
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
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Leave',
            'code': 'Test Leave',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            })

        self.env['hr.leave.allocation'].sudo().create({
            'state': 'confirm',
            'work_entry_type_id': work_entry_type.id,
            'employee_id': employee.id,
            'date_from': '2024-08-19',
            'date_to': '2024-08-20',
        }).action_approve()

        work_entry_types = self.env['hr.work.entry.type'].with_context(
            default_date_from='2024-08-20 21:00:00',
            default_date_to='2024-08-21 09:00:00',
            tz='Pacific/Saipan',
            employee_id=employee.id,
            ).search([('has_valid_allocation', '=', True)], limit=1)

        self.assertFalse(work_entry_types, "Got valid leaves outside vaild period")
