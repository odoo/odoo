# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date, timedelta
import time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from pytz import timezone

from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils, mute_logger
from odoo.tests import Form, tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon

@tagged('leave_requests')
class TestLeaveRequests(TestHrHolidaysCommon):

    def _check_holidays_status(self, holiday_status, employee, ml, lt, rl, vrl):
        result = holiday_status.get_allocation_data(employee)[employee][0][1]
        self.assertEqual(
            result['max_leaves'], ml,
            'hr_holidays: wrong type days computation')
        self.assertEqual(
            result['leaves_taken'], lt,
            'hr_holidays: wrong type days computation')
        self.assertEqual(
            result['remaining_leaves'], rl,
            'hr_holidays: wrong type days computation')
        self.assertEqual(
            result['virtual_remaining_leaves'], vrl,
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

    def _check_holidays_count(self, holidays_count_result, ml, lt, rl, vrl, vlt):
        self.assertEqual(holidays_count_result['max_leaves'], ml)
        self.assertEqual(holidays_count_result['remaining_leaves'], rl)
        self.assertEqual(holidays_count_result['virtual_remaining_leaves'], vrl)
        self.assertEqual(holidays_count_result['leaves_taken'], lt)
        self.assertEqual(holidays_count_result['virtual_leaves_taken'], vlt)

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
            'request_date_from': (date.today() - relativedelta(days=1)),
            'request_date_to': date.today(),
        })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Hol21',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_1.id,
                'request_date_from': (datetime.today() - relativedelta(days=1)),
                'request_date_to': datetime.today(),
            })

    def test_limited_type_not_enough_days(self):
        with freeze_time('2022-01-05'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hruser_id).create({
                'name': 'Days for limited category',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 2,
                'state': 'confirm',
                'date_from': time.strftime('%Y-1-1'),
                'date_to': time.strftime('%Y-12-31'),
            })

            allocation.action_validate()

            # Employee cannot take a leave longer than the allocation
            with self.assertRaises(ValidationError):
                self.env['hr.leave'].with_user(self.user_employee_id).create({
                    'name': 'Invalid Hol21',
                    'employee_id': self.employee_emp_id,
                    'holiday_status_id': self.holidays_type_2.id,
                    'request_date_from': time.strftime('2022-02-01'),
                    'request_date_to': time.strftime('2022-02-04'),
                })

            # A leave cannot be modified so that it's longer than the allocation
            valid_leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Valid Hol21',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': time.strftime('2022-02-02'),
                'request_date_to': time.strftime('2022-02-03'),
            })
            with self.assertRaises(ValidationError):
                valid_leave.write({
                    'request_date_from': time.strftime('2022-02-01'),
                    'request_date_to': time.strftime('2022-02-05'),
                })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_limited_type_days_left(self):
        """  Employee creates a leave request in a limited category and has enough days left  """
        with freeze_time('2022-01-05'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hruser_id).create({
                'name': 'Days for limited category',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 2,
                'state': 'confirm',
                'date_from': time.strftime('%Y-1-1'),
                'date_to': time.strftime('%Y-12-31'),
            })
            allocation.action_validate()

            holiday_status = self.holidays_type_2.with_user(self.user_employee_id)
            self._check_holidays_status(holiday_status, self.employee_emp, 2.0, 0.0, 2.0, 2.0)

            hol = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Hol11',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': (datetime.today() - relativedelta(days=1)),
                'request_date_to': datetime.today(),
            })

            holiday_status.invalidate_model()
            self._check_holidays_status(holiday_status, self.employee_emp, 2.0, 0.0, 2.0, 0.0)

            hol.with_user(self.user_hrmanager_id).action_approve()

            holiday_status.invalidate_model(['max_leaves'])
            self._check_holidays_status(holiday_status, self.employee_emp, 2.0, 2.0, 0.0, 0.0)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_accrual_validity_time_valid(self):
        """  Employee ask leave during a valid validity time """

        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Sick Time Off',
            'holiday_status_id': self.holidays_type_2.id,
            'employee_id': self.employee_emp.id,
            'date_from': fields.Datetime.from_string('2017-01-01 00:00:00'),
            'date_to': fields.Datetime.from_string('2017-06-01 00:00:00'),
            'number_of_days': 10,
        })
        allocation.action_validate()

        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Valid time period',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'request_date_from': fields.Date.from_string('2017-03-03'),
            'request_date_to': fields.Date.from_string('2017-03-11'),
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_department_leave(self):
        """ Create a department leave """
        self.employee_hrmanager.write({'department_id': self.hr_dept.id})
        self.assertFalse(self.env['hr.leave'].search([('employee_id', 'in', self.hr_dept.member_ids.ids)]))
        leave_wizard_form = Form(self.env['hr.leave.generate.multi.wizard'].with_user(self.user_hrmanager))
        leave_wizard_form.allocation_mode = 'department'
        leave_wizard_form.department_id = self.hr_dept
        leave_wizard_form.holiday_status_id = self.holidays_type_1
        leave_wizard_form.date_from = date(2019, 5, 6)
        leave_wizard_form.date_to = date(2019, 5, 6)
        leave_wizard = leave_wizard_form.save()
        leave_wizard.action_generate_time_off()
        member_ids = self.hr_dept.member_ids.ids
        self.assertEqual(self.env['hr.leave'].search_count([('employee_id', 'in', member_ids)]), len(member_ids), "Time Off should be created for members of department")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_allocation_request(self):
        """ Create an allocation request """
        # employee should be set to current user
        allocation_form = Form(self.env['hr.leave.allocation'].with_user(self.user_employee))
        allocation_form.holiday_status_id = self.holidays_type_2
        allocation_form.date_from = date(2019, 5, 6)
        allocation_form.date_to = date(2019, 5, 6)
        allocation_form.name = 'New Allocation Request'
        allocation_form.save()

    def test_allocation_constrain_dates_check(self):
        with self.assertRaises(UserError):
            self.env['hr.leave.allocation'].create({
                'name': 'Test allocation',
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 1,
                'employee_id': self.employee_emp_id,
                'state': 'confirm',
                'date_from': time.strftime('%Y-%m-10'),
                'date_to': time.strftime('%Y-%m-01'),
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_employee_is_absent(self):
        """ Only the concerned employee should be considered absent """
        user_employee_leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': (date.today() - relativedelta(days=1)),
            'request_date_to': date.today() + relativedelta(days=1),
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
        self.employee_emp.tz = 'Pacific/Auckland'  # GMT+12
        leave = self.env['hr.leave'].new({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_unit_hours': True,
            'request_date_from': date(2019, 5, 6),
            'request_date_to': date(2019, 5, 6),
            'request_hour_from': 8,  # 8:00 AM in the employee's timezone
            'request_hour_to': 17,  # 5:00 PM in the employee's timezone
        })
        self.assertEqual(leave.date_from, datetime(2019, 5, 5, 20, 0, 0), "It should have been localized before saving in UTC")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 5, 0, 0), "It should have been localized before saving in UTC")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_company_leave_request(self):
        """ Create a leave request for a company in another timezone """
        company = self.env['res.company'].create({'name': "Hergé"})
        company.resource_calendar_id.tz = 'Australia/Sydney'  # GMT+12
        leave = self.env['hr.leave'].new({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_unit_hours': True,
            'company_id': company.id,
            'request_date_from': date(2019, 5, 6),
            'request_date_to': date(2019, 5, 6),
            'request_hour_from': 8,  # 8:00 AM in the company's timezone
            'request_hour_to': 17,  # 5:00 PM in the company's timezone
        })
        self.assertEqual(leave.date_from, datetime(2019, 5, 6, 6, 0, 0), "It should have been localized in the Employee timezone")
        self.assertEqual(leave.date_to, datetime(2019, 5, 6, 15, 0, 0), "It should have been localized in the Employee timezone")

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_timezone_company_validated(self):
        """ Create a leave request for a company in another timezone and validate it """
        self.env.user.tz = 'Australia/Sydney' # GMT+12
        company = self.env['res.company'].create({'name': "Hergé"})
        employee = self.env['hr.employee'].create({'name': "Remi", 'company_id': company.id})
        leave_wizard_form = Form(self.env['hr.leave.generate.multi.wizard'])
        leave_wizard_form.allocation_mode = 'company'
        leave_wizard_form.company_id = company
        leave_wizard_form.holiday_status_id = self.holidays_type_1
        leave_wizard_form.date_from = date(2019, 5, 6)
        leave_wizard_form.date_to = date(2019, 5, 6)
        leave_wizard = leave_wizard_form.save()
        leave_wizard.action_generate_time_off()
        employee_leave = self.env['hr.leave'].search([('employee_id', '=', employee.id)])
        self.assertEqual(
            employee_leave.request_date_from, date(2019, 5, 6),
            "Timezone should be be adapted on the employee leave"
        )

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
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12.5, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12.5, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12.5, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8.5, 'hour_to': 12.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12.5, 'hour_to': 13, 'day_period': 'lunch'}),
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
        self.env['hr.leave.allocation'].create({
            'name': '20 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 20,
            'employee_id': employee.id,
            'state': 'confirm',
            'date_from': time.strftime('2018-1-1'),
            'date_to': time.strftime('%Y-1-1'),
        })

        leave1 = self.env['hr.leave'].create({
            'name': 'Holiday 1 week',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Date.from_string('2019-12-23'),
            'request_date_to': fields.Date.from_string('2019-12-27'),
        })

        self.assertEqual(leave1.number_of_hours, 38)
        leave1.action_approve()
        self.assertEqual(leave1.number_of_hours, 38)
        leave1.action_validate()
        self.assertEqual(leave1.number_of_hours, 38)

        leave2 = self.env['hr.leave'].create({
            'name': 'Holiday 1 Day',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Datetime.from_string('2019-12-30'),
            'request_date_to': fields.Datetime.from_string('2019-12-30'),
        })

        self.assertEqual(leave2.number_of_hours, 4)
        leave2.action_approve()
        self.assertEqual(leave2.number_of_hours, 4)
        leave2.action_validate()
        self.assertEqual(leave2.number_of_hours, 4)

    def test_number_of_hours_display_flexible_calendar(self):
        # Test that the field number_of_hours_dispay do change for flexible calendars
        calendar = self.env['resource.calendar'].create({
            'name': 'Full Time 24h/8day',
            'hours_per_day': 24,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 0, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 24, 'day_period': 'afternoon'})
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
        self.env['hr.leave.allocation'].create({
            'name': '20 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 20,
            'employee_id': employee.id,
            'state': 'confirm',
            'date_from': time.strftime('2018-1-1'),
            'date_to': time.strftime('%Y-1-1'),
        })

        leave0 = self.env['hr.leave'].create({
            'name': 'Holiday 1 day',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Date.from_string('2019-12-9'),
            'request_date_to': fields.Date.from_string('2019-12-9'),
        })

        self.assertAlmostEqual(leave0.number_of_hours, 24, 2)

        calendar.write({
            'flexible_hours': True,
            'hours_per_day': 8.0
        })

        leave1 = self.env['hr.leave'].create({
            'name': 'Holiday 1 week',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Date.from_string('2019-12-16'),
            'request_date_to': fields.Date.from_string('2019-12-20'),
        })

        self.assertEqual(leave1.number_of_hours, 5 * 8)

        leave2 = self.env['hr.leave'].create({
            'name': 'Holiday 1 Day',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Datetime.from_string('2019-12-23'),
            'request_date_to': fields.Datetime.from_string('2019-12-23'),
        })

        self.assertEqual(leave2.number_of_hours, 8)

        leave3 = self.env['hr.leave'].create({
            'name': 'Holiday 1/2 Day',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Datetime.from_string('2019-12-24'),
            'request_unit_half': True,
        })

        self.assertEqual(leave3.number_of_hours, 4)

        leave4 = self.env['hr.leave'].create({
            'name': 'Holiday 3 Hours',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Datetime.from_string('2019-12-25'),
            'request_unit_hours': True,
            'request_hour_from': 7,
            'request_hour_to': 10,
        })

        self.assertEqual(leave4.number_of_hours, 3)

        leave5 = self.env['hr.leave'].create({
            'name': 'Holiday 10 hours',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': fields.Datetime.from_string('2019-12-26'),
            'request_unit_hours': True,
            'request_hour_from': 7,
            'request_hour_to': 17,
        })

        self.assertEqual(leave5.number_of_hours, 8)

    def test_number_of_hours_display_global_leave(self):
        # Check that the field number_of_hours
        # takes the global leaves into account, even
        # after validation
        calendar = self.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ],
            'global_leave_ids': [(0, 0, {
                'name': 'Christmas Time Off',
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
            'request_date_from': fields.Date.from_string('2019-12-23'),
            'request_date_to': fields.Date.from_string('2019-12-27'),
        })
        self.assertEqual(leave1.number_of_hours, 24)
        leave1.action_approve()
        self.assertEqual(leave1.number_of_hours, 24)
        leave1.action_validate()
        self.assertEqual(leave1.number_of_hours, 24)

    def _test_leave_with_tz(self, tz, local_date_from, local_date_to, number_of_days):
        self.user_employee.tz = tz
        tz = timezone(tz)

        # We use new instead of create to avoid the leaves generated for the
        # different timezones clashing with each other.
        leave = self.env['hr.leave'].with_user(self.user_employee_id).new({
            'name': 'Test',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': local_date_from,
            'request_date_to': local_date_to,
        })
        self.assertEqual(leave.number_of_days, number_of_days)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_defaults_with_timezones(self):
        """ Make sure that leaves start with correct defaults for non-UTC timezones """
        timezones_to_test = ('UTC', 'Pacific/Midway', 'America/Los_Angeles', 'Asia/Taipei', 'Pacific/Kiritimati')  # UTC, UTC -11, UTC -8, UTC +8, UTC +14

        #     January 2020
        # Su Mo Tu We Th Fr Sa
        #           1  2  3  4
        #  5  6  7  8  9 10 11
        # 12 13 14 15 16 17 18
        # 19 20 21 22 23 24 25
        # 26 27 28 29 30 31
        local_date_from = date(2020, 1, 1)
        local_date_to = date(2020, 1, 1)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 1)

        # We, Th, Fr, Mo, Tu, We => 6 days
        local_date_from = date(2020, 1, 2)
        local_date_to = date(2020, 1, 9)
        for tz in timezones_to_test:
            self._test_leave_with_tz(tz, local_date_from, local_date_to, 6)

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
                'request_date_from': '2021-09-01',
                'request_date_to': '2021-09-01',
            })
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'request_date_from': '2020-09-01',
            'request_date_to': '2020-09-01',
        })

    def test_no_days_expired(self):
        # First expired allocation
        allocation_one = self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })
        allocation_one.action_validate()
        allocation_two = self.env['hr.leave.allocation'].create({
            'name': 'Expired Allocation',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'number_of_days': 3,
            'state': 'confirm',
            'date_from': '2021-01-01',
            'date_to': '2021-12-31',
        })
        allocation_two.action_validate()
        # Try creating a request that could be validated if allocation1 was still valid
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': '2021-09-06',
                'request_date_to': '2021-09-10',
            })
        # This time we have enough days
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-08',
        })

    def test_company_leaves(self):
        # First expired allocation
        self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Allocation',
            'company_id': self.env.company.id,
            'holiday_status_id': self.holidays_type_1.id,
            'duration': 20,
            'date_from': '2021-01-01',
        })

        req1_form = Form(self.env['hr.leave'].sudo())
        req1_form.employee_id = self.employee_emp
        req1_form.holiday_status_id = self.holidays_type_1
        req1_form.request_date_from = fields.Date.to_date('2021-12-06')
        req1_form.request_date_to = fields.Date.to_date('2021-12-08')

        self.assertEqual(req1_form.number_of_days, 3)
        req1_form.save().action_approve()

    def test_leave_with_public_holiday_other_company(self):
        other_company = self.env['res.company'].create({
            'name': 'Test Company 2',
        })
        # Create a public holiday for the second company
        p_leave = self.env['resource.calendar.leaves'].create({
            'date_from': datetime(2022, 3, 11),
            'date_to': datetime(2022, 3, 11, 23, 59, 59),
        })
        p_leave.company_id = other_company

        leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': date(2022, 3, 11),
            'request_date_to': date(2022, 3, 11),
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
        self.env['hr.leave.allocation'].create(allocation_vals)
        self.env['hr.leave.allocation'].create(allocation_vals)

        # Able to create a leave of 10 days with two allocations of 5 days
        self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'request_date_from': '2022-01-01',
            'request_date_to': '2022-01-15',
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
            allocation_4days.action_validate()
            allocation_vals.update({'number_of_days': 1})
            allocation_1day = Allocation.create(allocation_vals)
            allocation_1day.action_validate()
            allocations = (allocation_4days + allocation_1day)

            leave_vals.update({
                'request_date_from': '2022-01-03',
                'request_date_to': '2022-01-06',
            })
            leave_confirm = Leave.create(leave_vals)
            leave_confirm.action_refuse()
            leave_vals.update({
                'request_date_from': '2022-01-03',
                'request_date_to': '2022-01-06',
            })
            leave_4days = Leave.create(leave_vals)
            leave_vals.update({
                'request_date_from': '2022-01-07',
                'request_date_to': '2022-01-07',
            })
            leave_1day = Leave.create(leave_vals)
            leaves = (leave_4days + leave_1day)
            leaves.action_approve()

            allocation_days = self.employee_emp._get_consumed_leaves(self.holidays_type_2)[0]

            self.assertEqual(
                allocation_days[self.employee_emp][self.holidays_type_2][allocation_4days]['leaves_taken'],
                leave_4days['number_of_%ss' % unit],
                'As 4 days were available in this allocation, they should have been taken')
            self.assertEqual(
                allocation_days[self.employee_emp][self.holidays_type_2][allocation_1day]['leaves_taken'],
                leave_1day['number_of_%ss' % unit],
                'As no days were available in previous allocation, they should have been taken in this one')
            leaves.action_refuse()
            allocations.action_refuse()

    def test_time_off_recovery_on_create(self):
        time_off = self.env['hr.leave'].create([
            {
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_1.id,
                'request_date_from': '2021-12-06',
                'request_date_to': '2021-12-10',
            },
            {
                'name': 'Holiday Request',
                'employee_id': self.employee_hruser_id,
                'holiday_status_id': self.holidays_type_1.id,
                'request_date_from': '2021-12-06',
                'request_date_to': '2021-12-10',
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
            'request_date_from': '2021-12-06',
            'request_date_to': '2021-12-10',
        })
        self.assertEqual(time_off_1.number_of_days, 4)

        time_off_2 = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': '2021-12-13',
            'request_date_to': '2021-12-17',
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
        self.assertEqual(time_off_1.number_of_days, 5)
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
            'request_date_from': '2021-12-06',
            'request_date_to': '2021-12-10',
        })
        self.assertEqual(time_off.number_of_days, 4)
        global_time_off.unlink()
        self.assertEqual(time_off.number_of_days, 5)

    def test_time_off_duration_zero(self):
        time_off = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': '2021-11-15',
            'request_date_to': '2021-11-19',
        })
        self.assertEqual(time_off.number_of_days, 5)
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': '2021-11-15 00:00:00',
            'date_to': '2021-11-19 23:59:59',
        })
        self.assertEqual(time_off.state, 'confirm')
        self.assertEqual(time_off.number_of_days, 0)

    def test_time_off_irregular_working_schedule(self):
        # Test a specific case where `_get_attendances` bugged out when a
        # very specific working schedule was used.
        calendar = self.env['resource.calendar'].create({
            'name': 'Irregular Working Schedule (monday morning - wednesday afternoon)',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.employee_emp.resource_calendar_id = calendar
        # Take a time off on the next tuesday (when the employee is not
        # supposed to work) Previously this would raise a ValidationError.
        next_tuesday = date_utils.start_of(fields.Date.today() + relativedelta(days=7), 'week') + relativedelta(days=1)
        time_off = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'request_date_from': next_tuesday,
            'request_date_to': next_tuesday,
        })
        self.assertEqual(time_off.number_of_days, 0)

    def test_holiday_type_allocation(self):
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
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': '2020-09-07',
                'request_date_to': '2020-09-09',
            })

            self._check_holidays_count(
                self.employee_emp._get_consumed_leaves(self.holidays_type_2)[0][self.employee_emp][self.holidays_type_2][allocation],
                ml=5, lt=0, rl=5, vrl=2, vlt=3,
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
            allocation_2021.action_validate()

            allocation_2022 = self.env['hr.leave.allocation'].create({
                'name': 'Annual Time Off 2022',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_2.id,
                'number_of_days': 20,
                'state': 'confirm',
                'date_from': '2022-01-01',
                'date_to': '2022-12-31',
            })
            allocation_2022.action_validate()

            # Leave taken in 2021
            leave_2021 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': datetime(2021, 8, 9),
                'request_date_to': datetime(2021, 8, 13),
            })
            leave_2021.with_user(self.user_hrmanager_id).action_approve()

            # The holidays count only takes into account the valid allocations at that date
            self._check_holidays_count(
                self.holidays_type_2.get_allocation_data(self.employee_emp, target_date=date(2021, 12, 1))[self.employee_emp][0][1],
                ml=10, lt=5, rl=5, vrl=5, vlt=5,
            )

            # Days remaining before the allocation ends is equal to 1 because there is only one day remaining in the allocation based on its validity
            self.assertEqual(
                self.holidays_type_2.get_allocation_data(self.employee_emp, target_date=date(2021, 12, 31))[self.employee_emp][0][1]['closest_allocation_duration'],
                1,
                "Only one day should remain before the allocation expires"
            )

            leave_2022 = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.holidays_type_2.id,
                'request_date_from': datetime(2022, 8, 9),
                'request_date_to': datetime(2022, 8, 13),
            })
            leave_2022.with_user(self.user_hrmanager_id).action_approve()

            # The holidays count in 2022 is not affected by the first leave taken in 2021
            self._check_holidays_count(
                self.holidays_type_2.get_allocation_data(self.employee_emp)[self.employee_emp][0][1],
                ml=20, lt=4, rl=16, vrl=16, vlt=4,
            )

            # The holidays count in 2021 is not affected by the leave taken in 2022
            self._check_holidays_count(
                self.holidays_type_2.get_allocation_data(self.employee_emp, target_date=date(2021, 12, 1))[self.employee_emp][0][1],
                ml=10, lt=5, rl=5, vrl=5, vlt=5,
            )

    def test_cancel_leave(self):
        with freeze_time('2020-09-15'):
            self.env['hr.leave.allocation'].create({
                'name': 'Annual Time Off',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_4.id,
                'number_of_days': 20,
                'state': 'confirm',
                'date_from': '2020-01-01',
                'date_to': '2020-12-31',
            })

            leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_type_4.id,
                'request_date_from': '2020-09-21',
                'request_date_to': '2020-09-23',
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
                'request_date_from': '2022-10-17',
                'request_date_to': '2022-10-17',
                'supported_attachment_ids': [(6, 0, [])],  # Sent by webclient
            })

    def test_prevent_misplacement_of_allocations_without_end_date(self):
        """
            The objective is to check that it is not possible to place leaves
            for which the interval does not correspond to the interval of allocations.
        """
        leave_type_A = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
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
                'holiday_status_id': leave_type_A.id,
                'number_of_days': 1,
                'state': 'confirm',
                'date_from': '2023-01-03',
            },
            {
                'name': 'Type A april 5 day without date to',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': leave_type_A.id,
                'number_of_days': 5,
                'state': 'confirm',
                'date_from': '2023-04-01',
            },
        ])

        allocations.action_validate()

        trigger_error_leave = {
            'name': 'Holiday Request',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type_A.id,
            'request_date_from': '2023-03-14',
            'request_date_to': '2023-03-16',
        }

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.user_employee_id).create(trigger_error_leave)

    @freeze_time('2022-06-13 10:00:00')
    def test_current_leave_status(self):
        types = ('no_validation', 'manager', 'hr', 'both')
        employee = self.employee_emp

        def run_validation_flow(leave_validation_type):
            LeaveType = self.env['hr.leave.type'].with_user(self.user_hrmanager_id)
            leave_type = LeaveType.with_context(tracking_disable=True).create({
                'name': leave_validation_type.capitalize(),
                'leave_validation_type': leave_validation_type,
                'requires_allocation': 'no',
                'responsible_ids': [Command.link(self.env.ref('base.user_admin').id)],
            })
            current_leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Holiday Request',
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'date_from': datetime.today() - timedelta(days=1),
                'date_to': datetime.today() + timedelta(days=1),
            })

            if leave_validation_type in ('manager', 'both'):
                self.assertFalse(employee.is_absent)
                self.assertFalse(employee.current_leave_id)
                self.assertEqual(employee.filtered_domain([('is_absent', '=', False)]), employee)
                self.assertFalse(employee.filtered_domain([('is_absent', '=', True)]))
                current_leave.with_user(self.user_hruser_id).action_approve()

            if leave_validation_type in ('hr', 'both'):
                self.assertFalse(employee.is_absent)
                self.assertFalse(employee.current_leave_id)
                self.assertEqual(employee.filtered_domain([('is_absent', '=', False)]), employee)
                self.assertFalse(employee.filtered_domain([('is_absent', '=', True)]))
                current_leave.with_user(self.user_hrmanager_id).action_validate()

            self.assertTrue(employee.is_absent)
            self.assertEqual(employee.current_leave_id, current_leave.holiday_status_id)
            self.assertFalse(employee.filtered_domain([('is_absent', '=', False)]))
            self.assertEqual(employee.filtered_domain([('is_absent', '=', True)]), employee)

            raise RuntimeError()

        for leave_validation_type in types:
            with self.assertRaises(RuntimeError), self.env.cr.savepoint():
                run_validation_flow(leave_validation_type)

    @freeze_time('2019-11-01')
    def test_duration_display_global_leave(self):
        """ Ensure duration_display stays in sync with leave duration. """
        employee = self.employee_emp
        calendar = employee.resource_calendar_id
        sick_leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick Leave (days)',
            'request_unit': 'day',
            'leave_validation_type': 'hr',
        })
        sick_leave = self.env['hr.leave'].create({
            'name': 'Sick 3 days',
            'employee_id': employee.id,
            'holiday_status_id': sick_leave_type.id,
            'request_date_from': '2019-12-23',
            'request_date_to': '2019-12-25',
        })
        comp_leave_type = self.env['hr.leave.type'].create({
            'name': 'OT Compensation (hours)',
            'request_unit': 'hour',
            'leave_validation_type': 'manager',
        })
        comp_leave = self.env['hr.leave'].create({
            'name': 'OT Comp (4 hours)',
            'employee_id': employee.id,
            'holiday_status_id': comp_leave_type.id,
            'request_unit_hours': True,
            'request_date_from': '2019-12-26',
            'request_date_to': '2019-12-26',
            'request_hour_from': 8,
            'request_hour_to': 12,
        })

        self.assertEqual(sick_leave.duration_display, '3 days')
        self.assertEqual(comp_leave.duration_display, '4:00 hours')

        calendar.global_leave_ids = [(0, 0, {
            'name': 'Winter Holidays',
            'date_from': '2019-12-25 00:00:00',
            'date_to': '2019-12-26 23:59:59',
            'time_type': 'leave',
        })]

        msg = "hr_holidays: duration_display should update after adding an overlapping holiday"
        self.assertEqual(sick_leave.duration_display, '2 days', msg)
        self.assertEqual(comp_leave.duration_display, '0:00 hours', msg)

    def test_duration_display_public_leave_include(self):
        """
            The purpose is to test whether the duration_display
            computation considers public holidays when the
            `include_public_holidays_in_duration` is set to True.
        """
        employee = self.employee_emp
        calendar = employee.resource_calendar_id
        sick_leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick Leave (days)',
            'request_unit': 'day',
            'leave_validation_type': 'hr',
        })
        sick_leave = self.env['hr.leave'].create({
            'name': 'Sick 3 days',
            'employee_id': employee.id,
            'holiday_status_id': sick_leave_type.id,
            'request_date_from': '2021-11-15',
            'request_date_to': '2021-11-17',
        })

        self.assertEqual(sick_leave.duration_display, '3 days')

        calendar.global_leave_ids = [(0, 0, {
            'name': 'Autumn Holidays',
            'date_from': '2021-11-16 00:00:00',
            'date_to': '2021-11-16 23:59:59',
            'time_type': 'leave',
        })]

        self.assertEqual(sick_leave.duration_display, '2 days', "hr_holidays: duration_display should not count public holiday")

        sick_leave_type.include_public_holidays_in_duration = True
        sick_leave.unlink()
        sick_leave = self.env['hr.leave'].create({
            'name': 'Sick 3 days',
            'employee_id': employee.id,
            'holiday_status_id': sick_leave_type.id,
            'request_date_from': '2021-11-15',
            'request_date_to': '2021-11-17',
        })

        self.assertEqual(sick_leave.duration_display, '3 days', "hr_holidays: duration_display should not update after adding an overlapping holiday")

    @freeze_time('2024-01-18')
    def test_undefined_working_hours(self):
        """ Ensure time-off can also be allocated without ResourceCalendar. """
        employee = self.employee_emp

        # set a flexible working schedule
        calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })
        employee.resource_calendar_id = calendar
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Annual Time Off',
            'employee_id': employee.id,
            'holiday_status_id': self.holidays_type_4.id,
            'number_of_days': 20,
            'state': 'confirm',
            'date_from': '2024-01-01',
            'date_to': '2024-12-31',
        })
        allocation.action_validate()
        leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
            'name': 'Holiday Request',
            'employee_id': employee.id,
            'holiday_status_id': self.holidays_type_4.id,
            'request_date_from': '2024-01-23',
            'request_date_to': '2024-01-27',
        })
        holiday_status = self.holidays_type_4.with_user(self.user_employee_id)
        self._check_holidays_status(holiday_status, employee, 20.0, 0.0, 20.0, 15.0)
        self.assertEqual(leave.duration_display, '5 days')

    def test_default_request_date_timezone(self):
        """
            The purpose is to test whether the timezone is
            taken into account when requesting a leave.
        """
        self.user_employee.tz = 'Asia/Hong_Kong'  # UTC +08:00
        context = {
            # `date_from/to` in UTC to simulate client values
            'default_date_from': '2024-03-27 23:00:00',
            'default_date_to': '2024-03-28 08:00:00',
        }
        leave_form = Form(self.env['hr.leave'].with_user(self.user_employee).with_context(context))
        leave_form.holiday_status_id = self.holidays_type_2
        leave = leave_form.save()
        self.assertEqual(leave.number_of_days, 1.0)

    def test_filter_time_off_type_multiple_employees(self):
        """ This test mimics the behavior of creating time off for multiple employees.
        We check that the time off types that the user can select are correct.
        In this example, we use a time off type that requires allocations.
        Only the current user has an allocation for the time off type.
        This time off type should not appear when multiple employees are select (user included or not).
        """
        self.assertFalse(self.env['hr.leave.allocation'].search([['holiday_status_id', '=', self.holidays_type_2.id]]))

        self.env.user.employee_id = self.employee_hruser_id
        allocation = self.env['hr.leave.allocation'].create({
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.holidays_type_2.id,
            'allocation_type': 'regular'
        })
        allocation.action_validate()

        self.assertEqual(allocation.state, 'validate')

        search_domain = ['|',
                        ['requires_allocation', '=', 'no'],
                        '&',
                            ['has_valid_allocation', '=', True],
                            '&',
                                ['max_leaves', '>', '0'],
                                '|',
                                ['allows_negative', '=', True],
                                '&',
                                    ['virtual_remaining_leaves', '>', 0],
                                    ['allows_negative', '=', False]]

        search_result = self.env['hr.leave.type'].with_context(employee_id=False).name_search(args=search_domain)
        self.assertFalse(self.holidays_type_2.id in [alloc_id for (alloc_id, _) in search_result])

    def test_holiday_type_allocation_requirement_edit(self):
        # Does not raise an error since no leave of this type exists yet
        self.holidays_type_2.requires_allocation = 'no'
        self.assertEqual(self.holidays_type_2.requires_allocation, 'no', 'Allocations should no longer be required')

        self.env['hr.leave'].create({
            'name': 'Test leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })

        with self.assertRaises(UserError):
            self.holidays_type_2.requires_allocation = 'yes'

    def test_activity_update_with_time_off_officer(self):
        """ Test activity creation flow when approval settings involve Time Off Officer and Employee's Approver. """
        # Case 1: Approved by Time Off Officer but no Time Off Officer is set
        self.holidays_type_1.responsible_ids = False    # No Time Off Officer set

        test_holiday_1 = self.env['hr.leave'].create({
            'name': 'Test leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_type_1.id,
            'date_from': (datetime.today() - timedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })

        activities = test_holiday_1.activity_ids
        self.assertFalse(activities, "No activity should be created if no Time Off Officer is set for approval.")

        self.holidays_type_2.responsible_ids = [Command.link(self.user_employee.id)]
        test_holiday_2 = self.env['hr.leave'].create({
            'name': 'Test leave',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': (datetime.today() - timedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days': 1,
        })

        activities = test_holiday_2.activity_ids
        self.assertEqual(len(activities), 1, "One activity should be created for the Employee's Approver.")
        self.assertEqual(activities.activity_type_id, self.env.ref('hr_holidays.mail_act_leave_approval'), "The activity type should be for leave approval by the Employee's Approver.")
        self.assertEqual(activities.user_id.id, self.user_employee_id, "The activity should be assigned to the Employee's Approver.")

        # Case 2: Approved by Time Off Officer and Employee's Approver, but no Time Off Officer is set
        self.holidays_type_4.responsible_ids = False     # No Time Off Officer set

        test_holiday_3 = self.env['hr.leave'].create({
            'name': 'Test leave',
            'employee_id': self.employee_hrmanager_id,
            'holiday_status_id': self.holidays_type_4.id,
            'date_from': datetime.today(),
            'date_to': (datetime.today() + timedelta(days=1)),
            'number_of_days': 1,
            'state': 'confirm',
        })

        activities = test_holiday_3.activity_ids
        self.assertEqual(len(activities), 1, "One activity should be created for the Employee's Approver.")
        self.assertEqual(activities.activity_type_id, self.env.ref('hr_holidays.mail_act_leave_approval'), "The activity type should be for leave approval by the Employee's Approver.")
        self.assertEqual(activities.user_id, self.employee_hrmanager.leave_manager_id, "The activity should be assigned to the Employee's Approver.")

    def test_time_off_date_edit(self):
        user_id = self.employee_emp.user_id
        employee_id = self.employee_emp.id

        leave = self.env['hr.leave'].with_user(user_id).create({
            'name': 'Test leave',
            'employee_id': employee_id,
            'holiday_status_id': self.holidays_type_2.id,
            'date_from': (datetime.today() - relativedelta(days=2)),
            'date_to': datetime.today()
        })

        two_days_after = (datetime.today() + relativedelta(days=2)).date()
        with Form(leave.with_user(user_id)) as leave_form:
            leave_form.request_date_from = two_days_after
            leave_form.request_date_to = two_days_after
        modified_leave = leave_form.save()

        self.assertEqual(modified_leave.request_date_from, two_days_after)
        self.assertEqual(modified_leave.request_date_to, two_days_after)
