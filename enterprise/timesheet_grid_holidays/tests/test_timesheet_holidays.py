# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import fields, SUPERUSER_ID
from odoo.exceptions import UserError
from datetime import date, datetime

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTimesheetGridHolidays(TestCommonTimesheet, MailCase):

    @freeze_time('2018-2-6')
    def test_timer_methods_handle_project_access_restrictions(self):
        """Ensure timer visibility computation does not raise AccessError for restricted users.
            1. Create a private project with a task and a linked timesheet.
            2. Use a Timesheet Manager user without project access.
            3. Call _should_not_display_timer() and action_timer_start() as that user.
            4. Verify that no AccessError is raised due to the use of sudo() within these methods.
        """
        self.timesheet.date = fields.Date.today()
        self.timesheet_manager_no_project_user.action_create_employee()
        employee = self.timesheet_manager_no_project_user.employee_id
        timesheet = self.timesheet.with_user(self.timesheet_manager_no_project_user)
        timesheet.employee_id = employee
        self.assertFalse(
            timesheet._should_not_display_timer(),
            "_should_not_display_timer() should be True"
        )
        timesheet.action_timer_start()
        self.assertTrue(
            timesheet.is_timer_running,
            "Timer should be running after action_timer_start()"
        )

    def test_overtime_calcution_timesheet_holiday_flow(self):
        """ Employee's leave is not calculated as overtime hours when employee is on time off."""
        self.empl_employee.write({
            'create_date': date(2021, 1, 1),
            'employee_type': 'freelance',  # Avoid searching the contract if hr_contract module is installed before this module.
        })
        start_date = '2021-10-04'
        end_date = '2021-10-09'
        result = self.empl_employee.get_timesheet_and_working_hours_for_employees(start_date, end_date)
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 40, "Employee weekly working hours should be 40.")
        self.assertEqual(result[self.empl_employee.id]['worked_hours'], 0.0, "Employee's working hours should be None.")

        # all company have those internal project/task (created by default)
        internal_project = self.env.company.internal_project_id
        internal_task_leaves = self.env.company.leave_timesheet_task_id
        hr_leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': internal_project.id,
            'timesheet_task_id': internal_task_leaves.id,
        })
        HrLeave = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        # employee creates a leave request
        holiday = HrLeave.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type.id,
            'request_date_from': '2021-10-05',
            'request_date_to': '2021-10-05',
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        result = self.empl_employee.get_timesheet_and_working_hours_for_employees(start_date, end_date)
        self.assertTrue(len(holiday.timesheet_ids) > 0, 'Timesheet entry should be created in Internal project for time off.')
        # working hours for employee after leave creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's weekly units of work after the leave creation should be 32.")
        self.assertEqual(result[self.empl_employee.id]['worked_hours'], 0.0, "Employee's working hours shouldn't be altered after the leave creation.")

        # Timesheet created for same project
        timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': internal_project.id,
            'date': '2021-10-04',
            'unit_amount': 8.0,
        })
        timesheet1.with_user(self.user_manager).action_validate_timesheet()
        result = self.empl_employee.get_timesheet_and_working_hours_for_employees(start_date, end_date)
        # working hours for employee after Timesheet creations
        self.assertEqual(result[self.empl_employee.id]['units_to_work'], 32, "Employee's one week units of work after the Timesheet creation should be 32.")

    @freeze_time('2018-2-6')
    def test_grid_update_holiday(self):
        Requests = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        hr_leave_type_with_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.env.company.internal_project_id.id,
            'timesheet_task_id': self.env.company.leave_timesheet_task_id.id,
        })
        # employee creates a leave request
        holiday = Requests.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type_with_ts.id,
            'request_date_from': '2018-02-05',
            'request_date_to': '2018-02-05',
            'request_hour_from': 8,
            'request_hour_to': 9,
            'request_unit_hours': True,
        })
        # validate leave request and create timesheet
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), 1)

        # create timesheet via grid_update_cell
        today_date = fields.Date.today()
        column_date = today_date
        timesheet = holiday.timesheet_ids
        domain = [  # domain given by the grid cell edited
            ('date', '=', today_date),
            ('employee_id', '=', self.empl_employee.id),
            ('project_id', '=', timesheet.project_id.id),
            ('task_id', '=', timesheet.task_id.id),
        ]
        self.env['account.analytic.line'] \
            .with_user(SUPERUSER_ID) \
            .with_context( # when the user will edit a grid cell, the context of the cell will be given
                default_date=column_date,
                default_project_id=timesheet.project_id.id,
                default_task_id=timesheet.task_id.id,
                default_employee_id=self.empl_employee.id,
            ) \
            .grid_update_cell(domain, 'unit_amount', 3.0)

        timesheets = self.env['account.analytic.line'].search([
            ('date', '=', today_date),
            ('employee_id', '=', self.empl_employee.id),
            ('id', 'not in', holiday.timesheet_ids.ids),
        ])
        self.assertEqual(len(timesheets), 1, "The new timesheet should have been created")
        self.assertFalse(timesheets.holiday_id, "The new timesheet should not be linked to a leave request")
        self.assertEqual(timesheets.unit_amount, 3.0, "The new timesheet should have the correct amount of time")
        self.assertEqual(timesheets.project_id, holiday.timesheet_ids.project_id, "The new timesheet should have the same project as the timesheet generated by the leave request")
        self.assertEqual(timesheets.task_id, holiday.timesheet_ids.task_id, "The new timesheet should have the same task as the timesheet generated by the leave request")

    def test_start_timer_in_timeoff_task(self):
        common_vals = {
            'project_id': self.env.company.internal_project_id.id,
            'task_id': self.env.company.leave_timesheet_task_id.id,
        }
        Timesheet = self.env['account.analytic.line'].with_user(self.user_manager)
        timesheet = Timesheet.sudo().create({
            'name': "my timesheet 1",
            **common_vals,
        })
        with self.assertRaises(UserError, msg="a user cannot start timer in timesheet in time off task"):
            timesheet.action_timer_start()

        with self.assertRaises(UserError, msg="the user cannot create a timesheet and start a timer in time off task"):
            timesheet.action_start_new_timesheet_timer(common_vals)

    def test_employee_timesheet_reminder_skips_holidays_and_leaves(self):
        """
        Reminder mail should be sent to employees, skipping holidays and approved leaves.
        steps:
            - Create User & Employee
            - Setup Leave Type
            - Create & Validate Leave
            - Create Public Holiday
            - Create Timesheet Entry
            - Set Next Reminder Date
            - Run Cron & Assert Emails
        """
        user_hruser = mail_new_test_user(self.env, login='armande1', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        user_hruser.action_create_employee()

        Requests = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        hr_leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.env.company.internal_project_id.id,
            'timesheet_task_id':  self.env.company.leave_timesheet_task_id.id,
        })

        time_off = Requests.with_user(user_hruser).create({
            'name': 'Test Time Off',
            'employee_id': user_hruser.employee_id.id,
            'holiday_status_id': hr_leave_type.id,
            'request_date_from': '2022-01-31',
            'request_date_to': '2022-01-31',
        })
        time_off.with_user(SUPERUSER_ID).action_validate()

        self.env['resource.calendar.leaves'].create({
            'name': 'New Public Holiday',
            'calendar_id': user_hruser.employee_id.resource_calendar_id.id,
            'date_from': '2022-02-01',
            'date_to': '2022-02-01',
        })

        timesheet_date = datetime(2022, 2, 4, 8, 8, 15)
        timesheet_vals = {
            'name': "My Timesheet",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': '2022-02-03',
            'unit_amount': 8.0,
        }
        self.env['account.analytic.line'].with_user(self.user_employee).create(timesheet_vals)

        self.user_employee.company_id.timesheet_mail_employee_nextdate = timesheet_date

        with freeze_time(timesheet_date), self.mock_mail_gateway():
            self.env['res.company']._cron_timesheet_reminder_employee()

            self.assertEqual(
                len(self._new_mails.filtered(lambda x: x.res_id == self.user_employee.employee_id.id)),
                1, "An email should be sent to 'User Empl Officer'"
            )
            self.assertEqual(
                len(self._new_mails.filtered(lambda x: x.res_id == user_hruser.employee_id.id)),
                0, "No email should be sent to 'HR User Empl Officer'"
            )
