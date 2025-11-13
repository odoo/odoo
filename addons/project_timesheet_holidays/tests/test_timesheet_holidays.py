# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields, SUPERUSER_ID

from odoo.exceptions import UserError
from odoo.tests import common, new_test_user
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet
import time


class TestTimesheetHolidaysCreate(common.TransactionCase):

    def test_company_create(self):
        main_company = self.env.ref('base.main_company')
        user = new_test_user(self.env, login='fru',
                             groups='base.group_user,base.group_erp_manager,base.group_partner_manager',
                             company_id=main_company.id,
                             company_ids=[(6, 0, main_company.ids)])
        Company = self.env['res.company']
        Company = Company.with_user(user)
        Company = Company.with_company(main_company)
        company = Company.create({'name': "Wall Company"})
        self.assertEqual(company.internal_project_id.sudo().company_id, company, "It should have created a project for the company")

class TestTimesheetHolidays(TestCommonTimesheet):

    def setUp(self):
        super().setUp()

        self.employee_working_calendar = self.empl_employee.resource_calendar_id
        # leave dates : from next monday to next wednesday (to avoid crashing tests on weekend, when
        # there is no work days in working calendar)
        # NOTE: second and millisecond can add a working days
        self.leave_start_datetime = datetime(2018, 2, 5)  # this is monday
        self.leave_end_datetime = self.leave_start_datetime + relativedelta(days=2)

        # all company have those internal project/task (created by default)
        self.internal_project = self.env.company.internal_project_id
        self.internal_task_leaves = self.env.company.leave_timesheet_task_id

        self.hr_leave_type_with_ts = self.env['hr.leave.type'].sudo().create({
            'name': 'Time Off Type with timesheet generation (absence)',
            'requires_allocation': False,
        })

        self.hr_leave_type_worked = self.env['hr.leave.type'].sudo().create({
            'name': 'Time Off Type (worked time)',
            'requires_allocation': False,
            'time_type': 'other',
        })

        # HR Officer allocates some leaves to the employee 1
        self.Requests = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        self.Allocations = self.env['hr.leave.allocation'].with_context(mail_create_nolog=True, mail_notrack=True)
        self.hr_leave_allocation_with_ts = self.Allocations.sudo().create({
            'name': 'Days for limited category with timesheet',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'number_of_days': 10,
            'state': 'confirm',
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })

    def test_validate_with_timesheet(self):
        # employee creates a leave request
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_approve()

        # The leave type and timesheet are linked to the same project and task of hr_leave_type_with_ts as the company is set
        self.assertEqual(holiday.timesheet_ids.project_id.id, self.internal_project.id)
        self.assertEqual(holiday.timesheet_ids.task_id.id, self.internal_task_leaves.id)

        self.assertEqual(len(holiday.timesheet_ids), holiday.number_of_days, 'Number of generated timesheets should be the same as the leave duration (1 per day between %s and %s)' % (fields.Datetime.to_string(self.leave_start_datetime), fields.Datetime.to_string(self.leave_end_datetime)))

        # manager refuse the leave
        holiday.with_user(SUPERUSER_ID).action_refuse()
        self.assertEqual(len(holiday.timesheet_ids), 0, 'Number of linked timesheets should be zero, since the leave is refused.')

        company = self.env['res.company'].create({"name": "new company"})
        self.empl_employee.write({
            "company_id": company.id,
        })

        hr_leave_type_with_ts_without_company = self.hr_leave_type_with_ts.copy()
        hr_leave_type_with_ts_without_company.write({
            'company_id': False,
        })

        holiday = self.Requests.create({
            'name': 'Time Off 2',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type_with_ts_without_company.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_approve()

        # The leave type and timesheet are linked to the same project and task of the employee company as the company is not set
        self.assertEqual(holiday.timesheet_ids.project_id.id, company.internal_project_id.id)
        self.assertEqual(holiday.timesheet_ids.task_id.id, company.leave_timesheet_task_id.id)

    def test_validate_worked_leave(self):
        # employee creates a leave request of worked time type
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 3',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_worked.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_approve()

        self.assertEqual(len(holiday.timesheet_ids), 0, 'No timesheet should be created for a leave of worked time type')

    @freeze_time('2018-02-05')  # useful to be able to cancel the validated time off
    def test_cancel_validate_holidays(self):
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(self.env.user).action_approve()
        self.assertEqual(len(holiday.timesheet_ids), holiday.number_of_days, 'Number of generated timesheets should be the same as the leave duration (1 per day between %s and %s)' % (fields.Datetime.to_string(self.leave_start_datetime), fields.Datetime.to_string(self.leave_end_datetime)))

        self.env['hr.holidays.cancel.leave'].with_user(self.user_employee).with_context(default_leave_id=holiday.id) \
            .new({'reason': 'Test remove holiday'}) \
            .action_cancel_leave()
        self.assertEqual(holiday.state, 'cancel', 'The time off should be archived')
        self.assertEqual(len(holiday.timesheet_ids), 0, 'The timesheets generated should be unlink.')

    def test_timesheet_time_off_including_public_holiday(self):
        """ Generate one timesheet for the public holiday and 4 timesheets for the time off.
            Test Case:
            =========
            1) Create a public time off on Wednesday
            2) In the same week, create a time off during one week for an employee
            3) Check if there are five timesheets generated for time off and public
               holiday.4 timesheets should be linked to the time off and 1 for
               the public one.
        """

        leave_start_datetime = datetime(2022, 1, 24, 7, 0, 0, 0) # Monday
        leave_end_datetime = datetime(2022, 1, 28, 18, 0, 0, 0)

        # Create a public holiday
        self.env['resource.calendar.leaves'].create({
            'name': 'Test',
            'calendar_id': self.employee_working_calendar.id,
            'date_from': datetime(2022, 1, 26, 7, 0, 0, 0),  # This is Wednesday and India Independence
            'date_to': datetime(2022, 1, 26, 18, 0, 0, 0),
        })

        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': leave_start_datetime,
            'request_date_to': leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_approve()
        self.assertEqual(len(holiday.timesheet_ids), 4, '4 timesheets should be generated for this time off.')

        timesheets = self.env['account.analytic.line'].search([
            ('date', '>=', leave_start_datetime),
            ('date', '<=', leave_end_datetime),
            ('employee_id', '=', self.empl_employee.id),
        ])

        # should not able to update timeoff timesheets
        with self.assertRaises(UserError):
            timesheets.with_user(self.user_employee).write({'task_id': 4})

        # should not able to create timesheet in timeoff task
        with self.assertRaises(UserError):
            self.env['account.analytic.line'].with_user(self.user_employee).create({
                'name': "my timesheet",
                'project_id': self.internal_project.id,
                'task_id': self.internal_task_leaves.id,
                'date': '2021-10-04',
                'unit_amount': 8.0,
            })

        self.assertEqual(len(timesheets.filtered('holiday_id')), 4, "4 timesheet should be linked to employee's timeoff")
        self.assertEqual(len(timesheets.filtered('global_leave_id')), 1, '1 timesheet should be linked to global leave')

    def test_delete_timesheet_after_new_holiday_covers_whole_timeoff(self):
        """ User should be able to delete a timesheet created after a new public holiday is added,
            covering the *whole* period of a existing time off.
            Test Case:
            =========
            1) Create a Time off, approve and validate it.
            2) Create a new Public Holiday, covering the whole time off created in step 1.
            3) Delete the new timesheet associated with the public holiday.
        """

        leave_start_datetime = datetime(2022, 1, 31, 7, 0, 0, 0)    # Monday
        leave_end_datetime = datetime(2022, 1, 31, 18, 0, 0, 0)

        # (1) Create a timeoff and validate it
        time_off = self.Requests.with_user(self.user_employee).create({
            'name': 'Test Time off please',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': leave_start_datetime,
            'request_date_to': leave_end_datetime,
        })
        time_off.with_user(SUPERUSER_ID).action_approve()

        # (2) Create a public holiday
        self.env['resource.calendar.leaves'].create({
            'name': 'New Public Holiday',
            'calendar_id': self.employee_working_calendar.id,
            'date_from': datetime(2022, 1, 31, 5, 0, 0, 0),     # Covers the whole time off
            'date_to': datetime(2022, 1, 31, 23, 0, 0, 0),
        })

        # The timeoff should have been force_cancelled and its associated timesheet unlinked.
        self.assertFalse(time_off.timesheet_ids, '0 timesheet should remain for this time off.')

        # (3) Delete the timesheet
        timesheets = self.env['account.analytic.line'].search([
            ('date', '>=', leave_start_datetime),
            ('date', '<=', leave_end_datetime),
            ('employee_id', '=', self.empl_employee.id),
        ])

        # timesheet should be unlinked to the timeoff, and be able to delete it
        timesheets.with_user(SUPERUSER_ID).unlink()
        self.assertFalse(timesheets.exists(), 'Timesheet should be deleted')

    def test_timeoff_task_creation_with_holiday_leave(self):
        """ Test the search method on is_timeoff_task"""
        company = self.env['res.company'].create({"name": "new company"})
        self.empl_employee.write({
            "company_id": company.id,
        })
        task_count = self.env['project.task'].search_count([('is_timeoff_task', '!=', False)])
        timesheet_count = self.env['account.analytic.line'].search_count([('holiday_id', '!=', False)])
        leave = self.Requests.with_user(SUPERUSER_ID).create({
            'name': 'Test Leave',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': datetime(2024, 6, 24),
            'request_date_to': datetime(2024, 6, 24),
        })
        leave.with_user(SUPERUSER_ID).action_approve()
        new_task_count = self.env['project.task'].search_count([('is_timeoff_task', '!=', False)])
        self.assertEqual(task_count + 1, new_task_count)
        new_timesheet_count = self.env['account.analytic.line'].search_count([('holiday_id', '!=', False)])
        self.assertEqual(timesheet_count + 1, new_timesheet_count)

    def test_timesheet_timeoff_flexible_employee(self):
        flex_40h_calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'hours_per_day': 8.0,
            'full_time_required_hours': 40.0,
            'flexible_hours': True,
        })

        self.empl_employee.resource_calendar_id = flex_40h_calendar

        time_off = self.Requests.with_user(self.user_employee).create({
            'name': 'Test Time off please',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        time_off.with_user(SUPERUSER_ID)._action_validate()

        timesheet = self.env['account.analytic.line'].search([
            ('date', '>=', self.leave_start_datetime),
            ('date', '<=', self.leave_end_datetime),
            ('employee_id', '=', self.empl_employee.id),
        ])
        self.assertEqual(len(timesheet), 3, "Three timesheets should be created for each leave day")
        self.assertEqual(sum(timesheet.mapped('unit_amount')), 24, "The duration of the timesheet for flexible employee leave "
                                                        "should be number of days * hours per day")

    def test_multi_create_timesheets_from_calendar(self):
        """
        Simulate creating timesheets using the multi-create feature in the calendar view
        """

        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'date_from': datetime(2025, 5, 27, 0, 0),
            'date_to': datetime(2025, 5, 28, 23, 59),
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': False,
        })

        self.env['hr.leave'].sudo().create([
            {
                'holiday_status_id': leave_type.id,
                'employee_id': self.empl_employee.id,
                'request_date_from': datetime(2025, 5, 26, 8, 0),
                'request_date_to': datetime(2025, 5, 26, 17, 0),
            }, {
                'holiday_status_id': leave_type.id,
                'employee_id': self.empl_employee2.id,
                'request_date_from': datetime(2025, 5, 29, 8, 0),
                'request_date_to': datetime(2025, 5, 29, 17, 0),
            },
        ])._action_validate()

        # At this point:
        # - empl_employee is on time off the 26th
        # - both empl_employee and empl_employee2 are on public time off the 27th and 28th
        # - empl_employee2 is on time off the 29th

        timesheets = self.env['account.analytic.line'].with_context(timesheet_calendar=True).create([{
            'project_id': self.project_customer.id,
            'unit_amount': 1,
            'date': f'2025-05-{day}',
            'employee_id': employee.id,
        } for day in ('26', '27', '28', '29') for employee in (self.empl_employee, self.empl_employee2)])
        self.assertEqual(len(timesheets), 2, "Two leaves should have been created: one for each employee")
        self.assertEqual(timesheets[0].employee_id, self.empl_employee2)
        self.assertEqual(fields.Date.to_string(timesheets[0].date), '2025-05-26')
        self.assertEqual(timesheets[1].employee_id, self.empl_employee)
        self.assertEqual(fields.Date.to_string(timesheets[1].date), '2025-05-29')

    def test_one_day_timesheet_timeoff_flexible_employee(self):
        flex_40h_calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 10h/week',
            'hours_per_day': 10,
            'full_time_required_hours': 10,
            'flexible_hours': True,
        })

        self.empl_employee.resource_calendar_id = flex_40h_calendar

        time_off = self.Requests.with_user(self.user_employee).create({
            'name': 'Test 1 day Time off',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': datetime(2025, 7, 12),  # Random saturday
            'request_date_to': datetime(2025, 7, 12),
        })
        time_off.with_user(SUPERUSER_ID)._action_validate()

        timesheet = self.env['account.analytic.line'].search([
            ('date', '>=', datetime(2025, 7, 12)),
            ('date', '<=', datetime(2025, 7, 12)),
            ('employee_id', '=', self.empl_employee.id),
        ])
        self.assertEqual(len(timesheet), 1, "One timesheet should be created")
        self.assertEqual(sum(timesheet.mapped('unit_amount')), 10, "The duration of the timesheet for flexible employee leave "
                                                        "should be 10 hours")

    def test_timeoff_validation_fully_flexible_employee(self):
        self.empl_employee.resource_calendar_id = False

        time_off = self.Requests.with_user(self.user_employee).create({
            'name': 'Test Fully Flexible Employee Validation',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': datetime(2025, 8, 12),
            'request_date_to': datetime(2025, 8, 12)
        })
        time_off.with_user(SUPERUSER_ID)._action_validate()

        self.assertEqual(time_off.state, 'validate', "The time off for a fully flexible employee should be validated")
