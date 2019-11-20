# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, SUPERUSER_ID

from odoo.tests import common, new_test_user
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestTimesheetHolidaysCreate(common.TransactionCase):

    def test_status_create(self):
        """Ensure that when a status is created, it fullfills the project and task constrains"""
        status = self.env['hr.leave.type'].create({
            'name': 'A nice Leave Type',
            'allocation_type': 'no'
        })

        company = self.env.company
        self.assertEqual(status.timesheet_project_id, company.leave_timesheet_project_id, 'The default project linked to the status should be the same as the company')
        self.assertEqual(status.timesheet_task_id, company.leave_timesheet_task_id, 'The default task linked to the status should be the same as the company')

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
        self.assertEqual(company.leave_timesheet_project_id.sudo().company_id, company, "It should have created a project for the company")

class TestTimesheetHolidays(TestCommonTimesheet):

    def setUp(self):
        super(TestTimesheetHolidays, self).setUp()

        self.employee_working_calendar = self.empl_employee.resource_calendar_id
        # leave dates : from next monday to next wednesday (to avoid crashing tests on weekend, when
        # there is no work days in working calendar)
        # NOTE: second and millisecond can add a working days
        self.leave_start_datetime = datetime(2018, 2, 5, 7, 0, 0, 0)  # this is monday
        self.leave_end_datetime = self.leave_start_datetime + relativedelta(days=3)

        # all company have those internal project/task (created by default)
        self.internal_project = self.env.company.leave_timesheet_project_id
        self.internal_task_leaves = self.env.company.leave_timesheet_task_id

        self.hr_leave_type_with_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'allocation_type': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.internal_project.id,
            'timesheet_task_id': self.internal_task_leaves.id,
            'validity_start': False,
        })
        self.hr_leave_type_no_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type without timesheet generation',
            'allocation_type': 'no',
            'timesheet_generate': False,
            'timesheet_project_id': False,
            'timesheet_task_id': False,
            'validity_start': False,
        })

        # HR Officer allocates some leaves to the employee 1
        self.Requests = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True)
        self.Allocations = self.env['hr.leave.allocation'].with_context(mail_create_nolog=True, mail_notrack=True)
        self.hr_leave_allocation_with_ts = self.Allocations.sudo().create({
            'name': 'Days for limited category with timesheet',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'number_of_days': 10,
        })
        self.hr_leave_allocation_with_ts.action_approve()
        self.hr_leave_allocation_no_ts = self.Allocations.sudo().create({
            'name': 'Days for limited category without timesheet',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_no_ts.id,
            'number_of_days': 10,
        })
        self.hr_leave_allocation_no_ts.action_approve()

    def test_validate_with_timesheet(self):
        # employee creates a leave request
        number_of_days = (self.leave_end_datetime - self.leave_start_datetime).days
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'date_from': self.leave_start_datetime,
            'date_to': self.leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), number_of_days, 'Number of generated timesheets should be the same as the leave duration (1 per day between %s and %s)' % (fields.Datetime.to_string(self.leave_start_datetime), fields.Datetime.to_string(self.leave_end_datetime)))

        # manager refuse the leave
        holiday.with_user(SUPERUSER_ID).action_refuse()
        self.assertEqual(len(holiday.timesheet_ids), 0, 'Number of linked timesheets should be zero, since the leave is refused.')

    def test_validate_without_timesheet(self):
        # employee creates a leave request
        number_of_days = (self.leave_end_datetime - self.leave_start_datetime).days
        holiday = self.Requests.with_user(self.user_employee).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_no_ts.id,
            'date_from': self.leave_start_datetime,
            'date_to': self.leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.with_user(SUPERUSER_ID).action_validate()
        self.assertEqual(len(holiday.timesheet_ids), 0, 'Number of generated timesheets should be zero since the leave type does not generate timesheet')
