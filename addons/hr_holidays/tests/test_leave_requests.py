# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
import time
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.tests.common import Form
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon

@tagged('leave_requests')
class TestLeaveRequests(TestHrHolidaysCommon):

    def _check_holidays_status(self, holiday_status, ml, lt, rl, vrl):
            self.assertEqual(holiday_status.max_leaves, ml,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.leaves_taken, lt,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.remaining_leaves, rl,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.virtual_remaining_leaves, vrl,
                             'hr_holidays: wrong type days computation')

    def setUp(self):
        super(TestLeaveRequests, self).setUp()

        # Make sure we have the rights to create, validate and delete the leaves, leave types and allocations
        LeaveType = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.holidays_type_1 = LeaveType.create({
            'name': 'NotLimitedHR',
            'requires_allocation': 'no',
            'leave_validation_type': 'hr',
        })
        self.holidays_type_2 = LeaveType.create({
            'name': 'Limited',
            'requires_allocation': 'yes',
            'employee_requests': 'yes',
            'leave_validation_type': 'hr',
        })
        self.holidays_type_3 = LeaveType.create({
            'name': 'TimeNotLimited',
            'requires_allocation': 'no',
            'leave_validation_type': 'manager',
        })

        self.set_employee_create_date(self.employee_emp_id, '2010-02-03 00:00:00')
        self.set_employee_create_date(self.employee_hruser_id, '2010-02-03 00:00:00')

    def set_employee_create_date(self, id, newdate):
        """ This method is a hack in order to be able to define/redefine the create_date
            of the employees.
            This is done in SQL because ORM does not allow to write onto the create_date field.
        """
        self.env.cr.execute("""
                       UPDATE
                       hr_employee
                       SET create_date = '%s'
                       WHERE id = %s
                       """ % (newdate, id))

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_overlapping_requests(self):
        """  Employee cannot create a new leave request at the same time, avoid interlapping  """
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Hol21',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_1.id,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days': 1,
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_limited_type_no_days(self):
        """  Employee creates a leave request in a limited category but has not enough days left  """

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Hol22',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': (datetime.today() + relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': (datetime.today() + relativedelta(days=2)),
                'number_of_days': 1,
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_limited_type_days_left(self):
        """  Employee creates a leave request in a limited category and has enough days left  """
        aloc1_user_group = self.env['hr.leave.allocation'].with_user(self.user_hruser_id).create({
            'name': 'Days for limited category',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 2,
            'state': 'confirm',
            'date_from': time.strftime('%Y-1-1'),
            'date_to': time.strftime('%Y-12-31'),
        })
        aloc1_user_group.action_validate()

        holiday_status = self.holidays_type_2.with_user(self.user_employee_id)
        self._check_holidays_status(holiday_status, 2.0, 0.0, 2.0, 2.0)

        hol = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': (datetime.today() - relativedelta(days=2)),
            'date_to': datetime.today(),
            'number_of_days': 2,
        })

        holiday_status.invalidate_cache()
        self._check_holidays_status(holiday_status, 2.0, 0.0, 2.0, 0.0)

        hol.with_user(self.user_hrmanager_id).action_approve()

        holiday_status.invalidate_cache(['max_leaves'])
        self._check_holidays_status(holiday_status, 2.0, 2.0, 0.0, 0.0)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_accrual_validity_time_valid(self):
        """  Employee ask leave during a valid validity time """

        self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Sick Time Off',
                'holiday_status_id': self.holidays_type_2.id,
                'employee_id': self.employee_emp.id,
                'date_from': fields.Datetime.from_string('2017-01-01 00:00:00'),
                'date_to': fields.Datetime.from_string('2017-06-01 00:00:00'),
                'number_of_days': 10,
                'state': 'validate',
        })

        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Valid time period',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': fields.Datetime.from_string('2017-03-03 06:00:00'),
            'date_to': fields.Datetime.from_string('2017-03-11 19:00:00'),
            'number_of_days': 1,
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_accrual_validity_time_not_valid(self):
        """  Employee ask leave when there's no valid allocation """
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee).create({
                'name': 'Sick Time Off',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': fields.Datetime.from_string('2017-07-03 06:00:00'),
                'date_to': fields.Datetime.from_string('2017-07-11 19:00:00'),
                'number_of_days': 1,
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_department_leave(self):
        """ Create a department leave """
        self.employee_hrmanager.write({'department_id': self.hr_dept.id})
        self.assertFalse(self.env['hr.leave'].search([('employee_id', 'in', self.hr_dept.member_ids.ids)]))
        leave_form = Form(self.env['hr.leave'].with_user(self.user_hrmanager), view='hr_holidays.hr_leave_view_form_manager')
        leave_form.holiday_type = 'department'
        leave_form.department_id = self.hr_dept
        leave_form.holiday_status_id = self.holidays_type_1
        leave_form.request_date_from = date(2019, 5, 6)
        leave_form.request_date_to = date(2019, 5, 6)
        leave = leave_form.save()
        leave.action_approve()
        member_ids = self.hr_dept.member_ids.ids
        self.assertEqual(self.env['hr.leave'].search_count([('employee_id', 'in', member_ids)]), len(member_ids), "Leave should be created for members of department")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_allocation_request(self):
        """ Create an allocation request """
        # employee should be set to current user
        allocation_form = Form(self.env['hr.leave.allocation'].with_user(self.user_employee))
        allocation_form.name = 'New Allocation Request'
        allocation_form.holiday_status_id = self.holidays_type_2
        allocation_form.date_from = date(2019, 5, 6)
        allocation_form.date_to = date(2019, 5, 6)
        allocation = allocation_form.save()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_employee_is_absent(self):
        """ Only the concerned employee should be considered absent """
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': (fields.Datetime.now() - relativedelta(days=1)),
            'date_to': fields.Datetime.now() + relativedelta(days=1),
            'number_of_days': 2,
        })
        (self.employee_emp | self.employee_hrmanager).mapped('is_absent')  # compute in batch
        self.assertTrue(self.employee_emp.is_absent, "He should be considered absent")
        self.assertFalse(self.employee_hrmanager.is_absent, "He should not be considered absent")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_employee_leave_request(self):
        """ Create a leave request for an employee in another timezone """
        self.employee_emp.tz = 'NZ'  # GMT+12
        leave = self.env['hr.leave'].new({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_unit_hours': True,
            'request_date_from': date(2019, 5, 6),
            'request_date_to': date(2019, 5, 6),
            'request_hour_from': '8',  # 8:00 AM in the employee's timezone
            'request_hour_to': '17',  # 5:00 PM in the employee's timezone
        })
        self.assertEqual(leave.date_from, datetime(2019, 5, 5, 20, 0, 0), "It should have been localized before saving in UTC")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 5, 0, 0), "It should have been localized before saving in UTC")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_company_leave_request(self):
        """ Create a leave request for a company in another timezone """
        company = self.env['res.company'].create({'name': "Hergé"})
        company.resource_calendar_id.tz = 'NZ'  # GMT+12
        leave = self.env['hr.leave'].new({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_unit_hours': True,
            'holiday_type': 'company',
            'mode_company_id': company.id,
            'request_date_from': date(2019, 5, 6),
            'request_date_to': date(2019, 5, 6),
            'request_hour_from': '8',  # 8:00 AM in the company's timezone
            'request_hour_to': '17',  # 5:00 PM in the company's timezone
        })
        self.assertEqual(leave.date_from, datetime(2019, 5, 5, 20, 0, 0), "It should have been localized before saving in UTC")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 5, 0, 0), "It should have been localized before saving in UTC")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_company_validated(self):
        """ Create a leave request for a company in another timezone and validate it """
        self.env.user.tz = 'NZ' # GMT+12
        company = self.env['res.company'].create({'name': "Hergé"})
        employee = self.env['hr.employee'].create({'name': "Remi", 'company_id': company.id})
        leave_form = Form(self.env['hr.leave'], view='hr_holidays.hr_leave_view_form_manager')
        leave_form.holiday_type = 'company'
        leave_form.mode_company_id = company
        leave_form.holiday_status_id = self.holidays_type_1
        leave_form.request_date_from = date(2019, 5, 6)
        leave_form.request_date_to = date(2019, 5, 6)
        leave = leave_form.save()
        leave.state = 'confirm'
        leave.action_validate()
        employee_leave = self.env['hr.leave'].search([('employee_id', '=', employee.id)])
        self.assertEqual(
            employee_leave.request_date_from, date(2019, 5, 6),
            "Timezone should be kept between company and employee leave"
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_department_leave_request(self):
        """ Create a leave request for a department in another timezone """
        company = self.env['res.company'].create({'name': "Hergé"})
        company.resource_calendar_id.tz = 'NZ'  # GMT+12
        department = self.env['hr.department'].create({'name': "Museum", 'company_id': company.id})
        leave = self.env['hr.leave'].new({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_unit_hours': True,
            'holiday_type': 'department',
            'department_id': department.id,
            'request_date_from': date(2019, 5, 6),
            'request_date_to': date(2019, 5, 6),
            'request_hour_from': '8',  # 8:00 AM in the department's timezone
            'request_hour_to': '17',  # 5:00 PM in the department's timezone
        })
        self.assertEqual(leave.date_from, datetime(2019, 5, 5, 20, 0, 0), "It should have been localized before saving in UTC")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 5, 0, 0), "It should have been localized before saving in UTC")

    def test_number_of_hours_display(self):
        # Test that the field number_of_hours_dispay doesn't change
        # after time off validation, as it takes the attendances
        # minus the resource leaves to compute that field.
        calendar = self.env['resource.calendar'].create({
            'name': 'Monday Morning Else Full Time 38h/week',
            'hours_per_day': 7.6,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'})
            ],
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        self.env.user.company_id.resource_calendar_id = calendar
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
        })
        allocation = self.env['hr.leave.allocation'].create({
            'name': '20 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 20,
            'employee_id': employee.id,
            'state': 'confirm',
            'date_from': time.strftime('2018-1-1'),
            'date_to': time.strftime('%Y-1-1'),
        })
        allocation.action_validate()

        leave1 = self.env['hr.leave'].create({
            'name': 'Holiday 1 week',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'date_from': fields.Datetime.from_string('2019-12-23 06:00:00'),
            'date_to': fields.Datetime.from_string('2019-12-27 20:00:00'),
            'number_of_days': 5,
        })

        self.assertEqual(leave1.number_of_hours_display, 38)
        leave1.action_approve()
        self.assertEqual(leave1.number_of_hours_display, 38)
        leave1.action_validate()
        self.assertEqual(leave1.number_of_hours_display, 38)

        leave2 = self.env['hr.leave'].create({
            'name': 'Holiday 1 Day',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'date_from': fields.Datetime.from_string('2019-12-30 06:00:00'),
            'date_to': fields.Datetime.from_string('2019-12-30 13:00:00'),
            'number_of_days': 1,
        })

        self.assertEqual(leave2.number_of_hours_display, 4)
        leave2.action_approve()
        self.assertEqual(leave2.number_of_hours_display, 4)
        leave2.action_validate()
        self.assertEqual(leave2.number_of_hours_display, 4)

    def test_number_of_hours_display_global_leave(self):
        # Check that the field number_of_hours_display
        # takes the global leaves into account, even
        # after validation
        calendar = self.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ],
            'global_leave_ids': [(0, 0, {
                'name': 'Christmas Leave',
                'date_from': fields.Datetime.from_string('2019-12-25 00:00:00'),
                'date_to': fields.Datetime.from_string('2019-12-26 23:59:59'),
                'resource_id': False,
                'time_type': 'leave',
            })]
        })
        employee = self.employee_emp
        employee.resource_calendar_id = calendar
        self.env.user.company_id.resource_calendar_id = calendar
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': 'no',
        })
        leave1 = self.env['hr.leave'].create({
            'name': 'Sick 1 week during christmas snif',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'date_from': fields.Datetime.from_string('2019-12-23 06:00:00'),
            'date_to': fields.Datetime.from_string('2019-12-27 20:00:00'),
            'number_of_days': 5,
        })
        self.assertEqual(leave1.number_of_hours_display, 24)
        leave1.action_approve()
        self.assertEqual(leave1.number_of_hours_display, 24)
        leave1.action_validate()
        self.assertEqual(leave1.number_of_hours_display, 24)

    def _test_leave_with_tz(self, tz, local_date_from, local_date_to, number_of_days):
        self.user_employee.tz = tz
        tz = timezone(tz)

        # Mimic what is done by the calendar widget when clicking on a day. It
        # will take the local datetime from 7:00 to 19:00 and then convert it
        # to UTC before sending it. Values here are for PST (UTC -8) and
        # represent a leave on 2019/1/1 from 7:00 to 19:00 local time.
        values = {
            'date_from': tz.localize(local_date_from).astimezone(UTC).replace(tzinfo=None),
            'date_to': tz.localize(local_date_to).astimezone(UTC).replace(tzinfo=None),  # note that this can be the next day in UTC
        }
        values.update(self.env['hr.leave'].with_user(self.user_employee_id)._default_get_request_parameters(values))

        # Dates should be local to the user
        self.assertEqual(values['request_date_from'], local_date_from.date())
        self.assertEqual(values['request_date_to'], local_date_to.date())

        values.update({
            'name': 'Test',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
        })
        leave = self.env['hr.leave'].with_user(self.user_employee_id).new(values)
        self.assertEqual(leave.number_of_days, number_of_days)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_defaults_with_timezones(self):
        """ Make sure that leaves start with correct defaults for non-UTC timezones """
        timezones_to_test = ('UTC', 'Pacific/Midway', 'US/Pacific', 'Asia/Taipei', 'Pacific/Kiritimati')  # UTC, UTC -11, UTC -8, UTC +8, UTC +14

        #     January 2020
        # Su Mo Tu We Th Fr Sa
        #           1  2  3  4
        #  5  6  7  8  9 10 11
        # 12 13 14 15 16 17 18
        # 19 20 21 22 23 24 25
        # 26 27 28 29 30 31
        local_date_from = datetime(2020, 1, 1, 7, 0, 0)
        local_date_to = datetime(2020, 1, 1, 19, 0, 0)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 1)

        # We, Th, Fr, Mo, Tu, We => 6 days
        local_date_from = datetime(2020, 1, 1, 7, 0, 0)
        local_date_to = datetime(2020, 1, 8, 19, 0, 0)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 6)#TODO JUD check why this fails

    def test_expired_allocation(self):
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        allocation.action_validate()

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': '2021-09-01',
                'date_to': '2021-09-02',
                'number_of_days': 1,
            })
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': '2020-09-01',
            'date_to': '2020-09-02',
            'number_of_days': 1,
        })

    def test_no_days_expired(self):
        # First expired allocation
        allocation1 = self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        allocation2 = self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 3,
            'state': 'confirm',
            'date_from': '2021-01-01',
            'date_to': '2021-12-31',
        })
        allocation1.action_validate()
        allocation2.action_validate()
        # Try creating a request that could be validated if allocation1 was still valid
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': '2021-09-06',
                'date_to': '2021-09-10',
                'number_of_days': 5,
            })
        # This time we have enough days
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-08',
            'number_of_days': 3,
        })
