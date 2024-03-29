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

    def test_status_create(self):
        """Ensure that when a status is created, it fullfills the project and task constrains"""
        status = self.env['hr.leave.type'].create({
            'name': 'A nice Time Off Type',
            'requires_allocation': 'no'
        })

        self.assertEqual(status.timesheet_project_id, status.company_id.internal_project_id, 'The default project linked to the status should be the same as the company')
        self.assertEqual(status.timesheet_task_id, status.company_id.leave_timesheet_task_id, 'The default task linked to the status should be the same as the company')

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
        super(TestTimesheetHolidays, self).setUp()

        self.employee_working_calendar = self.empl_employee.resource_calendar_id
        # leave dates : from next monday to next wednesday (to avoid crashing tests on weekend, when
        # there is no work days in working calendar)
        # NOTE: second and millisecond can add a working days
        self.leave_start_datetime = datetime(2018, 2, 5)  # this is monday
        self.leave_end_datetime = self.leave_start_datetime + relativedelta(days=2)

        # all company have those internal project/task (created by default)
        self.internal_project = self.env.company.internal_project_id
        self.internal_task_leaves = self.env.company.leave_timesheet_task_id

        self.hr_leave_type_with_ts = self.env['hr.leave.type'].create({
            'name': 'Time Off Type with timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.internal_project.id,
            'timesheet_task_id': self.internal_task_leaves.id,
        })
        self.hr_leave_type_no_ts = self.env['hr.leave.type'].create({
            'name': 'Time Off Type without timesheet generation',
            'requires_allocation': 'no',
            'timesheet_generate': False,
            'timesheet_project_id': False,
            'timesheet_task_id': False,
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
        self.hr_leave_allocation_no_ts = self.Allocations.sudo().create({
            'name': 'Days for limited category without timesheet',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_no_ts.id,
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
        holiday.with_user(SUPERUSER_ID).action_validate()

        # The leave type and timesheet are linked to the same project and task of hr_leave_type_with_ts as the company is set
        self.assertEqual(holiday.timesheet_ids.project_id.id, self.hr_leave_type_with_ts.timesheet_project_id.id)
        self.assertEqual(holiday.timesheet_ids.task_id.id, self.hr_leave_type_with_ts.timesheet_task_id.id)

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
        self.assertTrue(hr_leave_type_with_ts_without_company.timesheet_generate)

        holiday = self.Requests.create({
            'name': 'Time Off 2',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': hr_leave_type_with_ts_without_company.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()

        # The leave type and timesheet are linked to the same project and task of the employee company as the company is not set
        self.assertEqual(holiday.timesheet_ids.project_id.id, company.internal_project_id.id)
        self.assertEqual(holiday.timesheet_ids.task_id.id, company.leave_timesheet_task_id.id)

    def test_validate_without_timesheet(self):
        # employee creates a leave request
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_no_ts.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), 0, 'Number of generated timesheets should be zero since the leave type does not generate timesheet')

    @freeze_time('2018-02-05')  # useful to be able to cancel the validated time off
    def test_cancel_validate_holidays(self):
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Time Off 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'request_date_from': self.leave_start_datetime,
            'request_date_to': self.leave_end_datetime,
        })
        holiday.with_user(self.env.user).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), holiday.number_of_days, 'Number of generated timesheets should be the same as the leave duration (1 per day between %s and %s)' % (fields.Datetime.to_string(self.leave_start_datetime), fields.Datetime.to_string(self.leave_end_datetime)))

        self.env['hr.holidays.cancel.leave'].with_user(self.user_employee).with_context(default_leave_id=holiday.id) \
            .new({'reason': 'Test remove holiday'}) \
            .action_cancel_leave()
        self.assertFalse(holiday.active, 'The time off should be archived')
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
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), 4, '4 timesheets should be generated for this time off.')

        timesheets = self.env['account.analytic.line'].search([
            ('date', '>=', leave_start_datetime),
            ('date', '<=', leave_end_datetime),
            ('employee_id', '=', self.empl_employee.id),
        ])

        # should not able to update timeoff timesheets
        with self.assertRaises(UserError):
            timesheets.with_user(self.empl_employee).write({'task_id': 4})

        # should not able to create timesheet in timeoff task
        with self.assertRaises(UserError):
            self.env['account.analytic.line'].with_user(self.empl_employee).create({
                'name': "my timesheet",
                'project_id': self.internal_project.id,
                'task_id': self.internal_task_leaves.id,
                'date': '2021-10-04',
                'unit_amount': 8.0,
            })

        self.assertEqual(len(timesheets.filtered('holiday_id')), 4, "4 timesheet should be linked to employee's timeoff")
        self.assertEqual(len(timesheets.filtered('global_leave_id')), 1, '1 timesheet should be linked to global leave')
