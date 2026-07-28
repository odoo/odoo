# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'accruals')
class TestAccrualAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAccrualAllocations, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Accrual Time Off',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no',
        })
        cls.accrual_plan = cls.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Test Seniority Plan',
            'level_ids': [
                (0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                }),
                (0, 0, {
                    'start_count': 4,
                    'start_type': 'year',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                }),
                (0, 0, {
                    'start_count': 8,
                    'start_type': 'year',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                }),
            ]
        })

    def _test_past_accrual(self):
        with freeze_time("2023-12-01"):
            allocation = self.env['hr.leave.allocation'].create({
                'employee_id': self.employee_emp_id,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.accrual_plan.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': date(2000, 1, 1),
                'number_of_days': 0,
            })

            allocation._process_accrual_plans()

            self.assertEqual(allocation.number_of_days, 0)
