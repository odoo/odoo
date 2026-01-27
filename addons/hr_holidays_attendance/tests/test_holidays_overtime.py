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
        ded = self.employee._get_deductible_employee_overtime()
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

            overtime_leave_data = self.leave_type_no_alloc.get_allocation_data(self.employee)
            self.assertEqual(overtime_leave_data[self.employee][0][1]['virtual_remaining_leaves'], 8.0)
            # `employee_company` must be present to avoid traceback when opening the Time Off Type
            self.assertTrue(overtime_leave_data[self.employee][0][1].get('employee_company'))

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

    def test_public_leave_overtime_with_timing_rule(self):
        ruleset_with_timing_rule = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                    'compensable_as_leave': True,
                }),
                Command.create({
                    'name': 'Rule employee is off',
                    'base_off': 'timing',
                    'timing_type': 'leave',
                }),
            ],
        })
        (self.employee.version_ids + self.manager.version_ids).ruleset_id = ruleset_with_timing_rule
        self.manager.company_id = self.env.company
        leave = self.env['resource.calendar.leaves'].with_company(self.manager.company_id).create([{
            'name': 'Public Holiday',
            'date_from': datetime(2022, 5, 5, 6),
            'date_to': datetime(2022, 5, 5, 18),
        }])

        leave.company_id.write({
            'attendance_overtime_validation': 'no_validation',
        })
        for emp in [self.employee, self.manager]:
            self.env['hr.attendance'].create({
                'employee_id': emp.id,
                'check_in': datetime(2022, 5, 5, 8),
                'check_out': datetime(2022, 5, 5, 17),
            })

        self.assertEqual(self.employee.total_overtime, 0, 'Should have 0 hours of overtime')
        self.assertEqual(self.manager.total_overtime, 9, "Should have 9 hours of overtime")

    def test_public_leave_overtime_without_timing_rule(self):
        self.manager.company_id = self.env.company
        leave = self.env['resource.calendar.leaves'].with_company(self.manager.company_id).create([{
            'name': 'Public Holiday',
            'date_from': datetime(2022, 5, 5, 6),
            'date_to': datetime(2022, 5, 5, 18),
        }])

        leave.company_id.write({
            'attendance_overtime_validation': 'no_validation',
        })
        for emp in [self.employee, self.manager]:
            self.env['hr.attendance'].create({
                'employee_id': emp.id,
                'check_in': datetime(2022, 5, 5, 8),
                'check_out': datetime(2022, 5, 5, 17),
            })

        self.assertEqual(self.employee.total_overtime, 0, 'Should have 0 hours of overtime')
        self.assertEqual(self.manager.total_overtime, 9, "Should have 9 hours of overtime (because of the quantity rule)")

    def test_worked_leave_type_overtime(self):
        """ Test that an attendance during a worked time off doesn't count as overtime. """
        calendar = self.env['resource.calendar'].create({'name': 'Calendar'})
        self.env['hr.version'].create({
            'date_version': datetime(2021, 1, 1),
            'contract_date_start': datetime(2021, 1, 1),
            'contract_date_end': datetime(2021, 12, 31),
            'name': 'Contract 2021',
            'resource_calendar_id': calendar.id,
            'wage': 5000.0,
            'employee_id': self.employee.id,
        })

        leave_type_worked = self.env['hr.leave.type'].create({
            'name': 'Worked Leave Type',
            'company_id': self.company.id,
            'requires_allocation': False,
            'overtime_deductible': False,
            'time_type': 'other',
        })

        leave = self.env['hr.leave'].create({
            'name': 'no overtime',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type_worked.id,
            'request_date_from': datetime(2021, 1, 5),
            'request_date_to': datetime(2021, 1, 5),
        })
        leave._action_validate()

        att = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 5, 8),
            'check_out': datetime(2021, 1, 5, 16),
        })

        self.assertEqual(att.overtime_hours, 0)
        self.assertEqual(att.worked_hours, 7)

        self.assertEqual(self.employee.total_overtime, 0, 'Should have 0 hours of overtime')

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

    def test_get_overtime_data_by_employee(self):
        # Even if employee has not overtime, it should still appear in return
        # value
        expected_overtime_data = {
            'compensable_overtime': 0,
            'not_compensable_overtime': 0,
            'unspent_compensable_overtime': 0,
        }
        overtime_data = self.employee.get_overtime_data_by_employee()
        self.assertEqual(
            overtime_data[self.employee.id],
            expected_overtime_data,
            "get_overtime_data_by_employee() did not return an empty overtime_data",
        )

        # These attendances will create some extra hours that is deductible as
        # time off
        self.new_attendance(
            check_in=datetime(2021, 1, 1, 8), check_out=datetime(2021, 1, 1, 20)
        )
        self.new_attendance(
            check_in=datetime(2021, 1, 2, 4), check_out=datetime(2021, 1, 2, 20)
        )
        self.new_attendance(
            check_in=datetime(2021, 2, 2, 4), check_out=datetime(2021, 2, 2, 18)
        )

        # The extra hours from the next attendances will not be deductible as
        # time off. Affects compensable_overtime's value.
        not_compensable_ruleset = self.env[
            'hr.attendance.overtime.ruleset'
        ].create(
            {
                'name': 'Ruleset schedule quantity',
                'rule_ids': [
                    Command.create(
                        {
                            'name': 'Extra Mile',
                            'base_off': 'quantity',
                            'expected_hours_from_contract': True,
                            'quantity_period': 'day',
                            'compensable_as_leave': False,
                        }
                    ),
                ],
            }
        )
        self.employee.ruleset_id = not_compensable_ruleset

        # Creates extra hours, but won't be usable as time off
        # Affects not_compensable_overtime's value.
        self.new_attendance(
            check_in=datetime(2021, 3, 3, 5), check_out=datetime(2021, 3, 3, 20)
        )

        # Use some of the overtime as a day off (8 hours)
        # Affects unspent_compensable_time's value
        leave = self.env['hr.leave'].create(
            {
                'name': 'no overtime',
                'employee_id': self.employee.id,
                'holiday_status_id': self.leave_type_no_alloc.id,
                'request_date_from': '2022-1-6',
                'request_date_to': '2022-1-6',
            }
        )
        leave.with_user(self.user_manager).action_approve()

        expected_overtime_data = {
            'compensable_overtime': 24.0,
            'not_compensable_overtime': 6.0,
            'unspent_compensable_overtime': 16.0,
        }
        overtime_data = self.employee.get_overtime_data_by_employee()
        self.assertEqual(
            overtime_data[self.employee.id],
            expected_overtime_data,
            "get_overtime_data_by_employee() did not return the expected values",
        )
