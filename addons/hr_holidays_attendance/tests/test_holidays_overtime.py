# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase, tagged

from odoo.exceptions import ValidationError

from freezegun import freeze_time
import time

@tagged('post_install', '-at_install', 'holidays_attendance')
class TestHolidaysOvertime(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
        })
        cls.user = new_test_user(cls.env, login='user', groups='base.group_user', company_id=cls.company.id).with_company(cls.company)
        cls.user_manager = new_test_user(cls.env, login='manager', groups='base.group_user,hr_holidays.group_hr_holidays_user,hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)

        cls.manager = cls.env['hr.employee'].create({
            'name': 'Dominique',
            'user_id': cls.user_manager.id,
            'company_id': cls.company.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Barnabé',
            'user_id': cls.user.id,
            'parent_id': cls.manager.id,
            'company_id': cls.company.id,
        })

        cls.leave_type_no_alloc = cls.env['hr.leave.type'].create({
            'name': 'Overtime Compensation No Allocation',
            'company_id': cls.company.id,
            'requires_allocation': False,
            'overtime_deductible': True,
        })
        cls.leave_type_employee_allocation = cls.env['hr.leave.type'].create({
            'name': 'Overtime Compensation Employee Allocation',
            'company_id': cls.company.id,
            'requires_allocation': True,
            'employee_requests': True,
            'allocation_validation_type': 'hr',
            'overtime_deductible': True,
        })

        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                    'compensable_as_leave': True,
                }),
            ],
        })

        cls.employee.ruleset_id = cls.ruleset
        cls.employee.version_ids.sorted('date_version')[0].date_version = datetime(2020, 1, 1).date()

        cls.manager.ruleset_id = cls.ruleset
        cls.manager.version_ids.sorted('date_version')[0].date_version = datetime(2020, 1, 1).date()

    def new_attendance(self, check_in, check_out=False):
        return self.env['hr.attendance'].sudo().create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

    def _check_deductible(self, expected_hours):
        ded = self.env['hr.leave']._get_deductible_employee_overtime(self.employee)
        self.assertAlmostEqual(ded[self.employee], expected_hours, 5)

    def test_check_overtime(self):
        with self.with_user('user'):
            self.assertEqual(self.employee.total_overtime, 0, 'No overtime')

            with self.assertRaises(ValidationError):
                self.env['hr.leave'].create({
                    'name': 'no overtime',
                    'employee_id': self.employee.id,
                    'holiday_status_id': self.leave_type_no_alloc.id,
                    'request_date_from': datetime(2021, 1, 4),
                    'request_date_to': datetime(2021, 1, 4),
                    'state': 'confirm',
                })

            self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
            self.assertEqual(self.employee.total_overtime, 8, 'Should have 8 hours of overtime')

    def test_leave_adjust_overtime(self):
        self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
        self.assertEqual(self.employee.total_overtime, 8, 'Should have 8 hours of overtime')

        leave = self.env['hr.leave'].create({
            'name': 'no overtime',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type_no_alloc.id,
            'request_date_from': datetime(2021, 1, 4),
            'request_date_to': datetime(2021, 1, 4),
        })

        self._check_deductible(0)
        leave.action_refuse()
        self._check_deductible(8)

    def test_leave_check_overtime_write(self):
        self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
        self.new_attendance(check_in=datetime(2021, 1, 3, 8), check_out=datetime(2021, 1, 3, 16))
        self.assertEqual(self.employee.total_overtime, 16)

        leave = self.env['hr.leave'].create({
            'name': 'no overtime',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type_no_alloc.id,
            'request_date_from': '2021-01-04',
            'request_date_to': '2021-01-04',
        })
        self._check_deductible(8)

        leave.date_to = datetime(2021, 1, 5)
        self._check_deductible(0)
        with self.assertRaises(ValidationError):
            leave.date_to = datetime(2021, 1, 6)

        leave.date_to = datetime(2021, 1, 4)
        self._check_deductible(8)

    def test_employee_create_allocation(self):
        with self.with_user('user'):
            self.assertEqual(self.employee.total_overtime, 0)
            with self.assertRaises(ValidationError):
                self.env['hr.leave.allocation'].create({
                    'name': 'test allocation',
                    'holiday_status_id': self.leave_type_employee_allocation.id,
                    'employee_id': self.employee.id,
                    'number_of_days': 1,
                    'state': 'confirm',
                    'date_from': time.strftime('%Y-01-01'),
                    'date_to': time.strftime('%Y-12-31'),
                })

            self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
            self.assertAlmostEqual(self.employee.total_overtime, 8, 'Should have 8 hours of overtime')

            self.env['hr.leave.allocation'].sudo().create({
                'name': 'test allocation',
                'holiday_status_id': self.leave_type_employee_allocation.id,
                'employee_id': self.employee.id,
                'number_of_days': 1,
                'state': 'confirm',
                'date_from': time.strftime('%Y-01-01'),
                'date_to': time.strftime('%Y-12-31'),
            })
            self._check_deductible(0)

            leave_type = self.env['hr.leave.type'].sudo().create({
                'name': 'Overtime Compensation Employee Allocation',
                'company_id': self.company.id,
                'requires_allocation': True,
                'employee_requests': True,
                'allocation_validation_type': 'hr',
                'overtime_deductible': False,
            })

            # User can request another allocation even without overtime
            self.env['hr.leave.allocation'].create({
                'name': 'test allocation',
                'holiday_status_id': leave_type.id,
                'employee_id': self.employee.id,
                'number_of_days': 1,
                'state': 'confirm',
                'date_from': time.strftime('%Y-01-01'),
                'date_to': time.strftime('%Y-12-31'),
            })

    def test_allocation_check_overtime_write(self):
        self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
        self.new_attendance(check_in=datetime(2021, 1, 3, 8), check_out=datetime(2021, 1, 3, 16))
        self.assertEqual(self.employee.total_overtime, 16, 'Should have 16 hours of overtime')
        self._check_deductible(16)

        alloc = self.env['hr.leave.allocation'].create({
            'name': 'test allocation',
            'holiday_status_id': self.leave_type_employee_allocation.id,
            'employee_id': self.employee.id,
            'number_of_days': 1,
            'state': 'confirm',
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })
        self._check_deductible(8)

        with self.assertRaises(ValidationError):
            alloc.number_of_days = 3

        alloc.number_of_days = 2
        self._check_deductible(0)

    @freeze_time('2022-01-01')
    def test_leave_check_cancel(self):
        self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
        self.new_attendance(check_in=datetime(2021, 1, 3, 8), check_out=datetime(2021, 1, 3, 16))
        self.assertEqual(self.employee.total_overtime, 16)

        leave = self.env['hr.leave'].create({
            'name': 'no overtime',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type_no_alloc.id,
            'request_date_from': '2022-01-06',
            'request_date_to': '2022-01-06',
        })
        leave.with_user(self.user_manager).action_approve()
        self._check_deductible(8)

        self.assertTrue(leave.with_user(self.user).can_cancel)
        self.env['hr.holidays.cancel.leave'].with_user(self.user).with_context(default_leave_id=leave.id) \
            .new({'reason': 'Test remove holiday'}) \
            .action_cancel_leave()
        self._check_deductible(16)

    def test_public_leave_overtime(self):
        leave = self.env['resource.calendar.leaves'].create([{
            'name': 'Public Holiday',
            'date_from': datetime(2022, 5, 5, 6),
            'date_to': datetime(2022, 5, 5, 18),
        }])

        leave.company_id.write({
            'attendance_overtime_validation': 'no_validation',
        })
        self.assertNotEqual(leave.company_id, self.employee.company_id)
        self.manager.company_id = leave.company_id.id

        for emp in [self.employee, self.manager]:
            self.env['hr.attendance'].create({
                'employee_id': emp.id,
                'check_in': datetime(2022, 5, 5, 8),
                'check_out': datetime(2022, 5, 5, 17),
            })

        self.assertEqual(self.employee.total_overtime, 0, 'Should have 0 hours of overtime')
        self.assertEqual(self.manager.total_overtime, 8, 'Should have 8 hours of overtime (there is one hour of lunch)')

    def test_overtime_approval_after_refusal(self):
        self.new_attendance(check_in=datetime(2021, 1, 2, 8), check_out=datetime(2021, 1, 2, 16))
        self.new_attendance(check_in=datetime(2021, 1, 3, 8), check_out=datetime(2021, 1, 3, 16))
        self.assertEqual(self.employee.total_overtime, 16)

        leave = self.env['hr.leave'].create({
            'name': 'no overtime',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type_no_alloc.id,
            'request_date_from': '2022-1-6',
            'request_date_to': '2022-1-6',
        })
        leave.with_user(self.user_manager).action_approve()
        self._check_deductible(8)

        leave.with_user(self.user_manager).action_refuse()
        self._check_deductible(16)

        leave.with_user(self.user_manager).action_approve(check_state=False)
        self._check_deductible(8)
