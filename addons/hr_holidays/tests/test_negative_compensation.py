# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.tests.common import tagged
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install')
class TestNegativeCompensation(TestHrHolidaysCommon):
    """
    Test ensuring that negative balances from previous years are correctly
    compensated by expired allocations from intermediate years that had a surplus.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a leave type that allows negative cap up to -2
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Limited with negative',
            'leave_validation_type': 'no_validation',
            'requires_allocation': 'yes',
            'company_id': cls.company.id,
            'allows_negative': True,
            'max_allowed_negative': 2,
        })

        # Allocation 2021: 3 days
        cls.allocation_2021 = cls.env['hr.leave.allocation'].create({
            'employee_id': cls.employee_emp_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': '2021-01-01',
            'date_to': '2021-12-31',
            'number_of_days': 3,
        })
        cls.allocation_2021.action_validate()

        # Allocation 2022: 3 days
        cls.allocation_2022 = cls.env['hr.leave.allocation'].create({
            'employee_id': cls.employee_emp_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
            'number_of_days': 3,
        })
        cls.allocation_2022.action_validate()

        # Allocation 2023: 3 days
        cls.allocation_2023 = cls.env['hr.leave.allocation'].create({
            'employee_id': cls.employee_emp_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': '2023-01-01',
            'date_to': '2023-12-31',
            'number_of_days': 3,
        })
        cls.allocation_2023.action_validate()

    def test_negative_compensate(self):
        # 2021: User receives 3 days. Takes 5 days. Balance: -2.
        with freeze_time('2021-10-04'):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'first 2021 leave of 5 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2021, 10, 25),
                'request_date_to': datetime(2021, 10, 29),
            })

        # 2022: User receives 3 days. Takes 1 day. Balance for year: +2.
        # This surplus of +2 should compensate the -2 from 2021. Global Balance: 0.
        with freeze_time('2022-10-02'):
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'first 2022 leave of 1 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2022, 10, 24),
                'request_date_to': datetime(2022, 10, 24),
            })

        # 2023: User receives 3 days.
        with freeze_time('2023-10-02'):
            # Takes 3 days. Global Balance goes to 0.
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'first 2023 leave of 3 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2023, 10, 2),
                'request_date_to': datetime(2023, 10, 4),
            })

            # User tries to take 1 more day.
            # Expected behavior: Allowed, as the global balance would be -1 (limit is -2).
            # Previous Bug: Failed because 2022 surplus was ignored, calculating balance as -3.
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'second 2023 leave of 1 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2023, 10, 9),
                'request_date_to': datetime(2023, 10, 9),
            })
