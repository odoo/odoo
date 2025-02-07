import datetime
from freezegun import freeze_time

from odoo.tests import tagged, users

from odoo.addons.hr_holidays.tests.test_accrual_allocations import TestAccrualAllocations
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install', 'accruals')
class TestAccrualAllocationsWithContracts(TestAccrualAllocations):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.yearly_accrual_plan = cls.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Yearly accrual',
            'company_id': cls.belgian_company.id,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'is_based_on_worked_time': False,
            'level_ids': [(0, 0, {
                'added_value': 10,
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'frequency': 'yearly',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.test_user = mail_new_test_user(
            cls.env, login='test_user',
            company_id=cls.belgian_company.id,
            groups='base.group_user,hr_holidays.group_hr_holidays_manager'
        )

        cls.leave_type_without_allocation = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'no',
            'allocation_validation_type': 'hr',
        })

        cls.resource_calendar_mid_time = cls.resource_calendar.copy({
            'name': 'Calendar (Mid-Time)',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
            ]
        })

        cls.employee_with_multiple_schedules = cls.env['hr.employee'].create({
            'name': 'Employee with different working schedules',
            'company_id': cls.belgian_company.id,
        })
        first_contract = cls.env['hr.contract'].create({
            'name': "employee's contract",
            'employee_id': cls.employee_with_multiple_schedules.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': datetime.date(2024, 1, 1),
            'date_end':   datetime.date(2024, 6, 30),
            'wage': 2500
        })
        first_contract.write({'state': 'close'})
        second_contract = first_contract.copy({
            'resource_calendar_id': cls.resource_calendar_mid_time.id,
            'date_start': datetime.date(2024, 7, 1),
            'date_end': False
        })
        second_contract.write({'state': 'open'})

    @users('test_user')
    def test_accrual_plan_with_changing_working_schedules_1(self):
        """
        Accrual period 1 year, accrual value = 10 days
        Employee worked from january to june in full time, then from july to december in half time.

        Accrual plan is not based on worked time. Value for the year should be 7.5.
        0,5 (accrual period) * 10 (accrual value) * 100% = 5 days
        + 0,5 (accrual period) * 10 (accrual value) * 50% = 2.5 days
        """

        self.leave_type['company_id'] = self.belgian_company.id

        with freeze_time("2024-01-01"):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_with_multiple_schedules.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.yearly_accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1),
            })
            allocation.action_approve()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 7.5, 1)

    @users('test_user')
    def test_accrual_plan_with_changing_working_schedules_2(self):
        """
        Accrual period 1 year, accrual value = 10 days
        Employee worked from january to june in full time, then from july to december in half time.
        Unpaid period in march, april, may.

        Value should be computed like this :
        0,5 (accrual period) * 10 (accrual value) * 100% (working rate) = 5 days * (3/6) (based on worked time) = 2,5 days
        + 0,5 (accrual period) * 10 (accrual value) * 50% (working rate) = 2,5 days * (6/6)  (based on worked time) = 2,5 days

        Total number of days is 5
        """

        self.yearly_accrual_plan['is_based_on_worked_time'] = True

        self.leave_type['company_id'] = self.belgian_company.id
        self.leave_type_without_allocation['company_id'] = self.belgian_company.id

        with freeze_time("2024-01-01"):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_with_multiple_schedules.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.yearly_accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1),
            })
            allocation.action_approve()
            leave = self.env['hr.leave'].with_context(tracking_disable=True).create({
                'name': '3 months time off',
                'employee_id': self.employee_with_multiple_schedules.id,
                'holiday_status_id': self.leave_type_without_allocation.id,
                'request_date_from': datetime.date(2024, 3, 1),
                'request_date_to': datetime.date(2024, 5, 31)
            })
            leave.action_validate()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 5, 1)

    @users('test_user')
    def test_accrual_plan_with_changing_working_schedules_3(self):
        """
        Accrual period 1 year, accrual value = 10 days
        Employee worked from january to june in full time, then from july to december in half time.
        Unpaid period in september, october, november.

        Value should be computed like this :
        0,5 (accrual period) * 10 (accrual value) * 100% (working rate) = 5 days * (6/6) (based on worked time) = 5 days
        +0,5 (accrual period) * 10 (accrual value) * 50% (working rate) = 2,5 days * (3/6) (based on worked time) = 1,25 days

        Total number of days is 6.25
        """

        self.yearly_accrual_plan['is_based_on_worked_time'] = True

        self.leave_type['company_id'] = self.belgian_company.id
        self.leave_type_without_allocation['company_id'] = self.belgian_company.id

        with freeze_time("2024-01-01"):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_with_multiple_schedules.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': self.yearly_accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1),
            })
            allocation.action_approve()
            leave = self.env['hr.leave'].with_context(tracking_disable=True).create({
                'name': '3 months time off',
                'employee_id': self.employee_with_multiple_schedules.id,
                'holiday_status_id': self.leave_type_without_allocation.id,
                'request_date_from': datetime.date(2024, 9, 1),
                'request_date_to': datetime.date(2024, 11, 30)
            })
            leave.action_validate()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 6.25, 1)
