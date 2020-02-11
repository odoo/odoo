# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.tests.common import Form

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase

class TestLeaveRequests(TestHrHolidaysBase):

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
        LeaveType = self.env['hr.leave.type'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.holidays_type_1 = LeaveType.create({
            'name': 'NotLimitedHR',
            'allocation_type': 'no',
            'validation_type': 'hr',
            'validity_start': False,
        })
        self.holidays_type_2 = LeaveType.create({
            'name': 'Limited',
            'allocation_type': 'fixed',
            'validation_type': 'hr',
            'validity_start': False,
        })
        self.holidays_type_3 = LeaveType.create({
            'name': 'TimeNotLimited',
            'allocation_type': 'no',
            'validation_type': 'manager',
            'validity_start': fields.Datetime.from_string('2017-01-01 00:00:00'),
            'validity_stop': fields.Datetime.from_string('2017-06-01 00:00:00'),
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
        self.env['hr.leave'].sudo(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].sudo(self.user_employee_id).create({
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
            self.env['hr.leave'].sudo(self.user_employee_id).create({
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
        aloc1_user_group = self.env['hr.leave.allocation'].sudo(self.user_hruser_id).create({
            'name': 'Days for limited category',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 2,
        })
        aloc1_user_group.action_approve()

        holiday_status = self.holidays_type_2.sudo(self.user_employee_id)
        self._check_holidays_status(holiday_status, 2.0, 0.0, 2.0, 2.0)

        hol = self.env['hr.leave'].sudo(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': (datetime.today() - relativedelta(days=2)),
            'date_to': datetime.today(),
            'number_of_days': 2,
        })

        holiday_status.invalidate_cache()
        self._check_holidays_status(holiday_status, 2.0, 0.0, 2.0, 0.0)

        hol.sudo(self.user_hrmanager_id).action_approve()

        self._check_holidays_status(holiday_status, 2.0, 2.0, 0.0, 0.0)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_accrual_validity_time_valid(self):
        """  Employee ask leave during a valid validity time """
        self.env['hr.leave'].sudo(self.user_employee_id).create({
            'name': 'Valid time period',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_3.id,
            'date_from': fields.Datetime.from_string('2017-03-03 06:00:00'),
            'date_to': fields.Datetime.from_string('2017-03-11 19:00:00'),
            'number_of_days': 1,
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_accrual_validity_time_not_valid(self):
        """  Employee ask leav during a not valid validity time """
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].sudo(self.user_employee_id).create({
                'name': 'Sick Time Off',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_3.id,
                'date_from': fields.Datetime.from_string('2017-07-03 06:00:00'),
                'date_to': fields.Datetime.from_string('2017-07-11 19:00:00'),
                'number_of_days': 1,
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_department_leave(self):
        """ Create a department leave """
        self.employee_hrmanager.write({'department_id': self.hr_dept.id})
        self.assertFalse(self.env['hr.leave'].search([('employee_id', 'in', self.hr_dept.member_ids.ids)]))
        leave_form = Form(self.env['hr.leave'].sudo(self.user_hrmanager))
        leave_form.holiday_type = 'department'
        leave_form.department_id = self.hr_dept
        leave_form.holiday_status_id = self.holidays_type_1
        leave = leave_form.save()
        leave.action_approve()
        member_ids = self.hr_dept.member_ids.ids
        self.assertEqual(self.env['hr.leave'].search_count([('employee_id', 'in', member_ids)]), len(member_ids), "Leave should be created for members of department")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_allocation_request(self):
        """ Create an allocation request """
        # employee should be set to current user
        allocation_form = Form(self.env['hr.leave.allocation'].sudo(self.user_employee))
        allocation_form.holiday_status_id = self.holidays_type_1
        allocation = allocation_form.save()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_employee_is_absent(self):
        """ Only the concerned employee should be considered absent """
        self.env['hr.leave'].sudo(self.user_employee_id).create({
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
        values.update(self.env['hr.leave'].sudo(self.user_employee_id)._default_get_request_parameters(values))

        # Dates should be local to the user
        self.assertEqual(values['request_date_from'], local_date_from.date())
        self.assertEqual(values['request_date_to'], local_date_to.date())

        values.update({
            'name': 'Test',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
        })
        leave = self.env['hr.leave'].sudo(self.user_employee_id).new(values)
        leave._onchange_request_parameters()
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
        local_date_from = datetime(2019, 1, 1, 7, 0, 0)
        local_date_to = datetime(2019, 1, 1, 19, 0, 0)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 1)

        # We, Th, Fr, Mo, Tu, We => 6 days
        local_date_from = datetime(2019, 1, 1, 7, 0, 0)
        local_date_to = datetime(2019, 1, 8, 19, 0, 0)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 6)
