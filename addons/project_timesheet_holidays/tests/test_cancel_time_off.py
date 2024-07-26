# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged, new_test_user


@tagged('post_install', '-at_install')
class TestCancelTimeOff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.global_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Test Global Leave',
            'date_from': '2020-01-08 00:00:00',
            'date_to': '2020-01-08 23:59:59',
            'calendar_id': cls.company.resource_calendar_id.id,
            'company_id': cls.company.id,
        })
        cls.employee_user = new_test_user(
            cls.env,
            login='test_user',
            name='Test User',
            company_id=cls.company.id,
            groups='base.group_user,hr_timesheet.group_hr_timesheet_user',
        )
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': cls.employee_user.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'company_id': cls.company.id,
        })
        cls.generic_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Generic Time Off',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'company_id': cls.company.id,
        })

    @freeze_time('2020-01-01')
    def test_cancel_time_off(self):
        """ Test that an employee can cancel a future time off, that crosses a global leave,
            if the employee is not in the group_hr_holidays_user.

            Test Case:
            =========
            1) Create a time off in the future and that crosses a global leave
            2) Approve the time off with the admin
            3) Cancel the time off with the user that is not in the group_hr_holidays_user
            4) No read error on employee_ids should be raised
        """
        time_off = self.env['hr.leave'].create({
            'name': 'Test Time Off',
            'holiday_type': 'employee',
            'holiday_status_id': self.generic_time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2020-01-07 08:00:00',
            'date_to': '2020-01-09 17:00:00',
        })
        time_off.action_validate()
        HrHolidaysCancelLeave = self.env[
            'hr.holidays.cancel.leave'].with_user(self.employee_user).with_company(self.company.id)
        HrHolidaysCancelLeave.create({
            'leave_id': time_off.id, 'reason': 'Test Reason'}).action_cancel_leave()
