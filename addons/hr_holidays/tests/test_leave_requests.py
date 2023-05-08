# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
import time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from pytz import timezone, UTC

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.tests.common import Form
from odoo.tests import tagged

from odoo.exceptions import UserError

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

    @classmethod
    def setUpClass(cls):
        super(TestLeaveRequests, cls).setUpClass()

        # Make sure we have the rights to create, validate and delete the leaves, leave types and allocations
        LeaveType = cls.env['hr.leave.type'].with_user(cls.user_hrmanager_id).with_context(tracking_disable=True)

        cls.holidays_type_1 = LeaveType.create({
            'name': 'NotLimitedHR',
            'requires_allocation': 'no',
            'leave_validation_type': 'hr',
        })
        cls.holidays_type_2 = LeaveType.create({
            'name': 'Limited',
            'requires_allocation': 'yes',
            'employee_requests': 'yes',
            'leave_validation_type': 'hr',
        })
        cls.holidays_type_3 = LeaveType.create({
            'name': 'TimeNotLimited',
            'requires_allocation': 'no',
            'leave_validation_type': 'manager',
        })

        cls.holidays_type_4 = LeaveType.create({
            'name': 'Limited with 2 approvals',
            'requires_allocation': 'yes',
            'employee_requests': 'yes',
            'leave_validation_type': 'both',
        })
        cls.holidays_support_document = LeaveType.create({
            'name': 'Time off with support document',
            'support_document': True,
            'requires_allocation': 'no',
            'leave_validation_type': 'no_validation',
        })

        cls.set_employee_create_date(cls.employee_emp_id, '2010-02-03 00:00:00')
        cls.set_employee_create_date(cls.employee_hruser_id, '2010-02-03 00:00:00')

    def _check_holidays_count(self, holidays_count_result, ml, lt, rl, vrl, vlt, closest_allocation):
        self.assertEqual(
            holidays_count_result,
            {
                'closest_allocation_to_expire': closest_allocation,
                'max_leaves': ml,
                'leaves_taken': lt,
                'remaining_leaves': rl,
                'virtual_remaining_leaves': vrl,
                'virtual_leaves_taken': vlt,
            }
        )


    @classmethod
    def set_employee_create_date(cls, _id, newdate):
        """ This method is a hack in order to be able to define/redefine the create_date
            of the employees.
            This is done in SQL because ORM does not allow to write onto the create_date field.
        """
        cls.env.cr.execute("""
                       UPDATE
                       hr_employee
                       SET create_date = '%s'
                       WHERE id = %s
                       """ % (newdate, _id))

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
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        return

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_limited_type_days_left(self):
        """  Employee creates a leave request in a limited category and has enough days left  """
        with freeze_time('2022-01-05'):
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

            holiday_status.invalidate_model()
            self._check_holidays_status(holiday_status, 2.0, 0.0, 2.0, 0.0)

            hol.with_user(self.user_hrmanager_id).action_approve()

            holiday_status.invalidate_model(['max_leaves'])
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
        }).action_validate()

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
        # Deprecated as part of https://github.com/odoo/odoo/pull/96545
        # TODO: remove in master
        return

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
        user_employee_leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': (fields.Datetime.now() - relativedelta(days=1)),
            'date_to': fields.Datetime.now() + relativedelta(days=1),
            'number_of_days': 2,
        })
        (self.employee_emp | self.employee_hrmanager).mapped('is_absent')  # compute in batch
        self.assertFalse(self.employee_emp.is_absent, "He should not be considered absent")
        self.assertFalse(self.employee_hrmanager.is_absent, "He should not be considered absent")

        user_employee_leave.sudo().write({
            'state': 'validate',
        })
        (self.employee_emp | self.employee_hrmanager)._compute_leave_status()
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
        self.assertEqual(leave.date_from, datetime(2019, 5, 6, 6, 0, 0), "It should have been localized in the Employee timezone")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 15, 0, 0), "It should have been localized in the Employee timezone")

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
        # TODO: The test is wrong by modifying `date_from` and `date_to`, which are invisible
        # It should edit only `request_date_from` and `request_date_to` instead
        # And there is really a bug. Using the web client, when you put your PC in Auckland timezone,
        # and the admin preferences in Auckland Timezone
        # and create a time off for the current day, the computation is completely wrong
        # and compute the date to before the date from *-)
        # For instance, for a time-off from 06/16/2022 to 06/16/2022 (1 day) it computes
        # 06/16/2022 08:00:00 as date_from and 06/15/2022 17:00:00 as date_to
        # Bug reported to the rd-fun-vidange channel to the dev who introduced the bug
        # https://discord.com/channels/678381219515465750/687337760452902925/986918361768263710
        leave_form._view['modifiers']['date_from']['invisible'] = False
        leave_form._view['modifiers']['date_to']['invisible'] = False
        leave_form.date_from = datetime(2019, 5, 6, 0, 0, 0)
        leave_form.date_to = datetime(2019, 5, 6, 23, 59, 59)
        leave = leave_form.save()
        leave.state = 'confirm'
        leave.action_validate()
        employee_leave = self.env['hr.leave'].search([('employee_id', '=', employee.id)])
        self.assertEqual(
            employee_leave.request_date_from, date(2019, 5, 5),
            "Timezone should be be adapted on the employee leave"
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
        self.assertEqual(leave.date_from, datetime(2019, 5, 6, 6, 0, 0), "It should have been localized in the Employee timezone")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 15, 0, 0), "It should have been localized in the Employee timezone")

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
        # will take the local datetime from 0:00 to 23:59
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
        local_date_from = datetime(2020, 1, 1, 0, 0, 0)
        local_date_to = datetime(2020, 1, 1, 23, 59, 59)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 1)

        # We, Th, Fr, Mo, Tu, We => 6 days
        local_date_from = datetime(2020, 1, 1, 0, 0, 0)
        local_date_to = datetime(2020, 1, 8, 23, 59, 59)
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

    def test_company_leaves(self):
        # First expired allocation
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'holiday_type': 'company',
            'mode_company_id': self.env.company.id,
            'holiday_status_id': self.holidays_type_1.id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2021-01-01',
        })
        allocation.action_validate()

        req1_form = Form(self.env['hr.leave'].sudo())
        req1_form.employee_ids.add(self.employee_emp)
        req1_form.employee_ids.add(self.employee_hrmanager)
        req1_form.holiday_status_id = self.holidays_type_1
        req1_form.request_date_from = fields.Date.to_date('2021-12-06')
        req1_form.request_date_to = fields.Date.to_date('2021-12-08')

        self.assertEqual(req1_form.number_of_days_display, 3)
        req1_form.save().action_approve()

        req2_form = Form(self.env['hr.leave'].sudo())
        req2_form.employee_ids.add(self.employee_hruser)
        req2_form.holiday_status_id = self.holidays_type_1
        req2_form.request_date_from = fields.Date.to_date('2021-12-06')
        req2_form.request_date_to = fields.Date.to_date('2021-12-08')

        self.assertEqual(req2_form.number_of_days_display, 3)

    def test_leave_with_public_holiday_other_company(self):
        other_company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        # Create a public holiday for the second company
        p_leave = self.env['resource.calendar.leaves'].create({
            'date_from': datetime(2022, 3, 11),
            'date_to': datetime(2022, 3, 11, 23, 59, 59),
        })
        p_leave.company_id = other_company

        leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'holiday_type': 'employee',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': datetime(2022, 3, 11),
            'date_to': datetime(2022, 3, 11, 23, 59, 59),
        })
        self.assertEqual(leave.number_of_days, 1)

    def test_several_allocations(self):
        allocation_vals = {
            'name': 'Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 5,
            'state': 'confirm',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
        }
        allocation1 = self.env['hr.leave.allocation'].create(allocation_vals)
        allocation2 = self.env['hr.leave.allocation'].create(allocation_vals)

        allocation1.action_validate()
        allocation2.action_validate()

        # Able to create a leave of 10 days with two allocations of 5 days
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': '2022-01-01',
            'date_to': '2022-01-15',
            'number_of_days': 10,
        })

    def test_several_allocations_split(self):
        Allocation = self.env['hr.leave.allocation']
        allocation_vals = {
            'name': 'Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'state': 'confirm',
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
        }
        Leave = self.env['hr.leave'].with_user(self.user_employee_id).sudo()
        leave_vals = {
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
        }

        for unit in ['hour', 'day']:
            self.holidays_type_2.request_unit = unit

            allocation_vals.update({'number_of_days': 4})
            allocation_4days = Allocation.create(allocation_vals)
            allocation_vals.update({'number_of_days': 1})
            allocation_1day = Allocation.create(allocation_vals)
            allocations = (allocation_4days + allocation_1day)
            allocations.action_validate()

            leave_vals.update({
                'date_from': '2022-01-03 00:00:00',
                'date_to': '2022-01-06 23:59:59',
                'number_of_days': 4,
            })
            leave_draft = Leave.create(leave_vals)
            leave_draft.action_refuse()
            leave_vals.update({
                'date_from': '2022-01-03 00:00:00',
                'date_to': '2022-01-06 23:59:59',
                'number_of_days': 4,
            })
            leave_4days = Leave.create(leave_vals)
            leave_vals.update({
                'date_from': '2022-01-07 00:00:00',
                'date_to': '2022-01-07 23:59:59',
                'number_of_days': 1,
            })
            leave_1day = Leave.create(leave_vals)
            leaves = (leave_4days + leave_1day)
            leaves.action_approve()

            allocation_days = self.holidays_type_2._get_employees_days_per_allocation([self.employee_emp_id])

            self.assertEqual(allocation_days[self.employee_emp_id][self.holidays_type_2][allocation_4days]['leaves_taken'], leave_4days['number_of_%ss_display' % unit], 'As 4 days were available in this allocation, they should have been taken')
            self.assertEqual(allocation_days[self.employee_emp_id][self.holidays_type_2][allocation_1day]['leaves_taken'], leave_1day['number_of_%ss_display' % unit], 'As no days were available in previous allocation, they should have been taken in this one')
            leaves.action_refuse()
            allocations.action_refuse()

    def test_time_off_recovery_on_create(self):
        time_off = self.env['hr.leave'].create([
            {
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_1.id,
                'date_from': '2021-12-06 00:00:00',
                'date_to': '2021-12-10 23:59:59',
            },
            {
                'name': 'Holiday Request',
                'employee_id': self.employee_hruser_id,
                'holiday_status_id': self.holidays_type_1.id,
                'date_from': '2021-12-06 00:00:00',
                'date_to': '2021-12-10 23:59:59',
            }
        ])
        self.assertEqual(time_off[0].number_of_days, 5)
        self.assertEqual(time_off[1].number_of_days, 5)
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': '2021-12-07 00:00:00',
            'date_to': '2021-12-07 23:59:59',
        })
        self.assertEqual(time_off[0].number_of_days, 4)
        self.assertEqual(time_off[1].number_of_days, 4)

    def test_time_off_recovery_on_write(self):
        global_time_off = self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': '2021-12-07 00:00:00',
            'date_to': '2021-12-07 23:59:59',
        })

        time_off_1 = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': '2021-12-06 00:00:00',
            'date_to': '2021-12-10 23:59:59',
        })
        self.assertEqual(time_off_1.number_of_days, 4)

        time_off_2 = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': '2021-12-13 00:00:00',
            'date_to': '2021-12-17 23:59:59',
        })
        self.assertEqual(time_off_2.number_of_days, 5)

        # adding 1 day to the global time off
        global_time_off.write({
            'date_to': '2021-12-08 23:59:59',
        })
        self.assertEqual(time_off_1.number_of_days, 3)

        # moving the global time off to the next week
        global_time_off.write({
            'date_from': '2021-12-15 00:00:00',
            'date_to': '2021-12-15 23:59:59',
        })
        self.assertEqual(time_off_1.number_of_days, 2)
        self.assertEqual(time_off_2.number_of_days, 4)

    def test_time_off_recovery_on_unlink(self):
        global_time_off = self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': '2021-12-07 00:00:00',
            'date_to': '2021-12-07 23:59:59',
        })
        time_off = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': '2021-12-06 00:00:00',
            'date_to': '2021-12-10 23:59:59',
        })
        self.assertEqual(time_off.number_of_days, 4)
        global_time_off.unlink()
        self.assertEqual(time_off.number_of_days, 3)

    def test_time_off_auto_cancel(self):
        time_off = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': '2021-11-15 00:00:00',
            'date_to': '2021-11-19 23:59:59',
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': '2021-11-15 00:00:00',
            'date_to': '2021-11-19 23:59:59',
        })
        self.assertEqual(time_off.active, False)
    def test_holiday_type_requires_no_allocation(self):
        # holiday_type_2 initially requires an allocation
        # Once an allocation is granted and a leave is taken,
        # the holiday type is changed to no longer require an allocation.
        # Leaves taken and available days should be correctly computed.
        with freeze_time('2020-09-15'):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Expired Allocation',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 5,
                'state': 'confirm',
                'date_from': '2020-01-01',
                'date_to': '2020-12-31',
            })
            allocation.action_validate()
            leave1 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': '2020-09-06',
                'date_to': '2020-09-08',
                'number_of_days': 3,
            })

            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                ml=5, lt=0, rl=5, vrl=2, vlt=3, closest_allocation=allocation,
            )

            self.holidays_type_2.requires_allocation = 'no'
            leave2 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': '2020-07-06',
                'date_to': '2020-07-08',
                'number_of_days': 3,
            })

            # The 5 allocation days are not consumed anymore
            # virtual_remaining_leaves reflect the total number of leave days taken
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                ml=5, lt=0, rl=5, vrl=5, vlt=6, closest_allocation=allocation,
            )

            leave1.with_user(self.user_hrmanager_id).action_approve()
            leave2.with_user(self.user_hrmanager_id).action_approve()

            # leaves_taken and virtual_leaves_taken reflect the total number of leave days taken
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                ml=5, lt=6, rl=5, vrl=5, vlt=6, closest_allocation=allocation,
            )

    def test_archived_allocation(self):
        with freeze_time('2022-09-15'):
            allocation_2021 = self.env['hr.leave.allocation'].create({
                'name': 'Annual Time Off 2021',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 10,
                'state': 'confirm',
                'date_from': '2021-06-01',
                'date_to': '2021-12-31',
            })
            allocation_2022 = self.env['hr.leave.allocation'].create({
                'name': 'Annual Time Off 2022',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 20,
                'state': 'confirm',
                'date_from': '2022-01-01',
                'date_to': '2022-12-31',
            })
            allocation_2021.action_validate()
            allocation_2022.action_validate()

            # Leave taken in 2021
            leave_2021 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'holiday_type': 'employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': datetime(2021, 8, 9, 0, 0, 0),
                'date_to': datetime(2021, 8, 13, 23, 59, 59),
            })
            leave_2021.with_user(self.user_hrmanager_id).action_approve()

            # The holidays count only takes into account the valid allocations at that date
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id], date=date(2021, 12, 1))[self.employee_emp_id][self.holidays_type_2.id],
                ml=10, lt=5, rl=5, vrl=5, vlt=5, closest_allocation=allocation_2021,
            )

            # Virtual remaining leave is equal to 1 because there is only one day remaining in the allocation based on its validity
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id], date=date(2021, 12, 31))[self.employee_emp_id][self.holidays_type_2.id],
                ml=10, lt=5, rl=5, vrl=1, vlt=5, closest_allocation=allocation_2022,
            )

            leave_2022 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'holiday_type': 'employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.holidays_type_2.id,
                'date_from': datetime(2022, 8, 9, 0, 0, 0),
                'date_to': datetime(2022, 8, 13, 23, 59, 59),
            })
            leave_2022.with_user(self.user_hrmanager_id).action_approve()

            # The holidays count in 2022 is not affected by the first leave taken in 2021
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                ml=20, lt=4, rl=16, vrl=16, vlt=4, closest_allocation=allocation_2022,
            )

            # The holidays count in 2021 is not affected by the leave taken in 2022
            self._check_holidays_count(
                self.holidays_type_2.get_employees_days([self.employee_emp_id], date=date(2021, 12, 1))[self.employee_emp_id][self.holidays_type_2.id],
                ml=10, lt=5, rl=5, vrl=5, vlt=5, closest_allocation=allocation_2021,
            )

            with self.assertRaisesRegex(UserError,
                r'You cannot archive an allocation which is in confirm or validate state.'):

                # The logic of the test is relevant, so we do not remove it.
                # However, the behaviour will change.
                # Indeed, a confirmed or validated allocation cannot be archived

                allocation_2021.active = False

                # If the allocation is archived, the leaves taken are still counted on this allocation
                # but the max leaves and remaining leaves are not counted anymore
                # If there are no virtual_remaining_leaves, then there is no upcoming allocation (closest_allocation_to_expire) to expire
                self._check_holidays_count(
                    self.holidays_type_2.get_employees_days([self.employee_emp_id], date=date(2021, 12, 1))[self.employee_emp_id][self.holidays_type_2.id],
                    ml=0, lt=5, rl=0, vrl=0, vlt=5, closest_allocation=False,
                )

                # The holidays count in 2022 is not affected by the archived allocation in 2021
                self._check_holidays_count(
                    self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                    ml=20, lt=4, rl=16, vrl=16, vlt=4, closest_allocation=allocation_2022,
                )

                allocation_2021.active = True

                # The holidays count in 2021 is back to what it was when the allocation was active
                self._check_holidays_count(
                    self.holidays_type_2.get_employees_days([self.employee_emp_id], date=date(2021, 12, 1))[self.employee_emp_id][self.holidays_type_2.id],
                    ml=10, lt=5, rl=5, vrl=5, vlt=5, closest_allocation=allocation_2021,
                )

                # The holidays count in 2022 is still not affected by the allocation in 2021
                self._check_holidays_count(
                    self.holidays_type_2.get_employees_days([self.employee_emp_id])[self.employee_emp_id][self.holidays_type_2.id],
                    ml=20, lt=4, rl=16, vrl=16, vlt=4, closest_allocation=allocation_2022,
                )

    def test_cancel_leave(self):
        with freeze_time('2020-09-15'):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Annual Time Off',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_4.id,
                'number_of_days': 20,
                'state': 'confirm',
                'date_from': '2020-01-01',
                'date_to': '2020-12-31',
            })
            allocation.action_validate()

            leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_4.id,
                'date_from': '2020-09-21',
                'date_to': '2020-09-23',
                'number_of_days': 3,
            })

            # A meeting is only created once the leave is validated
            self.assertFalse(leave.meeting_id)
            leave.with_user(self.user_hrmanager_id).action_approve()
            self.assertFalse(leave.meeting_id)

            # A meeting is created in the user's calendar when a leave is validated
            leave.with_user(self.user_hrmanager_id).action_validate()
            self.assertTrue(leave.meeting_id.active)

            # The meeting is archived when the leave is cancelled
            leave.with_user(self.user_employee_id)._action_user_cancel('Cancel leave')
            self.assertFalse(leave.meeting_id.active)

    def test_create_support_document_in_the_past(self):
        with freeze_time('2022-10-19'):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_support_document.id,
                'date_from': '2022-10-17',
                'date_to': '2022-10-17',
                'number_of_days': 1,
                'supported_attachment_ids': [(6, 0, [])],  # Sent by webclient
            })

    def test_prevent_misplacement_of_allocations_without_end_date(self):
        """
            The objective is to check that it is not possible to place leaves
            for which the interval does not correspond to the interval of allocations.
        """
        holiday_type_A = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Type A',
            'requires_allocation': 'yes',
            'employee_requests': 'yes',
            'leave_validation_type': 'hr',
        })

        # Create allocations with no end date
        allocations = self.env['hr.leave.allocation'].create([
            {
                'name': 'Type A march 1 day without date to',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': holiday_type_A.id,
                'number_of_days': 1,
                'state': 'confirm',
                'date_from': '2023-01-03',
            },
            {
                'name': 'Type A april 5 day without date to',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': holiday_type_A.id,
                'number_of_days': 5,
                'state': 'confirm',
                'date_from': '2023-04-01',
            },
        ])

        allocations.action_validate()

        trigger_error_leave = {
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': holiday_type_A.id,
            'date_from': '2023-03-14',
            'date_to': '2023-03-16',
            'number_of_days': 3,
        }

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create(trigger_error_leave)
