# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.tests.common import tagged
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import ValidationError


@tagged('negative_time_off')
class TestNegative(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Limited with negative',
            'leave_validation_type': 'no_validation',
            'requires_allocation': True,
            'company_id': cls.company.id,
            'allows_negative': True,
            'max_allowed_negative': 5,
        })

        cls.allocation_2022 = cls.env['hr.leave.allocation'].create({
            'employee_id': cls.employee_emp_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': '2022-01-01',
            'date_to': '2022-12-31',
            'number_of_days': 1,
        })
        cls.allocation_2022.action_approve()

        cls.allocation_2023 = cls.env['hr.leave.allocation'].create({
            'employee_id': cls.employee_emp_id,
            'holiday_status_id': cls.leave_type.id,
            'date_from': '2023-01-01',
            'number_of_days': 5,
        })
        cls.allocation_2023.action_approve()

    def test_negative_time_off(self):
        with freeze_time('2022-10-02'):
            # At the start of 2022, the user receives 1 days, his balance is at 1
            # The first 2022 leave brings the user balance at -4
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'first 2022 leave of 5 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2022, 10, 24),
                'request_date_to': datetime(2022, 10, 28),
            })

        with freeze_time('2023-10-02'):
            # At the start of 2023, the user receives 5 days, his balance is at 1
            # The first leave of 2023 brings the balance at -4
            self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'first 2023 leave of 5 days',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'request_date_from': datetime(2023, 10, 9),
                'request_date_to': datetime(2023, 10, 13),
            })

            # The leave should not be possible to take since it would bring the balance at -9
            with self.assertRaises(ValidationError):
                self.env['hr.leave'].with_user(self.user_employee_id).create({
                    'name': 'not takable leaves of 5 days',
                    'holiday_status_id': self.leave_type.id,
                    'employee_id': self.employee_emp_id,
                    'request_date_from': datetime(2023, 10, 16),
                    'request_date_to': datetime(2023, 10, 20),
                })

            # The second leave of 2023 brings the balance at -5
            one_day_leave = self.env['hr.leave'].with_user(self.user_employee_id).create({
                'name': 'Second 2023 leave of 1 day',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp_id,
                'request_date_from': datetime(2023, 10, 23),
                'request_date_to': datetime(2023, 10, 23),
            })

            # The leave should not be possible to edit since it would bring the balance at -6
            with self.assertRaises(ValidationError):
                one_day_leave.with_user(self.user_hrmanager_id).write({
                    'date_to': datetime(2023, 10, 24),
                })
