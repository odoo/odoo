# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.base.tests.common import HttpCase
from odoo.tests.common import tagged
from odoo.tests.common import users

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'carryover_expiring_leaves')
class TestExpiringLeaves(HttpCase, TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Test',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
        })

    @users('enguerran')
    def test_no_carried_over_leaves(self):
        """
        The accrual plan:
            - Accrue at the end of period.
            - Carryover date : 31/12 (end of the year).
            Milestones:
                Milestone 1:
                - Start immediately.
                - Accrue 10 days.
                - Accrue days on 01/01 (start of the year).
                - Unused accruals are lost (no leaves are carried over).

        Create an accrual allocation with this plan and allocate it to the logged-in user.
        The employee will be accrued 10 days. The employee will use some of them. The carryover policy is set
        to None, so no leaves will be carriedover. The remaining days of the allocation will expire.
        """
        number_of_accrued_days = 10
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan',
            'carryover_date': 'other',
            'carryover_day': 31,
            'carryover_month': 'dec',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': number_of_accrued_days,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost'
                })
            ],
        })

        logged_in_emp = self.env.user.employee_id
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'date_from': date(date.today().year, 1, 1),
            'allocation_type': 'accrual',
            'accrual_plan_id': accrual_plan.id,
            'holiday_status_id': self.leave_type.id,
            'employee_id': logged_in_emp.id,
            'number_of_days': 0,
        })

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env['hr.leave'].create({
            'employee_id': logged_in_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': target_date + relativedelta(month=12, day=1),
            'request_date_to': target_date + relativedelta(month=12, day=7)
        })

        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date)

        # Assert the date of expiration
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                    allocation._get_carryover_date(target_date).strftime('%m/%d/%Y'),
                    "The expiration date should match the carryover date")

        # Assert the number of expiring leaves
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_remaining'],
                         number_of_accrued_days - leave.number_of_days,
                         "All the remaining days of the allocation will expire")

    @users('enguerran')
    def test_carried_over_leaves_with_maximum(self):
        """
        The accrual plan:
            - Accrue at the end of period.
            - Carryover date : 31/12 (end of the year).
            Milestones:
                Milestone 1:
                - Start immediately.
                - Accrue 20 days.
                - Accrue days on 01/01 (start of the year).
                - Unused accruals are carried over with a maximum of 10.

        Create an accrual allocation with this plan and allocate it to the logged-in user.
        The employee will be accrued 20 days. The employee will use some of them. The carryover
        policy is set to carryover with a maximum of 10, so at max 10 leaves will be carriedover.
        The remaining days of the allocation will expire.
        """

        number_of_accrued_days = 20
        carryover_limit = 10
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan',
            'carryover_date': 'other',
            'carryover_day': 31,
            'carryover_month': 'dec',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': number_of_accrued_days,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': carryover_limit,
                })
            ],
        })

        logged_in_emp = self.env.user.employee_id
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'date_from': date(date.today().year, 1, 1),
            'allocation_type': 'accrual',
            'accrual_plan_id': accrual_plan.id,
            'holiday_status_id': self.leave_type.id,
            'employee_id': logged_in_emp.id,
            'number_of_days': 0,
        })

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env['hr.leave'].create({
            'employee_id': logged_in_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': target_date + relativedelta(month=12, day=1),
            'request_date_to': target_date + relativedelta(month=12, day=7)
        })
        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date)

        # Assert the date of expiration
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                    allocation._get_carryover_date(target_date).strftime('%m/%d/%Y'),
                    "The expiration date should match the carryover date")

        # Assert the number of expiring leaves
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_remaining'],
                         number_of_accrued_days - leave.number_of_days - carryover_limit,
                         "All the remaining days of the allocation will expire")

    @users('enguerran')
    def test_allocation_with_max_carryover_and_expiring_allocation(self):
        """
        The accrual plan:
            - Accrue at the end of period.
            - Carryover date : 31/12 (end of the year).
            Milestones:
                Milestone 1:
                - Start immediately.
                - Accrue 20 days.
                - Accrue days on 01/01 (start of the year).
                - Unused accruals are carried over with a maximum of 10.

        Create an accrual allocation with this plan:
        - Employee: logged-in user.
        - Start date: 01/01/2024
        - Carryover Policy: carryover with a maximum of 10

        On 01/01/2025 The employee will be accrued 20 days.
        The employee will take 5 leaves using this allocation.
        - The carryover policy is set to carryover with a maximum of 10, so at max 10 days will be carriedover.
        - 5 days will expire.

        Create a second accrual allocation:
        - The configuration is the same as the previous one except that carryover date is the start of the year
          and all unused accruals will be carriedover.
        - This allocation will expire on 31/12 next year. 20 days will expire when the allocation expires.
          Number of expiring leaves = number of not carriedover days from the first allocation +
                                    number of expiring leaves due to expiration of the second allocation
                                    = 5 + 20 = 25 days
        """

        number_of_accrued_days = 20
        carryover_limit = 10
        accrual_plan_1 = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan',
            'carryover_date': 'other',
            'carryover_day': 31,
            'carryover_month': 'dec',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': number_of_accrued_days,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': carryover_limit,
                })
            ],
        })

        accrual_plan_2 = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan With All Leaves Carried Over',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': number_of_accrued_days,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'all',
                })
            ],
        })

        logged_in_emp = self.env.user.employee_id
        with freeze_time("2024-1-1"):
            allocation_with_carryover = self.env['hr.leave.allocation'].sudo().create({
                'date_from': '2024-1-1',
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan_1.id,
                'holiday_status_id': self.leave_type.id,
                'employee_id': logged_in_emp.id,
                'number_of_days': 0,
            })
            leave = self.env['hr.leave'].create({
                'employee_id': logged_in_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2025-12-1',
                'request_date_to': '2025-12-5'
            })
            # The expiring allocation
            self.env['hr.leave.allocation'].sudo().create({
                'date_from': '2024-1-1',
                'date_to': '2025-12-31',
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan_2.id,
                'holiday_status_id': self.leave_type.id,
                'employee_id': logged_in_emp.id,
                'number_of_days': 0,
            })

        target_date = date(2025, 12, 30)
        allocation_data = self.leave_type.get_allocation_data(logged_in_emp, target_date)

        # Assert the date of expiration
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                    allocation_with_carryover._get_carryover_date(target_date).strftime('%m/%d/%Y'),
                    "The expiration date should match the carryover date")

        # Assert the number of expiring leaves
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_remaining'],
                         (number_of_accrued_days - leave.number_of_days - carryover_limit) + number_of_accrued_days,
                         "All the remaining days of the allocation will expire")

    @users('enguerran')
    def test_expiring_allocation_without_carried_over_leaves(self):
        """
        The accrual plan:
            - Accrue at the end of period.
            - Carryover date : 31/12 (end of the year).
            Milestones:
                Milestone 1:
                - Start immediately.
                - Accrue 20 days.
                - Accrue days on 01/01 (start of the year).
                - Unused accruals are lost (no leaves are carried over).

        Create an accrual allocation with this plan and allocate it to the logged-in user. This
        allocation will expire on 31/12 next year.
        The employee will be accrued 10 days. The carryover policy is set to None, so no leaves
        will be carriedover. The remaining days of the allocation will expire.

        The number of expiring leaves should be 10 and not 20 (10 for the expiration of the allocation
        and 10 for the leaves being not carried over).
        """

        number_of_accrued_days = 10
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan',
            'carryover_date': 'other',
            'carryover_day': 31,
            'carryover_month': 'dec',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': number_of_accrued_days,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
                })
            ],
        })

        logged_in_emp = self.env.user.employee_id
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'date_from': date(date.today().year, 1, 1),
            'date_to': date(date.today().year + 1, 12, 31),
            'allocation_type': 'accrual',
            'accrual_plan_id': accrual_plan.id,
            'holiday_status_id': self.leave_type.id,
            'employee_id': logged_in_emp.id,
            'number_of_days': 0,
        })

        target_date = date(date.today().year + 1, 12, 30)
        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date)

        # Assert the date of expiration
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                    allocation._get_carryover_date(target_date).strftime('%m/%d/%Y'),
                    "The expiration date should match the carryover date")

        # Assert the number of expiring leaves
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_remaining'],
                         number_of_accrued_days,
                         "All the remaining days of the allocation will expire")

    @users('enguerran')
    def test_expiration_date(self):
        """
        The accrual plan:
            - Accrue at the end of period.
            - Carryover date : 01/01.
            Milestones:
                Milestone 1:
                - Start immediately.
                - Accrue 10 days.
                - Accrue days on 01/01 (start of the year).
                - Unused accruals are carried over with a maximum of 5.

        Create an accrual allocation with this plan and allocate it to the logged-in user.
        The employee will be accrued 10 days. The carryover policy is set to carryover with
        a maximum of 5, so only 5 leaves will be carriedover. The remaining days of the allocation
        will expire.

        If the target date is 01/01/2025, then the expiration date should be 01/01/2026 because 5 of the days
        accrued on 01/01/2025 will expire on 01/01/2026.
        """
        with freeze_time('2024-1-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
                'name': 'Test Accrual Plan',
                'carryover_date': 'year_start',
                'level_ids': [
                    (0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 10,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'yearly_day': 1,
                    'yearly_month': 'jan',
                    'cap_accrued_time': False,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 5,
                    })
                ],
            })

            logged_in_emp = self.env.user.employee_id
            allocation = self.env['hr.leave.allocation'].sudo().create({
                'date_from': date(2024, 1, 1),
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'holiday_status_id': self.leave_type.id,
                'employee_id': logged_in_emp.id,
                'number_of_days': 0,
            })

            target_date = date(2025, 1, 1)
            allocation_data = self.leave_type.get_allocation_data(allocation.employee_id, target_date)
            # Assert the date of expiration
            self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                        (target_date + relativedelta(years=1)).strftime('%m/%d/%Y'),
                        "The expiration date should be the carryover date of the year that follows the target date's year")

            # Assert the number of expiring leaves
            self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_remaining'], 5)

    @users('enguerran')
    def test_expiration_date_2(self):
        """
        - Define an accrual plan:
            - Carryover date : 1st of September.
            - Carryover with a maximum of 5 days.
        - Define 2 allocations:
            - Both allocations will start on 01/01/2023.
            - Both allocations use the accrual plan defined above.
            - Both allocations accrue 3 days yearly.
            - The first allocation expires on the 1st of October.
            - The second allocation doesn't expire.

        - On 01/01/2024, both allocations will accrue 3 days for the employee.
        - The expiration date should be 01/10/2024 because on 01/09/2024, 3 days will carryover for both allocations
          and no days will expire.
        """

        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).sudo().create({
            'name': 'Test Accrual Plan',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'sep',
            'level_ids': [
                (0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': 3,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'yearly_day': 1,
                'yearly_month': 'jan',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 5,
                })
            ],
        })

        logged_in_emp = self.env.user.employee_id
        with freeze_time("2023-1-1"):
            # Allocation 1
            self.env['hr.leave.allocation'].sudo().create({
                'date_from': '2023-1-1',
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'holiday_status_id': self.leave_type.id,
                'employee_id': logged_in_emp.id,
                'number_of_days': 0,
            })
            # Allocation 2
            self.env['hr.leave.allocation'].sudo().create({
                'date_from': '2023-1-1',
                'date_to': '2024-10-1',
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'holiday_status_id': self.leave_type.id,
                'employee_id': logged_in_emp.id,
                'number_of_days': 0,
            })

        with freeze_time("2024-1-1"):
            self.env['hr.leave.allocation'].sudo()._update_accrual()

        target_date = date(2024, 1, 1)
        allocation_data = self.leave_type.get_allocation_data(logged_in_emp, target_date)
        # Assert the date of expiration
        self.assertEqual(allocation_data[logged_in_emp][0][1]['closest_allocation_expire'],
                    (target_date + relativedelta(month=10)).strftime('%m/%d/%Y'),
                    "The expiration date should be the expiration date of the second allocation because no days will expire on carryover date")
