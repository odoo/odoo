# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from odoo import Command

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveBalanceReport(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.leave_type = cls.env['hr.work.entry.type'].create({
            'name': 'Paid Time Off',
            'code': 'Paid Time Off',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.accrual_plan = cls.env['hr.leave.accrual.plan'].create({
            'name': 'Test Accrual Plan',
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'start',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': [
                Command.create({
                    'added_value_type': 'day',
                    'added_value': 2,
                    'frequency': 'monthly',
                    'milestone_date': 'creation',
                    'action_with_unused_accruals': 'all',
                }),
            ],
        })

    def _create_allocation(self, employee, leave_type, days, date_from, date_to=False):
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Test Allocation',
            'employee_id': employee.id,
            'work_entry_type_id': leave_type.id,
            'number_of_days': days,
            'date_from': date_from,
            'date_to': date_to,
        })
        allocation._action_validate()
        return allocation

    def _create_leave(self, employee, leave_type, date_from, date_to):
        leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': employee.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
        })
        leave.action_approve()
        leave._action_validate()
        return leave

    def _get_report_data(self, employee, leave_type):
        """Returns (allocated, left) from the balance report."""
        report = self.env['hr.leave.employee.type.report'].search([
            ('employee_id', '=', employee.id),
            ('work_entry_type_id', '=', leave_type.id),
        ])
        allocated = report.filtered(lambda r: r.holiday_status == 'allocated').number_of_days
        left = report.filtered(lambda r: r.holiday_status == 'left').number_of_days
        return allocated, left

    @freeze_time("2026-06-15")
    def test_01_single_allocation_with_leaves(self):
        """
        Single allocation Jan-Dec 2026,
        Expected: allocated = 20, left = 20 - 5 (3 days March + 2 days May) = 15
        """
        self._create_allocation(
            self.employee_emp, self.leave_type, 20,
            date(2026, 1, 1), date(2026, 12, 31),
        )
        self._create_leave(
            self.employee_emp, self.leave_type,
            date(2026, 3, 2), date(2026, 3, 4),  # 3 days
        )
        self._create_leave(
            self.employee_emp, self.leave_type,
            date(2026, 5, 4), date(2026, 5, 5),  # 2 days
        )
        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, 20)
        self.assertEqual(left, 15)

    @freeze_time("2026-06-15")
    def test_02_allocation_spanning_multiple_years(self):
        """
        Allocation spans 2025-2026.
        Leaves taken in both years.
        """
        self._create_allocation(
            self.employee_emp, self.leave_type, 20,
            date(2025, 1, 1), date(2026, 12, 31),
        )
        self._create_leave(
            self.employee_emp, self.leave_type,
            date(2025, 3, 3), date(2025, 3, 7),  # 5 days in 2025
        )
        self._create_leave(
            self.employee_emp, self.leave_type,
            date(2026, 2, 2), date(2026, 2, 4),  # 3 days in 2026
        )
        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, 20)
        self.assertEqual(left, 12)

    @freeze_time("2026-02-15")
    def test_03_two_allocations_same_type_leaves_in_both_periods(self):
        """
        Two allocations same leave type:
          - Allocation 1: Jan-Dec 2026, 10 days → valid today (Feb 15)
          - Allocation 2: Mar-Dec 2026, 5 days  → NOT valid today (Feb 15)
        Leaves taken in January (3 days).
        Today = Feb 15 → only Allocation 1 is valid.
        Expected: allocated = 10, left = 10 - 3 = 7
        """
        self._create_allocation(
            self.employee_emp, self.leave_type, 10,
            date(2026, 1, 1), date(2026, 12, 31),
        )
        self._create_allocation(
            self.employee_emp, self.leave_type, 5,
            date(2026, 3, 1), date(2026, 12, 31),
        )
        self._create_leave(
            self.employee_emp, self.leave_type,
            date(2026, 1, 6), date(2026, 1, 8),  # 3 days in January
        )
        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, 10)  # only allocation 1 valid on Feb 15
        self.assertEqual(left, 7)        # 10 - 3

    @freeze_time("2026-02-15")
    def test_04_accrual_allocation_leaves_in_current_period(self):
        """
        Accrual plan: 2 days at start of every month.
        Allocation created Jan 1, accrual updated Feb 15 → 4 days accrued.
        Leave taken: 2 days in January.
        Expected: allocated = 4, left = 2
        """
        with freeze_time("2026-01-01"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Test Accrual Allocation',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.accrual_plan.id,
                'date_from': date(2026, 1, 1),
                'number_of_days': 0,
            })

        with freeze_time("2026-02-15"):
            allocation._action_validate()
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 4)  # confirm accrual working

            self._create_leave(
                self.employee_emp, self.leave_type,
                date(2026, 1, 6), date(2026, 1, 7),  # 2 days in January
            )

            allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
            self.assertEqual(allocated, 4)
            self.assertEqual(left, 2)

    @freeze_time("2026-02-15")
    def test_05_accrual_allocation_leaves_in_future_period(self):
        """
        Accrual plan: 2 days at start of every month.
        Allocation created Jan 1, accrual updated Feb 15 → 4 days accrued.
        Leave taken: 2 days in April (future).
        Expected: allocated = 4, left = 2
        """
        with freeze_time("2026-01-01"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Test Accrual Allocation',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.accrual_plan.id,
                'date_from': date(2026, 1, 1),
                'number_of_days': 0,
            })

        with freeze_time("2026-02-15"):
            allocation._action_validate()
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 4)  # confirm accrual working

            self._create_leave(
                self.employee_emp, self.leave_type,
                date(2026, 4, 1), date(2026, 4, 2),  # 2 days in April (future)
            )

            allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
            self.assertEqual(allocated, 4)
            self.assertEqual(left, 4)
