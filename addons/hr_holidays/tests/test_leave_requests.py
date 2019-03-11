# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

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
        })
        self.holidays_type_2 = LeaveType.create({
            'name': 'Limited',
            'allocation_type': 'fixed',
            'validation_type': 'hr',
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
                'name': 'Sick Leave',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_3.id,
                'date_from': fields.Datetime.from_string('2017-07-03 06:00:00'),
                'date_to': fields.Datetime.from_string('2017-07-11 19:00:00'),
                'number_of_days': 1,
            })
