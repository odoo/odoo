from datetime import date

from freezegun import freeze_time

from odoo.tests import tagged, warmup

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('at_install', '-post_install')  # stable query counts, without the overrides of other modules
class TestAccrualPerformance(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Accrual Time Off',
            'code': 'ACCRUAL_PERF',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        accrual_plan = cls.env['hr.leave.accrual.plan'].create({
            'name': 'Daily accrual plan',
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
            })],
            'work_entry_type_id': cls.work_entry_type.id,
        })
        cls.employees = cls.employee_emp | cls.employee_hruser | cls.employee_hrmanager
        with freeze_time('2026-01-01'):
            cls.allocations = cls.env['hr.leave.allocation'].create([{
                'name': 'Daily accrual',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': employee.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'date_from': date(2026, 1, 1),
                'number_of_days': 10,
            } for employee in cls.employees])
            cls.allocations.action_approve()
            leaves = cls.env['hr.leave'].create([{
                'name': f'Leave {month}',
                'employee_id': employee.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'request_date_from': date(2026, month, 3),
                'request_date_to': date(2026, month, 3),
            } for employee in cls.employees for month in (2, 4, 6)])
            leaves._action_validate()

    @warmup
    def test_update_accrual_daily_plan_queries(self):
        expected_query_count = 26
        # mail_tracking is not a dependency, but it is installed before this test in a full
        # build and then stores the tracked change of number_of_days
        if 'mail.tracking.value' in self.env:
            expected_query_count += 1
        with freeze_time('2026-06-30'), self.assertQueryCount(expected_query_count):
            self.allocations._update_accrual(date(2026, 6, 30))
        for allocation in self.allocations:
            # the 10 initial days and 1 day per day from January 2nd
            self.assertEqual(allocation.number_of_days, 10 + 180)
            self.assertEqual(allocation.leaves_taken, 3)
