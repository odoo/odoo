import datetime
from freezegun import freeze_time
from datetime import date
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'accruals')
class TestAccrualAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAccrualAllocations, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'hr',
        })
        cls.leave_type_hour = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'hr',
            'request_unit': 'hour',
        })

    def setAllocationCreateDate(self, allocation_id, date):
        """ This method is a hack in order to be able to define/redefine the create_date
            of the allocations.
            This is done in SQL because ORM does not allow to write onto the create_date field.
        """
        self.env.cr.execute("""
                       UPDATE
                       hr_leave_allocation
                       SET create_date = '%s'
                       WHERE id = %s
                       """ % (date, allocation_id))

    def assert_allocation_and_balance(self, allocation, expected_allocation_value, expected_balance_value, msg):
        unit = allocation.accrual_plan_id.added_value_type
        allocation_value = allocation.number_of_hours_display if unit == 'hour' else allocation.number_of_days

        leave_type_data = allocation.holiday_status_id.get_allocation_data(self.employee_emp)
        remaining_leaves = leave_type_data[self.employee_emp][0][1]['remaining_leaves']

        self.assertAlmostEqual(allocation_value, expected_allocation_value, places=1, msg=msg)
        self.assertAlmostEqual(remaining_leaves, expected_balance_value, places=1, msg=msg)

    def test_consistency_between_cap_accrued_time_and_maximum_leave(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'hourly',
                'cap_accrued_time': True,
                'maximum_leave': 10000
            })],
        })
        level = accrual_plan.level_ids
        level.maximum_leave = 10
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 10)

        with self.assertRaises(UserError):
            level.maximum_leave = 0

        level.cap_accrued_time = False
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 0)

    def test_accrual_unlink(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
        })

        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
        })

        with self.assertRaises(ValidationError):
            accrual_plan.unlink()

        allocation.unlink()
        accrual_plan.unlink()

    def test_frequency_hourly_calendar(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'hourly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(allocation.number_of_days, 8, 'There should be 8 day allocated.')
                self.assertEqual(allocation.nextcall, nextcall, 'The next call date of the cron should be in 2 days.')
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 8, 'There should be only 8 day allocated.')

    def test_frequency_hourly_worked_hours(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'is_based_on_worked_time': True,
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'hourly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            leave_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': 'no',
                'responsible_ids': [(4, self.user_hrmanager_id)],
                'time_type': 'leave',
                'request_unit': 'half_day',
            })
            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2017-12-06 08:00:00',
                'request_date_to': '2017-12-06 17:00:00',
                'request_unit_half': True,
                'request_date_from_period': 'am',
            })
            leave.action_validate()

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(allocation.number_of_days, 4, 'There should be 4 day allocated.')
                self.assertEqual(allocation.nextcall, nextcall, 'The next call date of the cron should be in 2 days.')
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 4, 'There should be only 4 day allocated.')

    def test_frequency_daily(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(allocation.number_of_days, 1, 'There should be 1 day allocated.')
                self.assertEqual(allocation.nextcall, nextcall, 'The next call date of the cron should be in 2 days.')
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 1, 'There should be only 1 day allocated.')

    def test_frequency_weekly(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2021-09-03',
            })
            with freeze_time(datetime.date.today() + relativedelta(days=2)):
                allocation.action_validate()
                self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
                self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
                allocation._update_accrual()
                nextWeek = allocation.date_from + relativedelta(days=1, weekday=0)
                self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(nextWeek):
                allocation._update_accrual()
                nextWeek = datetime.date.today() + relativedelta(days=1, weekday=0)
                # Prorated
                self.assertAlmostEqual(allocation.number_of_days, 0.2857, 4, 'There should be 0.2857 day allocated.')
                self.assertEqual(allocation.nextcall, nextWeek, 'The next call date of the cron should be in 2 weeks')

            with freeze_time(nextWeek):
                allocation._update_accrual()
                nextWeek = datetime.date.today() + relativedelta(days=1, weekday=0)
                self.assertAlmostEqual(allocation.number_of_days, 1.2857, 4, 'There should be 1.2857 day allocated.')
                self.assertEqual(allocation.nextcall, nextWeek, 'The next call date of the cron should be in 2 weeks')

    def test_frequency_bimonthly(self):
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'bimonthly',
                    'first_day': 1,
                    'second_day': 15,
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2021-09-03',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            next_date = datetime.date(2021, 9, 15)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

        with freeze_time(next_date):
            next_date = datetime.date(2021, 10, 1)
            allocation._update_accrual()
            # Prorated
            self.assertAlmostEqual(allocation.number_of_days, 0.7857, 4, 'There should be 0.7857 day allocated.')
            self.assertEqual(allocation.nextcall, next_date, 'The next call date of the cron should be October 1st')

        with freeze_time(next_date):
            allocation._update_accrual()
            # Not Prorated
            self.assertAlmostEqual(allocation.number_of_days, 1.7857, 4, 'There should be 1.7857 day allocated.')

    def test_frequency_monthly(self):
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2021-08-31',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            next_date = datetime.date(2021, 10, 1)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

        with freeze_time(next_date):
            next_date = datetime.date(2021, 11, 1)
            allocation._update_accrual()
            # Prorata = 1 since a whole month passed
            self.assertEqual(allocation.number_of_days, 1, 'There should be 1 day allocated.')
            self.assertEqual(allocation.nextcall, next_date, 'The next call date of the cron should be November 1st')

    def test_frequency_biyearly(self):
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'biyearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                })],
            })
            # this sets up an accrual on the 1st of January and the 1st of July
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            next_date = datetime.date(2022, 1, 1)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

        with freeze_time(next_date):
            next_date = datetime.date(2022, 7, 1)
            allocation._update_accrual()
            # Prorated
            self.assertAlmostEqual(allocation.number_of_days, 0.6576, 4, 'There should be 0.6576 day allocated.')
            self.assertEqual(allocation.nextcall, next_date, 'The next call date of the cron should be July 1st')

        with freeze_time(next_date):
            allocation._update_accrual()
            # Not Prorated
            self.assertAlmostEqual(allocation.number_of_days, 1.6576, 4, 'There should be 1.6576 day allocated.')

    def test_frequency_yearly(self):
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                })],
            })
            # this sets up an accrual on the 1st of January
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            next_date = datetime.date(2022, 1, 1)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

        with freeze_time(next_date):
            next_date = datetime.date(2023, 1, 1)
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_days, 0.3315, 4, 'There should be 0.3315 day allocated.')
            self.assertEqual(allocation.nextcall, next_date, 'The next call date of the cron should be January 1st 2023')

        with freeze_time(next_date):
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_days, 1.3315, 4, 'There should be 1.3315 day allocated.')

    def test_check_gain(self):
        # 2 accruals, one based on worked time, one not
        # check gain
        with freeze_time('2021-08-30'):
            attendances = []
            for index in range(5):
                attendances.append((0, 0, {
                    'name': '%s_%d' % ('40 Hours', index),
                    'hour_from': 8,
                    'hour_to': 12,
                    'dayofweek': str(index),
                    'day_period': 'morning'
                }))
                attendances.append((0, 0, {
                    'name': '%s_%d' % ('40 Hours', index),
                    'hour_from': 12,
                    'hour_to': 13,
                    'dayofweek': str(index),
                    'day_period': 'lunch'
                }))
                attendances.append((0, 0, {
                    'name': '%s_%d' % ('40 Hours', index),
                    'hour_from': 13,
                    'hour_to': 17,
                    'dayofweek': str(index),
                    'day_period': 'afternoon'
                }))
            calendar_emp = self.env['resource.calendar'].create({
                'name': '40 Hours',
                'tz': self.employee_emp.tz,
                'attendance_ids': attendances,
            })
            self.employee_emp.resource_calendar_id = calendar_emp.id

            accrual_plan_not_based_on_worked_time = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 5,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                })],
            })
            accrual_plan_based_on_worked_time = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'is_based_on_worked_time': True,
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 5,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 10000,
                })],
            })
            allocation_not_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan_not_based_on_worked_time.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'state': 'confirm',
            })
            allocation_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan_based_on_worked_time.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'state': 'confirm',
            })
            (allocation_not_worked_time | allocation_worked_time).action_validate()
            self.setAllocationCreateDate(allocation_not_worked_time.id, '2021-08-01 00:00:00')
            self.setAllocationCreateDate(allocation_worked_time.id, '2021-08-01 00:00:00')
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': 'no',
                'responsible_ids': [Command.link(self.user_hrmanager_id)],
                'time_type': 'leave',
            })
            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2021-09-02',
                'request_date_to': '2021-09-02',
            })
            leave.action_validate()
            self.assertFalse(allocation_not_worked_time.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertFalse(allocation_worked_time.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation_not_worked_time.number_of_days, 0, 'There should be no days allocated yet.')
            self.assertEqual(allocation_worked_time.number_of_days, 0, 'There should be no days allocated yet.')

        next_date = datetime.date(2021, 9, 6)
        with freeze_time(next_date):
            # next_date = datetime.date(2021, 9, 13)
            self.env['hr.leave.allocation']._update_accrual()
            # Prorated
            self.assertAlmostEqual(allocation_not_worked_time.number_of_days, 4.2857, 4, 'There should be 4.2857 days allocated.')
            # 3.75 -> starts 1 day after allocation date -> 31/08-3/09 => 4 days - 1 days time off => (3 / 4) * 5 days
            # ^ result without prorata
            # Prorated
            self.assertAlmostEqual(allocation_worked_time.number_of_days, 3, 4, 'There should be 3 days allocated.')
            self.assertEqual(allocation_not_worked_time.nextcall, datetime.date(2021, 9, 13), 'The next call date of the cron should be the September 13th')
            self.assertEqual(allocation_worked_time.nextcall, datetime.date(2021, 9, 13), 'The next call date of the cron should be the September 13th')

        with freeze_time(next_date + relativedelta(days=7)):
            next_date = datetime.date(2021, 9, 20)
            self.env['hr.leave.allocation']._update_accrual()
            self.assertAlmostEqual(allocation_not_worked_time.number_of_days, 9.2857, 4, 'There should be 9.2857 days allocated.')
            self.assertEqual(allocation_not_worked_time.nextcall, next_date, 'The next call date of the cron should be September 20th')
            self.assertAlmostEqual(allocation_worked_time.number_of_days, 8, 4, 'There should be 8 days allocated.')
            self.assertEqual(allocation_worked_time.nextcall, next_date, 'The next call date of the cron should be September 20th')

    def test_check_max_value(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 1,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 1, 'There should be only 1 day allocated.')

            with freeze_time(nextcall):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                # The maximum value is 1 so this shouldn't change anything
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 1, 'There should be only 1 day allocated.')

    def test_check_max_value_hours(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'hour',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 4,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=10)
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 0.125, 'There should be only 0.125 days allocated.')

            with freeze_time(nextcall):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                # The maximum value is 1 so this shouldn't change anything
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 0.5, 'There should be only 0.5 days allocated.')

    def test_accrual_hours_with_max_carryover(self):
        with freeze_time("2024-10-10"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual plan - hours and max postpone',
                'level_ids': [(0, 0, {
                    'added_value_type': 'hour',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'first_day': 31,
                    'frequency': 'monthly',
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 4,  # confusing name but is in hours when added_value_type == 'hour'
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'date_from': datetime.date(2025, 1, 1),
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0)

            hours_per_day = self.employee_emp.resource_calendar_id.hours_per_day
            allocation_data = self.leave_type.get_allocation_data(self.employee_emp, "2025-12-02")[self.employee_emp][0][1]
            self.assertAlmostEqual(allocation_data["remaining_leaves"], 11 / hours_per_day, 1, '11 hours accrued.')

            allocation_data = self.leave_type.get_allocation_data(self.employee_emp, "2026-02-02")[self.employee_emp][0][1]
            self.assertAlmostEqual(allocation_data["remaining_leaves"], 5 / hours_per_day, 1, '5 hours accrued.')

    def test_accrual_transition_immediately(self):
        with freeze_time("2017-12-5"):
            # 1 accrual with 2 levels and level transition immediately
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'transition_mode': 'immediately',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 1,
                }), (0, 0, {
                    'start_count': 10,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 1,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env['hr.leave.accrual.level'].search([('accrual_plan_id', '=', accrual_plan.id), ('start_count', '=', 10)])
            self.assertEqual(allocation._get_current_accrual_plan_level_id(next_date)[0], second_level, 'The second level should be selected')

    def test_accrual_transition_after_period(self):
        with freeze_time("2017-12-5"):
            # 1 accrual with 2 levels and level transition after
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'transition_mode': 'end_of_accrual',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 1,
                }), (0, 0, {
                    'start_count': 10,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'cap_accrued_time': True,
                    'maximum_leave': 1,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env['hr.leave.accrual.level'].search([('accrual_plan_id', '=', accrual_plan.id), ('start_count', '=', 10)])
            self.assertEqual(allocation._get_current_accrual_plan_level_id(next_date)[0], second_level, 'The second level should be selected')

    def test_unused_accrual_lost(self):
        """
        Create an accrual plan:
            - Carryover date:  January 1st.
        Create a milestone:
            - Number of accrued days: 1
            - Frequency: daily
            - Start accrual 1 day after the allocation start date.
            - Carryover policy: No days carry over.
            - Accrued days cap: 20 days.
        Create an allocation:
            - Start date: 15/12/2021
            - Type: Accrual
            - Accrual Plan: Use the one defined above.
            - Number of days (given to the employee on the first run of the accrual plan): 10 days

        The employee is given 10 days on the first run of the accrual plan.
        From 15/12/2021, to 31/12/2021 10 days are accrued to the employee (It should be 16 but the accrued days cap is 20 days).
        On 01/01/2022
            - No days will carry over from the 25 days that the employee has.
            - 1 day is accrued.
            - The total number of days that the employee has is 1 day.
        """
        with freeze_time('2021-12-15'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 20,
                    'action_with_unused_accruals': 'lost',
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 10,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 1,
                             'The number of days should reset and 1 day will be accrued on 01/01/2022.')

    def test_unused_accrual_postponed(self):
        # 1 accrual with 2 levels and level transition after
        # This also tests retroactivity
        with freeze_time('2021-12-15'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 25,
                    'action_with_unused_accruals': 'all',
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 10,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 25, 'The maximum number of days should be reached and kept.')

    def test_unused_accrual_postponed_2(self):
        with freeze_time('2021-01-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 2,
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 10,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time('2023-01-26'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4, 'The maximum number of days should be reached and kept.')

    def test_unused_accrual_postponed_limit(self):
        """
        Create an accrual plan:
            - Carryover date:  January 1st.
            - The days are accrued at the start of the accrual period.
        Create a milestone:
            - Number of accrued days: 1
            - Frequency: daily
            - Start accrual 1 day after the allocation start date.
            - Carryover policy: Carryover with a maximum
            - Carryover limit: 15 days
            - Accrued days cap: 25 days.
        Create an allocation:
            - Start date: 15/12/2021
            - Type: Accrual
            - Accrual Plan: Use the one defined above.
            - Number of days (given to the employee on the first run of the accrual plan): 10 days

        The employee is given 10 days on the first run of the accrual plan.
        From 15/12/2021, to 31/12/2021 15 days are accrued to the employee (It should be 16 but the accrued days cap is 25 days).
        On 01/01/2022
            - Only 15 days carry over from the 25 days that the employee has.
            - 1 Additional day is accrued.
            - The total number of days that the employee has is 16 days.
        """
        # 1 accrual with 2 levels and level transition after
        # This also tests retroactivity
        with freeze_time('2021-12-15'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'accrued_gain_time': 'start',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'cap_accrued_time': True,
                    'maximum_leave': 25,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 15,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 10,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 16,
                          '15 days carryover. 1 day is accrued for the new accrual period. The total is 16 days.')

    def test_unused_accrual_postponed_limit_2(self):
        """
        Create an accrual plan:
            - Carryover date:  January 1st.
        Create a milestone:
            - Number of accrued days: 15
            - Frequency: Yearly
            - Accrual date: January 1st
            - Carryover policy: Carryover with a maximum
            - Carryover limit: 7 days
        Create an allocation:
            - Start date: 01/01/2021
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        On 01/01/2022, 15 days are accrued to the employee.
        On 01/01/2023:
            - Only 7 days carry over from the 15 days that the employee has.
            - 15 Additional days are accrued.
            - The total number of days that the employee has is 22 days.
        """
        with freeze_time('2021-01-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 15,
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 7,
                })],
            })
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time('2023-01-26'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 22,
                         '7 days carryover from the previous accrual period. 15 days are accrued for the new accrual period. The total is 22 days.')

    def test_accrual_skipped_period(self):
        # Test that when an allocation is made in the past and the second level is technically reached
        #  that the first level is not skipped completely.
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 15,
                'frequency': 'biyearly',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'action_with_unused_accruals': 'all',
            }), (0, 0, {
                'start_count': 4,
                'start_type': 'month',
                'added_value': 10,
                'frequency': 'biyearly',
                'cap_accrued_time': True,
                'maximum_leave': 500,
                'action_with_unused_accruals': 'all',
            })],
        })
        with freeze_time('2020-8-16'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': datetime.date(2020, 8, 16),
            })
            allocation.action_validate()
        with freeze_time('2022-1-10'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 30.82, 2, "Invalid number of days")

    def test_three_levels_accrual(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 2,
                'start_type': 'month',
                'added_value': 3,
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 3,
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            }), (0, 0, {
                'start_count': 3,
                'start_type': 'month',
                'added_value': 6,
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 6,
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            }), (0, 0, {
                'start_count': 4,
                'start_type': 'month',
                'added_value': 1,
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            })],
        })
        with freeze_time('2022-1-31'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': datetime.date(2022, 1, 31),
            })
            allocation.action_validate()
        with freeze_time('2022-7-20'):
            allocation._update_accrual()
        # The first level gives 3 days
        # The second level could give 6 days but since the first level was already giving
        # 3 days, the second level gives 3 days to reach the second level's limit.
        # The third level gives 1 day since it only counts for one iteration.
        self.assertAlmostEqual(allocation.number_of_days, 7, 2)

    def test_accrual_lost_previous_days(self):
        """
        Test that when an allocation with two levels is made and that the first level has it's action
        with unused accruals set as lost that the days are effectively lost
        Create an accrual plan:
            - Carryover date:  January 1st.
        Create first milestone:
            - Number of accrued days: 1
            - Frequency: monthly
            - Start accrual 0 day after the allocation start date.
            - Carryover policy: No days carry over
            - Accrued days cap: 12 days.
        Create second milestone:
            - Same as the first milestone but it starts after 1 year of the allocation start date
        Create an allocation:
            - Start date: 01/01/2021
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        From 01/01/2021, to 01/12/2021 11 days are accrued to the employee.

        On 01/01/2022:
            - No days carry over.
            - 1 day is accrued (for the period from 01/12/2021 to 31/12/2021).

        From 01/01/2022, to 01/04/2022 3 days are accrued to the employee.
        The total number of days that the employee has is 1 + 3 = 4 days.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'cap_accrued_time': True,
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                }),
                (0, 0, {
                    'start_count': 1,
                    'start_type': 'year',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'cap_accrued_time': True,
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                }),
            ],
        })
        with freeze_time('2021-1-1'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': datetime.date(2021, 1, 1),
            })
            allocation.action_validate()
        with freeze_time('2022-4-4'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4, "Invalid number of days")

    def test_accrual_lost_first_january(self):
        """
        Create an accrual plan:
            - Carryover date:  January 1st.
            - The days are accrued at the start of the accrual period.
        Create a milestone:
            - Number of accrued days: 3
            - Frequency: yearly
            - Start accrual immediately on the allocation start date.
            - Carryover policy: No days carry over
            - Accrued days cap: 12 days.
        Create an allocation:
            - Start date: 01/01/2019
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        On 01/01/2019, 3 days are accrued.
        On 01/01/2020, the previous 3 days are lost due to carryover. 3 days are accrued.
        On 01/01/2021, the previous 3 days are lost due to carryover. 3 days are accrued.
        On 01/01/2022, the previous 3 days are lost due to carryover. 3 days are accrued.
        The total number of days should be 3.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 3,
                    'frequency': 'yearly',
                    'cap_accrued_time': True,
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                })
            ],
        })
        with freeze_time('2019-1-1'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': datetime.date(2019, 1, 1),
            })
            allocation.action_validate()

        with freeze_time('2022-4-1'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 3, 2, "Invalid number of days")

    def test_accrual_maximum_leaves(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 5,
            })],
        })
        with freeze_time("2021-9-3"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2021-09-03',
            })

        with freeze_time("2021-10-3"):
            allocation.action_validate()
            allocation._update_accrual()

            self.assertEqual(allocation.number_of_days, 5, "Should accrue maximum 5 days")

    def test_accrual_maximum_leaves_no_limit(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': False,
            })],
        })
        with freeze_time("2021-9-3"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2021-09-03',
            })

        with freeze_time("2021-10-3"):
            allocation.action_validate()
            allocation._update_accrual()

            self.assertEqual(allocation.number_of_days, 29, "No limits for accrued days")

    def test_accrual_leaves_taken_maximum(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'week_day': 'mon',
                'cap_accrued_time': True,
                'maximum_leave': 5,
            })],
        })
        with freeze_time("2022-1-1"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2022-01-01',
            })
            allocation.action_validate()

        with freeze_time("2022-3-2"):
            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 5, "Maximum of 5 days accrued")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2022-03-07',
            'request_date_to': '2022-03-11',
        })
        leave.action_validate()

        with freeze_time("2022-6-1"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "Should accrue 5 additional days")

    def test_accrual_leaves_taken_maximum_hours(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'added_value_type': 'hour',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'week_day': 'mon',
                'cap_accrued_time': True,
                'maximum_leave': 10,
            })],
        })
        with freeze_time(datetime.date(2022, 1, 1)):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type_hour.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2022-01-01',
            })
            allocation.action_validate()

        with freeze_time(datetime.date(2022, 4, 1)):
            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 10 / self.hours_per_day, "Maximum of 10 hours accrued")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type_hour.id,
            'request_date_from': '2022-03-07',
            'request_date_to': '2022-03-07',
        })
        leave.action_validate()

        with freeze_time(datetime.date(2022, 6, 1)):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 18 / self.hours_per_day, "Should accrue 8 additional hours")

    @mute_logger('odoo.sql_db')
    def test_yearly_cap_constraint(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
                'week_day': 'mon',
                'cap_accrued_time': True,
                'maximum_leave': 5,
            })],
        })
        with self.assertRaises(IntegrityError):
            accrual_plan.level_ids[0].write({
                'cap_accrued_time_yearly': True,
                'maximum_leave_yearly': 0,
            })
        accrual_plan.level_ids[0].write({
            'cap_accrued_time_yearly': True,
            'maximum_leave_yearly': 1,
        })
        accrual_plan.level_ids[0].write({
            'cap_accrued_time_yearly': False,
            'maximum_leave_yearly': 0,
        })
        self.env.cr.precommit.run()
        self.env.flush_all()

    def test_yearly_cap(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Hour Time Off',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
        })
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'hour',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 0.06,
                'frequency': 'hourly',
                'week_day': 'mon',
                'cap_accrued_time': True,
                'maximum_leave': 180,
                'cap_accrued_time_yearly': True,
                'maximum_leave_yearly': 120,
            })],
        })

        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 0,
            })

        with freeze_time('2024-12-20'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 120, 120,
                "The yearly cap should be reached.")
            leave = self.env['hr.leave'].create({
                'name': "Leave for employee",
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_unit_hours': True,
                'request_date_from': datetime.date(2024, 12, 19),
                'request_date_to': datetime.date(2024, 12, 19),
                'request_hour_from': '10',
                'request_hour_to': '12',
            })
            self.assertEqual(leave.number_of_hours, 2)
            self.assert_allocation_and_balance(allocation, 120, 118,
                "The 2 hours should be deduced from the balance")

        with freeze_time('2024-12-31'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 120, 118,
                "The amount shouldn't exceed the yearly amount as all days days have already been accrued.")

        with freeze_time('2025-01-06'):
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_hours_display, 121.44)

        with freeze_time('2025-07-03'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 182, 180, "The global cap should be reached.")
            leave = self.env['hr.leave'].create({
                'name': "Leave for employee",
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': datetime.date(2025, 6, 2),
                'request_date_to': datetime.date(2025, 6, 11),
            })
            self.assertEqual(leave.number_of_hours, 64)
            self.assert_allocation_and_balance(allocation, 182, 116,
                "The leave hours should be deduced from the balance.")

        with freeze_time('2025-12-25'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 240, 174,
                "The total yearly amount should be reached.")

        with freeze_time('2025-12-31'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 240, 174,
                "Nothing more should have been accrued since the yearly cap was already reached.")

    def test_accrual_period_start(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'week_day': 'mon',
                'cap_accrued_time': True,
                'maximum_leave': 5,
            })],
        })
        with freeze_time("2023-4-24"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-24',
            })
            allocation.action_validate()

            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 0, "Should accrue 0 days, because the period is not done yet.")

        accrual_plan.accrued_gain_time = 'start'
        with freeze_time("2023-4-24"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-24',
            })
            allocation.action_validate()

            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 1, "Should accrue 1 day, at the start of the period.")

    def test_accrual_period_start_multiple_runs(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1.5,
                'frequency': 'monthly',
                'first_day': 13,
                'cap_accrued_time': True,
                'maximum_leave': 15,
            })],
        })
        with freeze_time("2023-4-13"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-13',
            })
            allocation.action_validate()
            allocation._update_accrual()

        self.assertAlmostEqual(allocation.number_of_days, 1.5, 2)

        with freeze_time("2023-9-13"):
            allocation._update_accrual()

        self.assertAlmostEqual(allocation.number_of_days, 9, 2)

    def test_accrual_period_start_level_transfer(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'week_day': 'wed',
                    'cap_accrued_time': True,
                    'maximum_leave': 10,
                }),
                (0, 0, {
                    'start_count': 3,
                    'start_type': 'month',
                    'added_value': 2,
                    'frequency': 'weekly',
                    'week_day': 'wed',
                    'cap_accrued_time': True,
                    'maximum_leave': 5,
                })
            ],
        })
        with freeze_time("2023-4-26"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-26',
            })
            allocation.action_validate()
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 1, "Should accrue 1 day, at the start of the period.")

        with freeze_time("2023-7-5"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "Should accrue 10 days, days received, but not over limit.")

        # first wednesday at the second level
        with freeze_time("2023-8-02"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 5, "Should accrue 5 days, after level transfer 10 are cut to 5")

    def test_accrual_carryover_at_allocation(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day': 27,
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })
        with freeze_time("2023-4-26"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-26',
            })
            allocation.action_validate()
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 0.03, 2, "Should accrue 0.03 days, accrued_gain_time == start.")

        with freeze_time("2023-4-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 1.03, 2, "Should accrue 1 day, days are added on 27th.")

        with freeze_time("2023-12-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 9.03, 2, "Should accrue 9 day, after 8 months.")

        with freeze_time("2024-04-26"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 0.0, 2, "Allocations not lost on 1st of January, but on allocation date.")

        with freeze_time("2024-04-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 1, "Allocations lost, then 1 accrued.")

    def test_accrual_carryover_at_other(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'carryover_date': 'other',
            'carryover_day': 20,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'monthly',
                'first_day': 11,
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 69,
            })],
        })
        with freeze_time("2023-04-20"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'date_from': '2023-04-20',
            })
            allocation.action_validate()

        with freeze_time("2024-04-20"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 69, "Carryover at other date, level's maximum leave is 69.")

    def test_accrual_carrover_other_period_end_multi_level(self):
        """
        Create an accrual plan:
            - Carryover date:  June 5th.
        Create first milestone:
            - Number of accrued days: 1
            - Frequency: monthly on the 9th day.
            - Start accrual 5 days after the allocation start date.
            - Carryover policy: Carryover with a maximum
            - Carryover limit: 13 days
            - Accrued days cap: 15 days.
        Create second milestone:
            - Number of accrued days: 2
            - Frequency: biyearly, on the 17th of February and on the 29th of October
            - Start accrual 9 months after the allocation start date.
            - Carryover policy: Carryover with a maximum
            - Carryover limit: 20 days
            - Accrued days cap: 10 days.
        Create third milestone:
            - Number of accrued days: 12
            - Frequency: yearly on the 15th of July
            - Start accrual 17 months after the allocation start date.
            - Carryover policy: No days carry over
            - Accrued days cap: 21 days.
        Create an allocation:
            - Start date: 04/04/2023
            - Type: Accrual
            - Accrual Plan: Use the one defined above.
            - Number of days (given to the employee on the first run of the accrual plan): 9 days

        Quick Overview:
        - On 05/06/2026 (carryover date): The allocation will be on the third milestone. All the accrued days will be lost due to the carryover policy.
        - On 15/07/2026, 12 days will be accrued.
        The the employee should have 12 days on 01/08/2026

        The detailed execution of the accrual plan is as follows:
        - The employee is given 9 days at the first run of the accrual plan.
        - From 09/04/2023, to 09/05/2023 1 day is accrued to the employee.
        - On 05/06/2023 (carryover date): The employee has 10 days < the carryover limit of 13 days. All days will carry over.
        - From 09/06/2023 to 09/12/2023: 5 days are accrued to the employee (should be 7 days but the accrued days cap is 15 days).
        - On 04/01/2024:
            * 0.7 days are accrued for the period from 09/12/2023 to 04/01/2024.
            * Total number of days will remain 15 days given that the employee has reached the accrued days cap.
            * The accrual plan transitions to the second milestone.

        - On 17/02/2024, No days will be accrued to the employee because he has 15 days and the accrued days cap is 10 days. Instead 5 days will be lost.
        - On 05/06/2024 (carryover date): The employee has 10 days < the carryover limit of 20 days. All days will carry over.
        - On 04/09/2024
            * No days will be accrued for the period from 17/02/2024 to 04/09/2024 due to accrued days cap.
            * Total number of days will remain 10 days.
            * The accrual plan transitions to the third milestone.

        - On 05/06/2025 (carryover date): All the accrued days will be lost.
        - On 15/07/2025, around 10 days will be accrued.
        - On 05/06/2026 (carryover date): All the accrued days will be lost.
        - On 15/07/2026, 12 days will be accrued.
        The the employee should have 12 days on 01/08/2026
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'end',
            'carryover_date': 'other',
            'carryover_day': 5,
            'carryover_month': 'jun',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'start_count': 5,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'first_day': 9,
                    'cap_accrued_time': True,
                    'maximum_leave': 15,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 13,
                }),
                (0, 0, {
                    'start_count': 9,
                    'start_type': 'month',
                    'added_value': 2,
                    'frequency': 'biyearly',
                    'first_month_day': 17,
                    'first_month': 'feb',
                    'second_month_day': 29,
                    'second_month': 'oct',
                    'cap_accrued_time': True,
                    'maximum_leave': 10,
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 20,
                }),
                (0, 0, {
                    'start_count': 17,
                    'start_type': 'month',
                    'added_value': 12,
                    'frequency': 'yearly',
                    'yearly_month': 'jul',
                    'yearly_day': 15,
                    'cap_accrued_time': True,
                    'maximum_leave': 21,
                    'action_with_unused_accruals': 'lost',
                }),
            ],
        })
        with freeze_time("2023-04-04"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 9,
                'allocation_type': 'accrual',
                'date_from': '2023-04-4',
            })
            allocation.action_validate()

        with freeze_time("2026-08-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 12)

    def test_accrual_creation_on_anterior_date(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Weekly accrual',
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })
        with freeze_time('2023-09-01'):
            accrual_allocation = self.env['hr.leave.allocation'].new({
                'name': 'Employee allocation',
                'holiday_status_id': self.leave_type.id,
                'date_from': '2023-01-01',
                'employee_id': self.employee_emp.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
            })
            # As the duration is set to a onchange, we need to force that onchange to run
            accrual_allocation._onchange_date_from()
            accrual_allocation.action_validate()
            # The amount of days should be computed as if it was accrued since
            # the start date of the allocation.
            self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)
            self.assertFalse(accrual_allocation.lastcall == accrual_allocation.date_from)
            accrual_allocation._update_accrual()
            # The amount being already computed, the amount should stay the same after the cron
            # running on the same day.
            self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)

    def test_future_accural_time(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'request_unit': 'hour',
        })
        with freeze_time("2023-12-31"):
            accrual_plan = self.env['hr.leave.accrual.plan'].create({
                'name': 'Accrual Plan For Test',
                'is_based_on_worked_time': False,
                'accrued_gain_time': 'end',
                'carryover_date': 'year_start',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'hour',
                    'frequency': 'monthly',
                    'cap_accrued_time': True,
                    'maximum_leave': 100,
                })],
            })
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': 0.125,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            allocation_data = leave_type.get_allocation_data(self.employee_emp, datetime.date(2024, 2, 1))
            self.assertEqual(allocation_data[self.employee_emp][0][1]['virtual_remaining_leaves'], 2)

    def test_added_type_during_onchange(self):
        """
            The purpose is to test whether the value of the `added_value_type`
            field is correctly propagated from the first level to the second
            during creation on the dialog form view.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 4,
                'added_value_type': 'hour',
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 100,
            })],
        })
        # Simulate the onchange of the dialog form view
        # Trigger the `_compute_added_value_type` method (with virtual records)
        res = self.env['hr.leave.accrual.level'].onchange({'accrual_plan_id': {'id': accrual_plan.id}}, [], {'added_value_type': {}})
        self.assertEqual(res['value']['added_value_type'], accrual_plan.level_ids[0].added_value_type)

    def test_accrual_immediate_cron_run(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Weekly accrual',
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })
        with freeze_time('2023-09-01'):
            accrual_allocation = self.env['hr.leave.allocation'].new({
                'name': 'Employee allocation',
                'holiday_status_id': self.leave_type.id,
                'date_from': '2023-08-01',
                'employee_id': self.employee_emp.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
            })
            # As the duration is set to a onchange, we need to force that onchange to run
            accrual_allocation._onchange_date_from()
            accrual_allocation.action_validate()
            # The amount of days should be computed as if it was accrued since
            # the start date of the allocation.
            self.assertEqual(accrual_allocation.number_of_days, 31.0, "The allocation should have given 31 days")
            accrual_allocation._update_accrual()
            self.assertEqual(accrual_allocation.number_of_days, 31.0,
                "the amount shouldn't have changed after running the cron")

    def test_accrual_creation_for_history(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day_display': 'last',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })
        with freeze_time('2024-03-02'):
            accrual_allocation = self.env['hr.leave.allocation'].new({
                'name': 'History allocation',
                'holiday_status_id': self.leave_type.id,
                'date_from': '2024-03-01',
                'employee_id': self.employee_emp.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
            })
            # As the duration is set to an onchange, we need to force that onchange to run
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 0, places=0)

            # Yearly Report lost
            accrual_allocation.write({'date_from': '2022-01-01'})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 2, places=0)

            # Update date_to
            accrual_allocation.write({'date_to': '2022-12-31'})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 12, places=0)

    def test_accrual_with_report_creation_for_history(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day_display': 'last',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 5
            })],
        })
        with freeze_time('2024-03-02'):
            accrual_allocation = self.env['hr.leave.allocation'].new({
                'name': 'History allocation',
                'holiday_status_id': self.leave_type.id,
                'date_from': '2024-03-01',
                'employee_id': self.employee_emp.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
            })
            # As the duration is set to an onchange, we need to force that onchange to run
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 0, places=0)

            # Yearly Report capped to 5 after 2022 and after 2023
            accrual_allocation.write({'date_from': '2022-01-01'})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 7, places=0)

            # Update date_to
            accrual_allocation.write({'date_to': '2022-12-31'})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 12, places=0)

    def test_accrual_period_start_past_start_date(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day_display': '1',
                'cap_accrued_time': False,
            })],
        })
        with freeze_time('2024-03-01'):
            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = '2024-01-01'
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            accrual_allocation = f.record
            accrual_allocation.action_validate()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 3.0, places=0)

        with freeze_time('2024-04-01'):
            accrual_allocation._update_accrual()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 4.0, places=0)

    def test_cancel_invalid_leaves_with_regular_and_accrual_allocations(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day_display': '1',
                'cap_accrued_time': False,
            })],
        })
        allocations = self.env['hr.leave.allocation'].create([
            {
                'name': 'Regular allocation',
                'allocation_type': 'regular',
                'date_from': '2024-05-01',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'number_of_days': 2,
            },
            {
                'name': 'Accrual allocation',
                'allocation_type': 'accrual',
                'date_from': '2024-05-01',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 3,
            }
        ])
        allocations.action_validate()
        leave = self.env['hr.leave'].create({
                'name': 'Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-05-13',
                'request_date_to': '2024-05-17',
            })
        leave.action_validate()
        with freeze_time('2024-05-06'):
            self.env['hr.leave']._cancel_invalid_leaves()
        self.assertEqual(leave.state, 'validate', "Leave must not be canceled")

    def test_accrual_leaves_cancel_cron(self):
        leave_type_no_negative = self.env['hr.leave.type'].create({
            'name': 'Test Accrual - No negative',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'allows_negative': False,
        })
        leave_type_negative = self.env['hr.leave.type'].create({
            'name': 'Test Accrual - Negative',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'allows_negative': True,
            'max_allowed_negative': 1,
        })
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day_display': 'last',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 5
            })],
        })

        with freeze_time("2024-01-01"):
            self.env['hr.leave.allocation'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_no_negative.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 1,
            }, {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_negative.id,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 1,
            }])

            excess_leave = self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_no_negative.id,
                'request_date_from': '2024-01-05',
                'request_date_to': '2024-01-05',
            }])
            allowed_negative_leave = self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_negative.id,
                'request_date_from': '2024-01-12',
                'request_date_to': '2024-01-12',
            }])

            # As accrual allocation don't take into account future leaves,
            # it should be possible to take both leaves.
            self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_no_negative.id,
                'request_date_from': '2024-01-04',
                'request_date_to': '2024-01-04',
            }, {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_negative.id,
                'request_date_from': '2024-01-11',
                'request_date_to': '2024-01-11',
            }])
            self.env.flush_all()

            self.env['hr.leave']._cancel_invalid_leaves()

            # Since both leave are outside an allocation validity,
            # they are detected as discrepancies. However, the
            # leave that is not exceeding the negative amount should be kept
            # as it is valid according to the configuration.
            self.assertEqual(excess_leave.state, 'cancel')
            self.assertEqual(allowed_negative_leave.state, 'validate')

            self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type_negative.id,
                'request_date_from': '2024-01-10',
                'request_date_to': '2024-01-10',
            }])

            self.env['hr.leave']._cancel_invalid_leaves()

            # The last added leave creates a discrepancy that exceeds the
            # maximum amount allowed in negative.
            self.assertEqual(allowed_negative_leave.state, 'cancel')

    def test_check_lastcall_change_regular_to_accrual(self):
        with freeze_time("2017-12-5"):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
            })
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 10,
                'allocation_type': 'regular',
            })
            allocation.action_validate()

            self.assertEqual(allocation.lastcall, False)

            allocation.action_refuse()
            allocation.write({
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
            })

            self.assertEqual(allocation.lastcall, datetime.date(2017, 12, 5))

    def test_accrual_allocation_data_persists(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
        })
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 10
            })],
        })

        def get_remaining_leaves(*args):
            return leave_type.get_allocation_data(self.employee_emp, datetime.date(*args))[self.employee_emp][0][1][
                'remaining_leaves']

        with freeze_time("2024-03-01"):
            # Simulate creating an allocation from frontend interface
            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.employee_id = self.employee_emp
                f.holiday_status_id = leave_type
                f.date_from = '2024-02-01'
                f.name = "Accrual allocation for employee"

            allocation = f.record
            allocation.action_validate()

            first_result = get_remaining_leaves(2024, 2, 21)
            self.assertEqual(get_remaining_leaves(2024, 2, 21), first_result, "Function return result should persist")

    def test_future_accural_time_with_leaves_taken_in_the_past(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
        })
        accrual_plan = self.env['hr.leave.accrual.plan'].create({
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 10
            })],
        })

        def get_remaining_leaves(*args):
            return leave_type.get_allocation_data(self.employee_emp, datetime.date(*args))[self.employee_emp][0][1][
                'remaining_leaves']

        with freeze_time("2024-03-01"):
            # Simulate creating an allocation from frontend interface
            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.employee_id = self.employee_emp
                f.holiday_status_id = leave_type
                f.date_from = '2024-02-01'
                f.name = "Accrual allocation for employee"

            allocation = f.record
            allocation.action_validate()
            self.assertEqual(get_remaining_leaves(2024, 3, 1), 10, "The cap is reached, no more leaves should be accrued")

            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2024-02-26',
                'request_date_to': '2024-03-01',
            })
            leave.action_validate()
            self.assertEqual(get_remaining_leaves(2024, 3, 1), 5, "5 day should be deduced from the allocation")
            self.assertEqual(get_remaining_leaves(2024, 3, 3), 7, "2 days should be added to the accrual allocation")
            self.assertEqual(get_remaining_leaves(2024, 3, 10), 10, "Accrual allocation should be capped at 10")

            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2024-03-04',
                'request_date_to': '2024-03-08',
            })
            leave.action_validate()
            self.assertEqual(get_remaining_leaves(2024, 3, 4), 3, "5 days should be deduced from the allocation and a new day should be accrued")
            self.assertEqual(get_remaining_leaves(2024, 3, 11), 10, "Accrual allocation should be capped at 10")

    @freeze_time('2024-01-01')
    def test_validate_leaves_with_more_days_than_allocation(self):
        allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 1,
            'allocation_type': 'regular',
        })

        allocation.action_validate()
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-01-09',
                'request_date_to': '2024-01-12',
            }])

        leave = self.env['hr.leave'].create([{
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-01-09 08:00:00',
                'request_date_to': '2024-01-09 17:00:00',
            }])

        leave.action_validate()
        leave.action_refuse()
        leave.action_reset_confirm()

        with self.assertRaises(ValidationError):
            leave.write({
                'request_date_from': '2024-01-09',
                'request_date_to': '2024-01-12',
            })

    def test_compute_allocation_days_after_adding_employee(self):
        """
        Test the addition of the employee after the date when creating an allocation
        will the number_of_days be computed or not. Also that the number_of_days
        gets recomputed when changing the employee
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Monthly accrual',
            'is_based_on_worked_time': True,
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids':
                [(0, 0, {
                    'added_value_type': 'day',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'first_day_display': '1',
                    'cap_accrued_time': False,
                    'action_with_unused_accruals': 'all',
                }),
             ],
        })

        with freeze_time('2024-08-19'):
            attendances = []
            for index in range(3):
                attendances.extend([
                    (0, 0, {
                        'name': '%s_%d' % ('20 Hours', index),
                        'hour_from': 8,
                        'hour_to': 10,
                        'dayofweek': str(index),
                        'day_period': 'morning'
                    }),
                    (0, 0, {
                        'name': '%s_%d' % ('20 Hours', index),
                        'hour_from': 10,
                        'hour_to': 11,
                        'dayofweek': str(index),
                        'day_period': 'lunch'
                    }),
                    (0, 0, {
                        'name': '%s_%d' % ('20 Hours', index),
                        'hour_from': 11,
                        'hour_to': 13,
                        'dayofweek': str(index),
                        'day_period': 'afternoon'
                    })
                ])
            calendar_emp = self.env['resource.calendar'].create({
                'name': '20 Hours',
                'tz': self.employee_hrmanager.tz,
                'attendance_ids': attendances,
            })
            self.employee_hrmanager.resource_calendar_id = calendar_emp.id

            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = '2024-08-07'
                f.holiday_status_id = self.leave_type
                f.employee_id = self.employee_emp
                f.name = "Employee Allocation"

            accrual_allocation = f.record
            allocation_days = accrual_allocation.number_of_days
            self.assertEqual(accrual_allocation.number_of_days, 7.0)

            with Form(accrual_allocation) as accForm:
                accForm.employee_id = self.employee_hrmanager

            updated_allocation = accForm.record

            self.assertNotEqual(updated_allocation.number_of_days, allocation_days)
            self.assertEqual(updated_allocation.number_of_days, 3.0)

    def test_no_days_accrued_on_carryover_date(self):
        """
        All time off days should be accrued on the specified date by the current milestone of the accrual
        plan. No days should be accrued on a carryover date.

        Create an accrual plan:
            - Carryover date: July 1st.
        Create a milestone:
            - Number of accrued days: 10
            - Frequency: Yearly
            - Start accrual immediately on the allocation start date.
            - Accrual date: January 1st
            - Carryover policy: All days carry over
        Create an allocation:
            - Start date: 01/01/2024
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        On 01/01/2025 (Accrual date), 10 days are accrued to the employee.
        On 01/07/2025 (Carryover date), no days should be accrued.
        On 01/01/2026 (Accrual date), 10 days are accrued to the employee. Total accrued days = 20 days.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'carryover_date': 'other',
                'carryover_day': 1,
                'carryover_month': 'jul',
                'level_ids': [(0, 0, {
                    'added_value': 10,
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'frequency': 'yearly',
                })],
        })
        with freeze_time('2024-1-01'):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1)
            })
            allocation.action_validate()

        with freeze_time('2025-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "10 days should be accrued")

        with freeze_time('2025-7-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "No Days should be accrued on the carryover date")

        with freeze_time('2026-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 20,
                         "10 additional days should be accrued on January 1st. The total number of accrued days should be 20")

    def test_matching_accrual_and_carryover_dates(self):
        """
        When the accrual date and carry over date are the same, the carry over policy should be applied
        first, then the time off days should be accrued to the employee

        Create an accrual plan:
            - Carryover date: January 1st.
        Create a milestone:
            - Number of accrued days: 10
            - Frequency: Yearly
            - Start accrual immediately on the allocation start date.
            - Accrual date: January 1st
            - Carryover policy: No days carry over
        Create an allocation:
            - Start date: 01/01/2024
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        On 01/01/2025 (Accrual date), 10 days are accrued to the employee.
        On 01/01/2026 (Accrual date and carryover date):
            * The previous 10 days are lost.
            * 10 days are accrued to the employee.
            * Total employee should have 10 days.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'carryover_date': 'year_start',
                'level_ids': [(0, 0, {
                    'added_value': 10,
                    'added_value_type': 'day',
                    'start_count': 0,
                    'start_type': 'day',
                    'frequency': 'yearly',
                    'action_with_unused_accruals': 'lost'
                })],
        })
        with freeze_time('2024-1-01'):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1)
            })
            allocation.action_validate()

        with freeze_time('2025-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "10 days are accrued")

        with freeze_time('2026-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10,
                         "All previous days are lost. 10 new days are added.")

    def test_matching_carryover_and_level_transition_dates(self):
        """
        When the carry over date matches the date of a level transition, some days are accrued. The number of
        accrued days is proportionate to the period that elapsed from the accrual period of the previous
        level. For example if 24 days are accrued yearly, and only 2 months have passed before the level
        transition has occured, then the number of accrued days will be 2/12 * 24 = 4 days

        Create an accrual plan:
            - Carryover date: July 1st.
        Create a milestone:
            - Number of accrued days: 12
            - Frequency: Yearly
            - Accrual date: January 1st
            - Carryover policy: No days carry over
        Create an allocation:
            - Start date: 01/01/2024
            - Type: Accrual
            - Accrual Plan: Use the one defined above.

        On 01/01/2025 (Accrual date), 12 days are accrued to the employee.
        On 01/07/2025 (Level transition date and carryover date):
            - The previous 12 days are lost.
            - (6/12) * 12 = 6 days are accrued to the employee.
            - Level tranisition occurs.
        On 01/01/2026 (Accrual date):
            - (6/12) / 14 = 7 days are accrued to the employee.
            - Total number of days = 6 + 7 = 13 days
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'carryover_date': 'other',
                'carryover_day': 1,
                'carryover_month': 'jul',
                'level_ids': [(0, 0, {
                    'added_value': 12,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'start_count': 0,
                    'start_type': 'day',
                    'action_with_unused_accruals': 'lost'
                }),
                (0, 0, {
                    'added_value': 14,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'start_count': 18,
                    'start_type': 'month',
                    'action_with_unused_accruals': 'lost'
                })],
        })
        with freeze_time('2024-1-01'):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1)
            })
            allocation.action_validate()

        with freeze_time('2025-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 12, "12 days are accrued")

        with freeze_time('2025-7-01'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 6, 1,
                         "All previous days are lost. 6 new days are added.")
        with freeze_time('2026-1-01'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 13, 1,
                        "7 days are accrued. Total days = 6 + 7 = 13.")

    def test_accrual_plan_with_multiple_levels(self):
        """
        Test that if an accrual plan with multiple levels accrues days at the start of the accrual period, then the carryover
        will be executed correctly and that the days are accrued correctly for the level transition.

        Define an accrual plan:
            1. The days are accrued at the start of the accrual period.
            2. The carryover date is on June 1st (01/06).
            3. Has 2 levels:
                a. First Level:
                      I. Starts immediately on allocation start date
                     II. Accrues 1 day monthly.
                    III. Carryover policy is None (no days are carried over).
                b. Second level:
                      I. Starts 20 Months after allocation start date.
                     II. Accrues 1 days monthly on January 1st (01/01).
                    III. Carryover policy is carryover with a maximum of 5.

        Create an allocation that starts 01/01/2024 and uses the above accrual plan.

        1. From 01/01/2024 to 01/05/2024: The employee is accrued 5 days.
        2. On 01/06/2024: The 5 days are lost due to carryover policy. 1 day is accrued for the new month.
           The employee now has 1 day.
        3. From 01/07/2024 to 01/08/2024: The employee is accrued 2 days.
           The employee now has 3 days.
        4. On 01/09/2024: Transition to new level. 1 day is accrued for the new month.
           The employee now has 4 days.
        5. From 01/010/2024 to 01/012/2024: 3 days are accrued.
           The employee now has 7 days.
        6. On 01/01/2025: 1 day is accrued.
        Total number of days =  8 days
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'accrued_gain_time': 'start',
                'carryover_date': 'other',
                'carryover_day': 1,
                'carryover_month': 'jun',
                'level_ids': [(0, 0, {
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'monthly',
                    'start_count': 0,
                    'start_type': 'day',
                    'action_with_unused_accruals': 'lost'
                }),
                (0, 0, {
                    'added_value': 1,
                    'added_value_type': 'day',
                    'frequency': 'monthly',
                    'start_count': 20,
                    'start_type': 'month',
                    'action_with_unused_accruals': 'maximum',
                    'postpone_max_days': 5
                })],
        })
        with freeze_time('2024-1-01'):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1)
            })
            allocation.action_validate()

        with freeze_time('2024-5-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 5)

        with freeze_time('2024-6-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 1)

        with freeze_time('2024-8-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 3)

        with freeze_time('2024-9-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4)

        with freeze_time('2024-12-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 7)

        with freeze_time('2025-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 8)

    def test_accrual_plan_with_multiple_levels_2(self):
        """
        Test that if an accrual plan with multiple levels accrues days at the start of the accrual period, then the carryover
        will be executed correctly and that the days are accrued correctly for the level transition.

        Define an accrual plan:
            1. The days are accrued at the start of the accrual period.
            2. The carryover date is on June 1st (01/06).
            3. Has 2 levels:
                a. First Level:
                      I. Starts immediately on allocation start date
                     II. Accrues 10 day yearly.
                    III. Carryover policy is None (no days are carried over).
                b. Second level:
                      I. Starts 30 Months after allocation start date.
                     II. Accrues 12 days yearly on January 1st (01/01).
                    III. Carryover policy is all (all days carry over).

        Create an allocation that starts 01/01/2024 and uses the above accrual plan.

        1. On 01/01/2024: The employee is accrued 10 days.
        2. On 01/01/2025: The employee is accrued 10 days.
        3. On 01/06/2025: All the days are lost due to carryover policy.
        4. On 01/01/2026: The employee is accrued 10 days.
        5. On 01/06/2026: All the days are lost due to carryover policy.
        6. On 01/09/2026: Level transition occurrs. 6.67 days are accrued.
        7. On 01/01/2027:
            - 4 days are accrued for the period from 01/09/2026 until 31/12/2026.
            - 12 days are accrued for the new period (becase days are accrue at the start of the accrual period)
            - Total number of days is 6.67 + 4 + 12 = 22.67 days.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'accrued_gain_time': 'start',
                'carryover_date': 'other',
                'carryover_day': 1,
                'carryover_month': 'jun',
                'level_ids': [(0, 0, {
                    'added_value': 10,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'start_count': 0,
                    'start_type': 'day',
                    'action_with_unused_accruals': 'lost'
                }),
                (0, 0, {
                    'added_value': 12,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'start_count': 32,
                    'start_type': 'month',
                    'action_with_unused_accruals': 'all',
                })],
        })
        with freeze_time('2024-1-01'):
            allocation = self.env['hr.leave.allocation'].with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'date_from': datetime.date(2024, 1, 1)
            })
            allocation.action_validate()

        with freeze_time('2024-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10)

        with freeze_time('2025-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 20)

        with freeze_time('2025-6-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 0)

        with freeze_time('2026-1-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10)

        with freeze_time('2026-6-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 0)

        with freeze_time('2026-9-01'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 10.7, 1)

        with freeze_time('2027-1-01'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 22.67, 2)

    def test_carried_over_days_expiry_date_computation(self):
        """
        Assert that the expiration date is computed correclty in the case of an accrual plan with multiple levels.
        - Create an accrual plan:
            - Carryover date: 1 April
            - First level:
                - Accrues 10 days.
                - Accrual date: bi-yearly on 1 January and 1 July
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 5 months.
            - Second level:
                - Accrues 20 days.
                - Accrual date: bi-yearly on 1 January and 1 July
                - Starts 17 months after accrual start date.
                - Carryover policy: all days carry over
                - Carried over days validity: 2 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - First carryover date 01/04/2024. The carried over days will expire in 5 months.
        - The expiration date should be 01/09/2024 and not 01/06/2024. In other words, the expiration date
          should be computed using the first level's validity period and not the second level's expiration period.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'biyearly',
                'first_month': 'jan',
                'first_month_day': 1,
                'second_month': 'jul',
                'second_month_day': 1,
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 5,
            }),
            (0, 0, {
                'added_value_type': 'day',
                'start_count': 17,
                'start_type': 'month',
                'added_value': 20,
                'frequency': 'biyearly',
                'first_month': 'jan',
                'first_month_day': 1,
                'second_month': 'jul',
                'second_month_day': 1,
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            })],
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-04-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 9, 1))

    def test_carried_over_days_expiry_date_computation_2(self):
        """
        Assert that the expiration date is computed correclty in the case of an accrual plan with multiple levels.
        - Create an accrual plan:
            - Carryover date: 1 April
            - First level:
                - Accrues 10 days.
                - Accrual date: yearly on 1 January
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 2 months.
            - Second level:
                - Accrues 20 days.
                - Accrual date: yearly on 1 January
                - Starts 2 years after accrual start date.
                - Carryover policy: all days carry over
                - Carried over days validity: 3 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - 01/04/2024 carryover date. The carried over days will expire in 2 months.
        - 01/06/2024 expiration date .
        - 01/01/2025 level transition date.
        - 01/04/2025 carryover date. The carried over days will expire in 3 months.
        - 01/07/2025 expiration date.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            }),
            (0, 0, {
                'added_value_type': 'day',
                'start_count': 2,
                'start_type': 'year',
                'added_value': 20,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 3,
            })],
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-04-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 6, 1))

        with freeze_time('2025-04-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 7, 1))

    def test_carried_over_days_expiry_date_computation_3(self):
        """
        Assert that the expiration date is computed correclty in the case of an accrual plan with multiple levels.
        - Create an accrual plan:
            - Carryover date: 1 May
            - First level:
                - Accrues 10 days.
                - Accrual date: yearly on 1 January
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 2 months.
            - Second level:
                - Accrues 20 days.
                - Accrual date: yearly on 1 January
                - Starts 29 months (2 years and 5 months) after accrual start date.
                - Carryover policy: all days carry over
                - Carried over days validity: 3 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - 01/05/2024 carryover date. The carried over days will expire in 2 months.
        - 01/07/2024 expiration date .
        - 01/05/2025 carryover date. The carried over days will expire in 2 months.
        - 01/06/2025 level transition date. The carried over days on 01/05/2025 should still expire on 01/07/2025
        - 01/07/2025 expiration date.
        - 01/01/2026 accrual date (the new expiration date should be computed and set to 01/08/2026)
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'may',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            }),
            (0, 0, {
                'added_value_type': 'day',
                'start_count': 29,
                'start_type': 'month',
                'added_value': 20,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 3,
            })],
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-05-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1))

        with freeze_time('2025-05-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 7, 1))

        with freeze_time('2026-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2026, 8, 1))

    def test_carried_over_days_expiry_date_computation_4(self):
        """
        Assert that the expiration date is computed correclty when the carryover date changes.
        - Create an accrual plan:
            - Carryover date: 1 May
            - One level:
                - Accrues 10 days.
                - Accrual date: yearly on 1 January
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 2 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - 01/05/2024 carryover date. The carried over days will expire in 2 months.
        - 01/07/2024 expiration date .
        - Change carryover date to 1 July.
        - 01/01/2025 accrual date (The expiration date should be computed and set to 01/09/2025)
        - 01/07/2025 carryover date. The carried over days will expire in 2 months.
        - 01/09/2025 expiration date.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'may',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            })],
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-05-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1))

        accrual_plan.carryover_month = 'jul'
        with freeze_time('2025-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1))

        with freeze_time('2025-07-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1))

    def test_carried_over_days_expiry_date_computation_5(self):
        """
        Assert that the expiration date is computed correclty when the carryover date changes.
        - Create an accrual plan:
            - Carryover date: 1 May
            - One level:
                - Accrues 10 days.
                - Accrual date: yearly on 1 January
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 2 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - 01/05/2024 carryover date. The carried over days will expire in 2 months.
        - Change carryover date to 1 July. The carried over days on 01/05/2024 should still expire on 01/07/2024
        - 01/07/2024 expiration date .
        - 01/01/2025 accrual date (The expiration date should be computed and set to 01/09/2025)
        - 01/07/2025 carryover date. The carried over days will expire in 2 months.
        - 01/09/2025 expiration date.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'may',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            })],
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-05-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1))

        with freeze_time('2024-06-01'):
            accrual_plan.carryover_month = 'jul'
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1))

        with freeze_time('2025-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1))

        with freeze_time('2025-07-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1))

    def test_carried_over_days_expiry(self):
        """
        - Create an accrual plan:
            - Carryover date: 20 April
            - One level:
                - Accrues 10 days.
                - Accrual date: 1 January
                - Starts immediately on allocation start date
                - Carryover policy: carryover with a maximum of 5 days
                - Carried over days validity: 20 days.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2024
        - On 01/01/2025: 10 days are accrued.
        - On 20/04/2025(carryover date): 5 days are lost and 5 days will carry over.
        - On 10/05/2025(carried over days expiration date): 5 days are lost.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 20,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 5,
                'accrual_validity': True,
                'accrual_validity_type': 'day',
                'accrual_validity_count': 20,
            })],
        })
        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2025-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 10)
        with freeze_time('2025-04-20'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 5)
        with freeze_time('2025-05-10'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0)

    def test_time_off_using_expiring_carried_over_days(self):
        """
        Assert that the employee balance is set correctly when taking time-off using carried over days
        that are going to expire soon.
        - Create an accrual plan:
            - Carryover date: 1 April
            - One level:
                - Accrues 10 days.
                - Accrual date: bi-yearly on 1 January and 1 July
                - Starts immediately on allocation start date
                - Carryover policy: all days carry over
                - Carried over days validity: 5 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2024
        - On 01/07/2024: 10 days are accrued.
        - On 01/01/2025: 10 days are accrued. The employee now has 20 days.
        - On 01/04/2025(carryover date): The 20 days will carryover. The 20 days will expire after 5 months.
        - On 01/07/2025: 10 days are accrued. The employee now has 30 days.
        - From 02/07 to 05/07 the employee is on leave (3 days). The employee has 27 days now.
        - On 01/09/2025(carried over days expiration date): (20 expiring_days - 3 time-off days) 17 days are lost.
        - The employee's balance should be 10 days at the end.
        - allocation.number_of_days (employee balance + leaves_taken) should be 13 days at the end.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'biyearly',
                'first_month': 'jan',
                'first_month_day': 1,
                'second_month': 'jul',
                'second_month_day': 1,
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 5,
            })],
        })
        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-07-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 10)
        with freeze_time('2025-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 20)
        with freeze_time('2025-04-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 20)
        with freeze_time('2025-07-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 30)

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2025-07-02',
            'request_date_to': '2025-07-04',
        })
        leave.action_validate()

        with freeze_time('2025-09-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 13, 10, "The employee balance should be 10 days.")

    def test_time_off_balance_computation(self):
        """
        Assert that the time off balance is computed correctly after applying carryover-policy and after
        expiring carried over days.
        - Create an accrual plan:
            - Carryover date: 1 April
            - One level:
                - Accrues 10 days.
                - Accrual date: yearly on 1 January
                - Starts immediately on allocation start date
                - Carryover policy: carry over with a maximum of 5 days.
                - Carried over days validity: 5 months.
        - Create an allocation that uses the above accrual plan:
            - Starts on 01/01/2023
        - On 01/01/2024: 10 days are accrued.
        - The employee takes 2 days as time-off. The employee has 8 days now.
        - On 01/04/2024(carryover date): Only 5 days will carry over. These 5 days will expire after 5 months.
        - The employee takes 1 day as time-off. The employee has 4 days now.
        - On 01/09/2024: all days will expire. The employee has 0 days now.
        - On 01/01/2025: 10 days are accrued. The employee has 10 days now.
        - The employee takes 3 days off. The employee has 7 days now.
        - On 01/04/2025 (carryover date): Only 5 days will carryover.
        - The employee's balance should be 5 days at the end.
        - allocation.number_of_days (employee balance + leaves_taken) should be 11 days at the end.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': 'apr',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'maximum',
                'postpone_max_days': 5,
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 5,
            })]
        })
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()

        with freeze_time('2024-01-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 10, 10, "The employee was accrued 10 days")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2024-03-25',
            'request_date_to': '2024-03-26',
        })
        leave.action_validate()

        with freeze_time('2024-04-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 7, 5, "Only 5 days will carry over")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2024-04-02',
            'request_date_to': '2024-04-02',
        })
        leave.action_validate()

        with freeze_time('2024-09-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 3, 0, "The 5 carried over days should expire")

        with freeze_time('2025-01-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 13, 10, "The employee was accrued 10 days")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2025-01-08',
            'request_date_to': '2025-01-10',
        })
        leave.action_validate()

        with freeze_time('2025-04-01'):
            allocation._update_accrual()
            self.assert_allocation_and_balance(allocation, 11, 5, "Only 5 days will carry over")

    def test_carriedover_days_expiration_reset(self):
        """
        Description:

        Assert that the number of expiring carry-over days and the expiration date of the carry-over days
        are reset when the start date of the allocation is changed. This should result in the number of accrued days
        being consistent when setting the allocation start date to some date, changing the start date to another date
        and then changing the start date back to the first date.

        Steps:

        Create an accrual plan:
        - Carryover date on allocation start date.
        - Has 1 level:
            * Start 0 days after allocation start date.
            * Accrues 1 day monthly on 1st day of the month.
            * Carryover policy all accrued time carried over.
            * Carryover validity 1 month.

        Note: The following dates are in mm/dd/YYYY
        Create an allocation:
            * Allocation type: accrual allocation.
            * Accrual plan: use the one defined above.
            * Set allocation start date 08/01/2023.

            Assume that today is 09/25/2024

            * Compute the number of accrued days on 09/25/2024 -> 2 days.

            * Change allocation start date to 09/01/2023.
              - Number of expiring carry-over days will reset to 0
              - Expiration date of carry-over days will reset to False
              - Compute the number of accrued days on 09/25/2024 -> 12 days.

            * Change allocation start date back to 08/01/2023.
              - Number of expiring carry-over days will reset to 0
              - Expiration date of carry-over days will reset to False
              - Compute the number of accrued days on 09/25/2024 -> 2 days.
        """
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 1,
            })]
        })

        with freeze_time('2023-08-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'allocation_type': 'accrual',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'date_from': '2023-08-01'
            })

        with freeze_time('2024-09-25'):
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 2)

            allocation.date_from = '2023-09-01'
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 12)

            allocation.date_from = '2023-08-01'
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 2)

    def test_start_accrual_gain_time_immediately(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': '1.25 days each 1st of the month',
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'level_ids':
                [(0, 0, {
                    'start_type': 'day',
                    'start_count': 0,
                    'added_value_type': 'day',
                    'added_value': 1.25,
                    'frequency': 'monthly',
                    'cap_accrued_time': False,
                    'action_with_unused_accruals': 'all',
                })],
        })

        with freeze_time('2024-09-02'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })

            allocation.action_validate()
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_days, 1.21, 2, 'Days for the current month should be granted immediately')

            leave = self.env['hr.leave'].create({
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-09-13 08:00:00',
                'request_date_to': '2024-09-13 17:00:00',
            })
            leave.action_validate()
            remaining_leaves = self.leave_type.get_allocation_data(self.employee_emp, date(2024, 9, 14))[self.employee_emp][0][1]['remaining_leaves']
            self.assertAlmostEqual(remaining_leaves, 0.21, 2, 'Leave should be deducted from accrued days')

        with freeze_time("2024-10-01"):
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_days, 2.46, 2, 'Days for the upcoming month should be granted on the 1st')

    def test_cache_invalidation_with_future_leaves(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': '1 days every last day of the month',
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids':
                [(0, 0, {
                    'start_type': 'day',
                    'start_count': 0,
                    'added_value_type': 'day',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'cap_accrued_time': False,
                    'action_with_unused_accruals': 'all',
                    'first_day': 31,
                })
            ],
        })

        with freeze_time('2024-06-30'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation.action_validate()
            allocation._update_accrual()

            leave = self.env['hr.leave'].create({
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-09-02',
                'request_date_to': '2024-09-03',
            })
            leave.action_validate()

        with freeze_time('2024-07-31'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 1, 'Days should be allocated even when leave is taken in the future')

    def test_accrual_days_left_under_carryover_maximum(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': '21 days per year, 28 days cap, 7 carryover max',
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'level_ids':
                [(0, 0, {
                "accrued_gain_time": "start",
                "action_with_unused_accruals": "maximum",
                "added_value": 21,
                "cap_accrued_time": True,
                "first_day": 1,
                "first_month": "jan",
                "first_month_day": 1,
                "frequency": "yearly",
                "maximum_leave": 28,
                "postpone_max_days": 7,
                "start_count": 0,
                "start_type": "day",
                "yearly_day": 1,
                "yearly_month": "jan"
            })
            ],
        })

        with freeze_time('2024-11-25'):
            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = '2024-01-01'
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            allocation = f.record
            allocation.action_validate()

            # take 15 days, left with 6 days on the alloc
            leave = self.env['hr.leave'].create({
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-10-07',
                'request_date_to': '2024-10-25',
            })
            leave.action_validate()
            data = self.leave_type.get_allocation_data(self.employee_emp, date(2025, 1, 15))
            remaining_future = data[self.employee_emp][0][1]["remaining_leaves"]
            self.assertEqual(remaining_future, 27)

    def test_accrual_unused_accrual_reset_to_lost(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': '21 days per year, 28 days cap, 7 carryover max',
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
        })

        plan = self.env["hr.leave.accrual.level"].with_context(tracking_disable=True).create({
            "accrual_plan_id" : accrual_plan.id,
        })

        with Form(plan) as f:
            f.added_value = 21
            f.frequency = 'yearly'
            f.yearly_day_display = "1"
            f.cap_accrued_time = True
            f.maximum_leave = 28
            f.start_count = 0
            # Set a maximum carry-over
            f.action_with_unused_accruals = 'maximum'
            f.postpone_max_days = 7
            # Set it back to 'lost'
            f.action_with_unused_accruals = 'lost'

        with freeze_time('2024-11-25'):
            with Form(self.env['hr.leave.allocation']) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = '2024-01-01'
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            allocation = f.record
            allocation.action_validate()

            # take 15 days, left with 6 days on the alloc
            leave = self.env['hr.leave'].create({
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-10-07',
                'request_date_to': '2024-10-25',
            })
            leave.action_validate()
            data = self.leave_type.get_allocation_data(self.employee_emp, date(2025, 1, 15))
            remaining_future = data[self.employee_emp][0][1]["remaining_leaves"]
            self.assertEqual(remaining_future, 21)
