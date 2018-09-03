# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.tests import common
from odoo.addons.hr_timesheet.tests.test_timesheet import TestTimesheet


class TestTimesheetHolidaysCreate(common.TransactionCase):

    def test_status_create(self):
        """Ensure that when a status is created, it fullfills the project and task constrains"""
        status = self.env['hr.leave.type'].create({
            'name': 'A nice Leave Type',
            'allocation_type': 'no'
        })

        company = self.env.user.company_id
        self.assertEqual(status.timesheet_project_id, company.leave_timesheet_project_id, 'The default project linked to the status should be the same as the company')
        self.assertEqual(status.timesheet_task_id, company.leave_timesheet_task_id, 'The default task linked to the status should be the same as the company')


class TestTimesheetHolidays(TestTimesheet):

    def setUp(self):
        super(TestTimesheetHolidays, self).setUp()

        self.employee_working_calendar = self.empl_employee.resource_calendar_id
        # leave dates : from next monday to next wednesday (to avoid crashing tests on weekend, when
        # there is no work days in working calendar)
        # NOTE: second and millisecond can add a working days
        self.leave_start_datetime = datetime(2018, 2, 5, 7, 0, 0, 0)  # this is monday
        self.leave_end_datetime = self.leave_start_datetime + relativedelta(days=3)

        # all company have those internal project/task (created by default)
        self.internal_project = self.env.user.company_id.leave_timesheet_project_id
        self.internal_task_leaves = self.env.user.company_id.leave_timesheet_task_id

        self.hr_leave_type_with_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type with timesheet generation',
            'allocation_type': 'no',
            'timesheet_generate': True,
            'timesheet_project_id': self.internal_project.id,
            'timesheet_task_id': self.internal_task_leaves.id,
        })
        self.hr_leave_type_no_ts = self.env['hr.leave.type'].create({
            'name': 'Leave Type without timesheet generation',
            'allocation_type': 'no',
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
        holiday = self.Requests.sudo(self.user_employee.id).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_with_ts.id,
            'date_from': self.leave_start_datetime,
            'date_to': self.leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.sudo().action_validate()
        self.assertEquals(len(holiday.timesheet_ids), number_of_days, 'Number of generated timesheets should be the same as the leave duration (1 per day between %s and %s)' % (fields.Datetime.to_string(self.leave_start_datetime), fields.Datetime.to_string(self.leave_end_datetime)))

        # manager refuse the leave
        holiday.sudo().action_refuse()
        self.assertEquals(len(holiday.timesheet_ids), 0, 'Number of linked timesheets should be zero, since the leave is refused.')

    def test_validate_without_timesheet(self):
        # employee creates a leave request
        number_of_days = (self.leave_end_datetime - self.leave_start_datetime).days
        holiday = self.Requests.sudo(self.user_employee.id).create({
            'name': 'Leave 1',
            'employee_id': self.empl_employee.id,
            'holiday_status_id': self.hr_leave_type_no_ts.id,
            'date_from': self.leave_start_datetime,
            'date_to': self.leave_end_datetime,
            'number_of_days': number_of_days,
        })
        holiday.sudo().action_validate()
        self.assertEquals(len(holiday.timesheet_ids), 0, 'Number of generated timesheets should be zero since the leave type does not generate timesheet')
