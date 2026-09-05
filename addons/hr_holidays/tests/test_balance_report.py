# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from dateutil.relativedelta import relativedelta
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
            'accrued_gain_time': 'start',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': [
                Command.create({
                    'added_value': 2,
                    'added_value_type': 'day',
                    'frequency': 'monthly',
                    'milestone_date': 'creation',
                    'action_with_unused_accruals': 'all',
                    'carryover_options': 'unlimited',
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
        domain = [
            ('employee_id', '=', employee.id),
            ('work_entry_type_id', '=', leave_type.id),
        ]
        report = self.env['hr.leave.employee.type.report'].search(domain)
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

    @freeze_time("2026-06-15")
    def test_03_two_allocations_same_type_leaves_in_both_periods(self):
        today = date.today()
        # Allocation 1 already active; allocation 2 starts next month (not valid yet in SQL)
        self._create_allocation(
            self.employee_emp,
            self.leave_type, 10,
            today - relativedelta(months=5),
            today + relativedelta(months=6))
        self._create_allocation(
            self.employee_emp,
            self.leave_type, 5,
            today + relativedelta(months=1),
            today + relativedelta(months=7))  # future start
        self._create_leave(
            self.employee_emp,
            self.leave_type,
            today - relativedelta(months=3) + relativedelta(days=1),
            today - relativedelta(months=3, days=-3))  # 3 past days
        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, 10)
        self.assertEqual(left, 7)

    @freeze_time("2026-05-25")
    def test_04_accrual_allocation_leaves_in_current_period(self):
        """
        Accrual plan: 2 days at start of every month.
        Allocation started 4 months ago. Leave taken in the past.
        Expected: allocated = accrued days, left = accrued - leave_days
        """
        today = date.today()
        alloc_start = (today - relativedelta(months=4)).replace(day=1)

        allocation = self.env['hr.leave.allocation'].with_user(
            self.user_hrmanager_id,
        ).with_context(tracking_disable=True).create({
            'name': 'Test Accrual Allocation',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.leave_type.id,
            'accrual_plan_id': self.accrual_plan.id,
            'date_from': alloc_start,
            'number_of_days': 0,
        })
        allocation._action_validate()
        allocation._process_accrual_plans()
        allocation.flush_recordset()
        accrued_days = allocation.number_of_days
        self.assertTrue(accrued_days > 0, "Accrual should have generated days by now")

        # Take a leave in the past (last month)
        past_start = (today - relativedelta(months=1)).replace(day=6)
        past_end = (today - relativedelta(months=1)).replace(day=7)
        leave = self._create_leave(
            self.employee_emp, self.leave_type, past_start, past_end,
        )

        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, accrued_days)
        self.assertEqual(left, accrued_days - leave.number_of_days)

    @freeze_time("2026-06-15")
    def test_05_accrual_allocation_leaves_in_future_period(self):
        """
        Accrual plan: 2 days at start of every month.
        Allocation started 4 months ago. Leave taken in the future (next month).
        Expected: allocated = accrued days, left = accrued (future leave NOT deducted)
        """
        today = date.today()
        alloc_start = (today - relativedelta(months=4)).replace(day=1)

        allocation = self.env['hr.leave.allocation'].with_user(
            self.user_hrmanager_id
        ).with_context(tracking_disable=True).create({
            'name': 'Test Accrual Allocation',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.leave_type.id,
            'accrual_plan_id': self.accrual_plan.id,
            'date_from': alloc_start,
            'number_of_days': 0,
        })
        allocation._action_validate()
        allocation._process_accrual_plans()
        allocation.flush_recordset()
        accrued_days = allocation.number_of_days
        self.assertTrue(accrued_days > 0, "Accrual should have generated days by now")

        # Take a leave in the future (next month) — should NOT be deducted
        future_start = date(2026, 12, 1)
        future_end = date(2026, 12, 2)
        self._create_leave(
            self.employee_emp, self.leave_type, future_start, future_end,
        )

        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, accrued_days)
        self.assertEqual(left, accrued_days)  # future leave with accrual → not deducted  # future accrual leave not deducted

    @freeze_time("2026-06-15")
    def test_06_leave_consumed_by_expired_allocation_not_deducted(self):
        """
        Two allocations for the same leave type:
          - Allocation 1: expired last month, 10 days. A 3-day leave was taken during it.
          - Allocation 2: currently active, 15 days. No leaves taken against it.

        The leave from the expired allocation does NOT overlap any currently-valid
        allocation, so it must NOT reduce today's balance.
        Expected: allocated = 15 (only alloc 2), left = 15
        """
        today = date.today()
        self._create_allocation(
            self.employee_emp, self.leave_type, 10,
            today - relativedelta(months=6), today - relativedelta(months=1),
        )
        # Leave taken during the expired allocation's period
        leave_start = today - relativedelta(months=3, day=2)
        leave_end = today - relativedelta(months=3, day=4)
        self._create_leave(self.employee_emp, self.leave_type, leave_start, leave_end)
        # Currently active allocation
        self._create_allocation(
            self.employee_emp, self.leave_type, 15,
            today - relativedelta(days=15), today + relativedelta(months=6),
        )

        allocated, left = self._get_report_data(self.employee_emp, self.leave_type)
        self.assertEqual(allocated, 15)
        self.assertEqual(left, 15)  # leave from expired allocation not deducted

    @freeze_time("2026-05-25")
    def test_07_allows_negative_shows_negative_balance(self):
        """
        Leave type with allows_negative=True.
        5 days allocated, 8 days taken → left should be -3 (not floored to 0).
        """
        today = date.today()
        negative_leave_type = self.env['hr.work.entry.type'].create({
            'name': 'Negative Time Off',
            'code': 'Negative Time Off',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'allows_negative': True,
            'max_allowed_negative': 10,
        })
        self._create_allocation(
            self.employee_emp, negative_leave_type, 5,
            today - relativedelta(months=6), today + relativedelta(months=6),
        )
        # 8-day leave exceeds allocation
        leave_start = today - relativedelta(months=2, day=2)
        leave_end = today - relativedelta(months=2, day=11)
        self._create_leave(self.employee_emp, negative_leave_type, leave_start, leave_end)

        allocated, left = self._get_report_data(self.employee_emp, negative_leave_type)
        self.assertEqual(allocated, 5)
        self.assertEqual(left, -3, "Left should be negative for allows_negative types")
