# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'payroll_right_to_legal_leaves')
class TestPayrollRightToLegalLeaves(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollRightToLegalLeaves, cls).setUpClass()

        cls.paid_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'hr',
            'leave_validation_type': 'both',
            'responsible_ids': [Command.link(cls.env.ref('base.user_admin').id)],
            'request_unit': 'day'
        })

        cls.resource_calendar_24_hours_per_week_5_days_per_week = cls.resource_calendar.copy({
            'name': 'Calendar 24 Hours/Week',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

        cls.resource_calendar_24_hours_per_week_4_days_per_week = cls.resource_calendar.copy({
            'name': 'Calendar 24 Hours/Week',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
            ]
        })

        cls.resource_calendar_20_hours_per_week = cls.resource_calendar.copy({
            'name': 'Calendar 20 Hours/Week',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

    def test_credit_time_for_employee_test_example1(self):
        """
        Test Case:
        In 2017, Employee Test has a Full-Time contract (38 hours/week - 5 days/week)
        In 2018, he keeps his contract until 31/03/2018 and take no time off.
        After that, he has a new contract on 01/04/2018, he works 30 hours/week (4 days/week)

        The calculation of paid time off should be :
        On 01/01/2018, this employee has right 20 days of Paid Time Off.
        On 01/04/2018, this employee should has 16 days of Paid Time Off.
        """
        wizard = self.env['hr.payroll.alloc.paid.leave'].new({
            'year': 2017,
            'holiday_status_id': self.paid_time_off_type.id
        })
        wizard.alloc_employee_ids = wizard.alloc_employee_ids.filtered(lambda alloc_employee: alloc_employee.employee_id.id == self.employee_test.id)
        self.assertEqual(wizard.alloc_employee_ids.paid_time_off, 20, "Employee Test should have 20 days for 2018")

        view = wizard.generate_allocation()
        allocation = self.env['hr.leave.allocation'].search(view['domain'])
        allocation.action_validate()

        self.assertEqual(allocation.number_of_days, 20)
        self.assertEqual(allocation.max_leaves_allocated, 152)

        employee_test_current_contract = self.test_contracts[-1]

        # Credit time
        wizard = self.env['l10n_be.hr.payroll.schedule.change.wizard'].with_context(allowed_company_ids=self.belgian_company.ids, active_id=employee_test_current_contract.id).new({
            'date_start': date(2018, 4, 1),
            'date_end': date(2018, 4, 30),
            'resource_calendar_id': self.resource_calendar_30_hours_per_week.id,
            'leave_type_id': self.paid_time_off_type.id,
            'previous_contract_creation': True,
        })
        self.assertEqual(wizard.time_off_allocation, 16)
        view = wizard.with_context(force_schedule=True).action_validate()
        self.env['l10n_be.schedule.change.allocation']._cron_update_allocation_from_new_schedule(date(2018, 4, 1))
        self.assertEqual(allocation.number_of_days, 16)

    def test_credit_time_for_employee_test_example2(self):
        """
        Test Case:
        In 2017, Employee Test has a Full-Time contract (38 hours/week - 5 days/week)
        In 2018, he keeps his contract until 31/03/2018 and take 4 days of paid time offs.
        After that, he has a new contract on 01/04/2018, he works 30 hours/week (4 days/week)

        The calculation of paid time off should be :
        On 01/01/2018, this employee has right 20 days of Paid Time Off.
        On 01/04/2018, this employee should has 16 days of Paid Time Off.
        """
        wizard = self.env['hr.payroll.alloc.paid.leave'].new({
            'year': 2017,
            'holiday_status_id': self.paid_time_off_type.id
        })
        wizard.alloc_employee_ids = wizard.alloc_employee_ids.filtered(lambda alloc_employee: alloc_employee.employee_id.id == self.employee_test.id)
        self.assertEqual(wizard.alloc_employee_ids.paid_time_off, 20, "Employee Test should have 20 days for 2018")

        view = wizard.generate_allocation()
        allocation = self.env['hr.leave.allocation'].search(view['domain'])
        allocation.action_validate()

        self.assertEqual(allocation.number_of_days, 20)
        self.assertEqual(allocation.max_leaves_allocated, 152)

        employee_test_current_contract = self.test_contracts[-1]

        leave = self.env['hr.leave'].create({
            'holiday_status_id': self.paid_time_off_type.id,
            'employee_id': self.employee_test.id,
            'request_date_from': date(2018, 2, 1),
            'request_date_to': date(2018, 2, 5),
        })
        leave.action_validate()

        # Credit time
        wizard = self.env['l10n_be.hr.payroll.schedule.change.wizard'].with_context(allowed_company_ids=self.belgian_company.ids, active_id=employee_test_current_contract.id).new({
            'date_start': date(2018, 4, 1),
            'date_end': date(2018, 4, 30),
            'resource_calendar_id': self.resource_calendar_30_hours_per_week.id,
            'leave_type_id': self.paid_time_off_type.id,
            'previous_contract_creation': True,
        })
        self.assertEqual(wizard.time_off_allocation, 16)
        view = wizard.with_context(force_schedule=True).action_validate()
        self.env['l10n_be.schedule.change.allocation']._cron_update_allocation_from_new_schedule(date(2018, 4, 1))
        self.assertEqual(allocation.number_of_days, 16, "15 days left becomes 11.5 (15 * .78, rounded down) + 5 for the days already taken.")

    def test_credit_time_for_employee_test_example3(self):
        """
        Test Case:
        In 2017, Employee Test has 3 contracts :
            - From 01/01/2017 to 05/31/2017: 38 hours/week (5 days/week)
            - From 06/01/2017 to 07/31/2017: 24 hours/week (5 days/week)
            - From 08/01/2017 to 12/31/2017: 20 hours/week (5 days/week)

        In 2018, he keeps his contract until 03/31/2018 and take 4 days of paid time offs.
        After that, he has a new contract on 04/01/2018, he works 30 hours/week (4 days/week)

        The calculation of paid time off should be :
        On 01/01/2018, this employee has right 20 days of Paid Time Off.
        On 04/01/2018, this employee should has 16 days of Paid Time Off.
        """
        employee_test_first_contract = self.test_contracts[-1]
        employee_test_first_contract.write({
            'date_end': date(2017, 5, 31),
            'state': 'close'
        })
        self.test_contracts |= employee_test_first_contract.copy({
            'name': "Employee Test's Contract",
            'employee_id': self.employee_test.id,
            'resource_calendar_id': self.resource_calendar_24_hours_per_week_5_days_per_week.id,
            'date_start': date(2017, 6, 1),
            'date_end': date(2017, 7, 31),
            'wage': employee_test_first_contract.wage / 24 * 38
        })

        self.test_contracts |= employee_test_first_contract.copy({
            'name': "Employee Test's Contract",
            'employee_id': self.employee_test.id,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
            'date_start': date(2017, 8, 1),
            'date_end': date(2017, 12, 31),
            'wage': employee_test_first_contract.wage / 20 * 38
        })
        self.test_contracts.write({'state': 'close'})

        employee_test_current_contract = employee_test_first_contract.copy({
            'name': "Employee Test's Contract",
            'employee_id': self.employee_test.id,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
            'date_start': date(2018, 1, 1),
            'date_end': False,
            'wage': employee_test_first_contract.wage / 20 * 38
        })
        employee_test_current_contract.write({'state': 'open'})
        self.test_contracts |= employee_test_current_contract

        wizard = self.env['hr.payroll.alloc.paid.leave'].new({
            'year': 2017,
            'holiday_status_id': self.paid_time_off_type.id
        })
        wizard.alloc_employee_ids = wizard.alloc_employee_ids.filtered(lambda alloc_employee: alloc_employee.employee_id.id == self.employee_test.id)
        self.assertEqual(wizard.alloc_employee_ids.paid_time_off, 15)
        self.assertEqual(wizard.alloc_employee_ids.paid_time_off_to_allocate, 10, "10 days is equal to 20 half days")

        view = wizard.generate_allocation()
        allocation = self.env['hr.leave.allocation'].search(view['domain'])
        allocation.action_validate()

        self.assertEqual(allocation.number_of_days, 10)
        self.assertAlmostEqual(allocation.max_leaves_allocated, 15 * 7.6, places=0)

        leave = self.env['hr.leave'].create({
            'holiday_status_id': self.paid_time_off_type.id,
            'employee_id': self.employee_test.id,
            'request_date_from': date(2018, 2, 1),
            'date_from': date(2018, 2, 1),
            'request_date_to': date(2018, 2, 3),
            'date_to': date(2018, 2, 3),
            'number_of_days': 1.5
        })
        leave.action_validate()

        # Credit time
        wizard = self.env['l10n_be.hr.payroll.schedule.change.wizard'].with_context(allowed_company_ids=self.belgian_company.ids, active_id=employee_test_current_contract.id).new({
            'date_start': date(2018, 4, 1),
            'date_end': date(2018, 4, 30),
            'resource_calendar_id': self.resource_calendar_24_hours_per_week_4_days_per_week.id,
            'leave_type_id': self.paid_time_off_type.id,
            'previous_contract_creation': True,
        })
        self.assertEqual(wizard.time_off_allocation, 12.5)
        view = wizard.with_context(force_schedule=True).action_validate()
        self.env['l10n_be.schedule.change.allocation']._cron_update_allocation_from_new_schedule(date(2018, 4, 1))
        self.assertEqual(allocation.number_of_days, 12.5, "10 days allocated by the credit")
