# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo.tools import float_compare

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install')
class TestAccrualAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAccrualAllocations, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'officer',
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

    def test_frequency_daily(self):
        with freeze_time(datetime.date(2017, 12, 5)):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'daily',
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
            allocation.action_confirm()
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
        with freeze_time(datetime.date(2017, 12, 5)):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
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
                allocation.action_confirm()
                allocation.action_validate()
                self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
                self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
                allocation._update_accrual()
                nextWeek = allocation.date_from + relativedelta(days=1, weekday=0)
                self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

            with freeze_time(nextWeek):
                allocation._update_accrual()
                nextWeek = datetime.date.today() + relativedelta(days=1, weekday=0)
                #Prorated
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
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'bimonthly',
                    'first_day': 1,
                    'second_day': 15,
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
            allocation.action_confirm()
            allocation.action_validate()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')
            allocation._update_accrual()
            next_date = datetime.date(2021, 9, 15)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet. The accrual starts tomorrow.')

        with freeze_time(next_date):
            next_date = datetime.date(2021, 10, 1)
            allocation._update_accrual()
            #Prorated
            self.assertAlmostEqual(allocation.number_of_days, 0.7857, 4, 'There should be 0.7857 day allocated.')
            self.assertEqual(allocation.nextcall, next_date, 'The next call date of the cron should be October 1st')

        with freeze_time(next_date):
            allocation._update_accrual()
            #Not Prorated
            self.assertAlmostEqual(allocation.number_of_days, 1.7857, 4, 'There should be 1.7857 day allocated.')

    def test_frequency_monthly(self):
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
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
            allocation.action_confirm()
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
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'biyearly',
                    'maximum_leave': 10000,
                })],
            })
            #this sets up an accrual on the 1st of January and the 1st of July
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_confirm()
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
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'yearly',
                    'maximum_leave': 10000,
                })],
            })
            #this sets up an accrual on the 1st of January
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            self.setAllocationCreateDate(allocation.id, '2021-09-01 00:00:00')
            allocation.action_confirm()
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
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 5,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
                    'maximum_leave': 10000,
                })],
            })
            accrual_plan_based_on_worked_time = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 5,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
                    'maximum_leave': 10000,
                    'is_based_on_worked_time': True,
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
            holiday_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': 'no',
                'responsible_id': self.user_hrmanager_id,
                'time_type': 'leave',
            })
            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': holiday_type.id,
                'date_from': '2021-09-02 00:00:00',
                'date_to': '2021-09-02 23:59:59',
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
        with freeze_time(datetime.date(2017, 12, 5)):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'daily',
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
            allocation.action_confirm()
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
                #The maximum value is 1 so this shouldn't change anything
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 1, 'There should be only 1 day allocated.')

    def test_check_max_value_hours(self):
        with freeze_time(datetime.date(2017, 12, 5)):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'hours',
                    'frequency': 'daily',
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
            allocation.action_confirm()
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
                #The maximum value is 1 so this shouldn't change anything
                allocation._update_accrual()
                self.assertEqual(allocation.number_of_days, 0.5, 'There should be only 0.5 days allocated.')

    def test_accrual_transition_immediately(self):
        with freeze_time(datetime.date(2017, 12, 5)):
            #1 accrual with 2 levels and level transition immediately
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'transition_mode': 'immediately',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
                    'maximum_leave': 1,
                }), (0, 0, {
                    'start_count': 10,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
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
            allocation.action_confirm()
            allocation.action_validate()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env['hr.leave.accrual.level'].search([('accrual_plan_id', '=', accrual_plan.id), ('start_count', '=', 10)])
            self.assertEqual(allocation._get_current_accrual_plan_level_id(next_date)[0], second_level, 'The second level should be selected')

    def test_accrual_transition_after_period(self):
        with freeze_time(datetime.date(2017, 12, 5)):
            # 1 accrual with 2 levels and level transition after
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'transition_mode': 'end_of_accrual',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
                    'maximum_leave': 1,
                }), (0, 0, {
                    'start_count': 10,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'weekly',
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
            allocation.action_confirm()
            allocation.action_validate()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env['hr.leave.accrual.level'].search([('accrual_plan_id', '=', accrual_plan.id), ('start_count', '=', 10)])
            self.assertEqual(allocation._get_current_accrual_plan_level_id(next_date)[0], second_level, 'The second level should be selected')

    def test_unused_accrual_lost(self):
        #1 accrual with 2 levels and level transition immediately
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'daily',
                    'maximum_leave': 1,
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
            allocation.action_confirm()
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 9, 1)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 1, 'The number of days should be reset')

    def test_unused_accrual_postponed(self):
        # 1 accrual with 2 levels and level transition after
        # This also tests retroactivity
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'daily',
                    'maximum_leave': 25,
                    'action_with_unused_accruals': 'postponed',
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
            allocation.action_confirm()
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 9, 1)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 25, 'The maximum number of days should be reached and kept.')

        with freeze_time('2021-01-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 2,
                    'added_value_type': 'days',
                    'frequency': 'yearly',
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'postponed',
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
            allocation.action_confirm()
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time('2023-01-26'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4, 'The maximum number of days should be reached and kept.')

    def test_accrual_over_years(self):
        hr_leave_allocation = self.env['hr.leave.allocation']
        with freeze_time('2023-11-20'):
            accrual_plan_postponed = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'first_day': 20,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'postponed',
                    'postpone_max_days': 10,
                })],
            })
            accrual_plan_lost = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'first_day': 20,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'lost',
                })],
            })
            allocation_postponed = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee (postponed)',
                'accrual_plan_id': accrual_plan_postponed.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation_lost = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee (lost)',
                'accrual_plan_id': accrual_plan_lost.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation_postponed.action_confirm()
            allocation_postponed.action_validate()
            allocation_lost.action_confirm()
            allocation_lost.action_validate()

        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2023, 11, 20)

        with freeze_time('2023-12-21'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(allocation_postponed.number_of_days, 1)
        self.assertEqual(allocation_lost.number_of_days, 1)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2023, 12, 20))
        self.assertEqual(allocation_lost.lastcall, datetime.date(2023, 12, 20))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2024, 1, 20))
        self.assertEqual(allocation_lost.nextcall, datetime.date(2024, 1, 20))

        with freeze_time('2024-1-5'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(float_compare(allocation_postponed.number_of_days, 1.39, 2), 0)
        self.assertEqual(allocation_lost.number_of_days, 0)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2024, 1, 1))
        self.assertEqual(allocation_lost.lastcall, datetime.date(2023, 12, 20))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2024, 1, 20))
        self.assertEqual(allocation_lost.nextcall, datetime.date(2024, 1, 20))

        with freeze_time('2024-1-21'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(allocation_postponed.number_of_days, 2)
        self.assertEqual(allocation_lost.number_of_days, 1)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2024, 1, 20))
        self.assertEqual(allocation_lost.lastcall, datetime.date(2024, 1, 20))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2024, 2, 20))
        self.assertEqual(allocation_lost.nextcall, datetime.date(2024, 2, 20))

    def test_accrual_over_multiple_years(self):
        hr_leave_allocation = self.env['hr.leave.allocation']
        with freeze_time('2023-1-1'):
            accrual_plan_postponed = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'first_day': 20,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'postponed',
                    'postpone_max_days': 10,
                })],
            })
            allocation_postponed = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee (postponed)',
                'accrual_plan_id': accrual_plan_postponed.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation_postponed.action_confirm()
            allocation_postponed.action_validate()

        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2023, 1, 1)

        with freeze_time('2026-1-1'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(float_compare(allocation_postponed.number_of_days, 10.39, 2), 0)
        # 2023 --> 2024: 0 + 12 = 12
        # 12 ==> 10 (postpone_max_days)
        # 2024 --> 2025: 10 + 12 = 22
        # 22 ==> 10 (postpone_max_days)
        # 2025 --> 2026: 10 + 12 = 22
        # 22 ==> 10 (postpone_max_days)
        # 1st January 2026: 10 + part between 2025-12-20 and 2026-1-1 = 10.39
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 1, 1))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 1, 20))

        with freeze_time('2026-1-10'):
            hr_leave_allocation._update_accrual()
        # Nothing changes
        self.assertEqual(float_compare(allocation_postponed.number_of_days, 10.39, 2), 0)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 1, 1))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 1, 20))
        with freeze_time('2026-1-20'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(float_compare(allocation_postponed.number_of_days, 11, 2), 0)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 1, 20))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 2, 20))
        with freeze_time('2026-2-20'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(float_compare(allocation_postponed.number_of_days, 12, 2), 0)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 2, 20))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 3, 20))

    def test_accrual_over_multiple_years_first_of_month(self):
        hr_leave_allocation = self.env['hr.leave.allocation']
        with freeze_time('2023-1-1'):
            accrual_plan_postponed = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'first_day': 1,
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'postponed',
                    'postpone_max_days': 10,
                })],
            })
            allocation_postponed = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee (postponed)',
                'accrual_plan_id': accrual_plan_postponed.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
            })
            allocation_postponed.action_confirm()
            allocation_postponed.action_validate()

        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2023, 1, 1)

        with freeze_time('2026-1-1'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(allocation_postponed.number_of_days, 11)
        # 2023 --> 2024: 0 + 12 = 12
        # 12 ==> 10 (postpone_max_days)
        # 2024 --> 2025: 10 + 12 = 22
        # 22 ==> 10 (postpone_max_days)
        # 2025 --> 2026: 10 + 12 = 22
        # 22 ==> 10 (postpone_max_days)
        # 1st January 2026: 10 + 1 = 11
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 1, 1))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 2, 1))

        with freeze_time('2026-1-10'):
            hr_leave_allocation._update_accrual()
        # Nothing changes
        self.assertEqual(allocation_postponed.number_of_days, 11)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 1, 1))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 2, 1))
        with freeze_time('2026-2-20'):
            hr_leave_allocation._update_accrual()
        self.assertEqual(allocation_postponed.number_of_days, 12)
        self.assertEqual(allocation_postponed.lastcall, datetime.date(2026, 2, 1))
        self.assertEqual(allocation_postponed.nextcall, datetime.date(2026, 3, 1))

    def test_unused_accrual_postponed_limit(self):
        # 1 accrual with 2 levels and level transition after
        # This also tests retroactivity
        with freeze_time('2021-09-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'daily',
                    'maximum_leave': 25,
                    'action_with_unused_accruals': 'postponed',
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
            allocation.action_confirm()
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 9, 1)
        with freeze_time('2022-01-01'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 16, 'The maximum number of days should be reached and kept.')

        with freeze_time('2021-01-01'):
            accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
                'name': 'Accrual Plan For Test',
                'level_ids': [(0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 15,
                    'added_value_type': 'days',
                    'frequency': 'yearly',
                    'maximum_leave': 100,
                    'action_with_unused_accruals': 'postponed',
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
            allocation.action_confirm()
            allocation.action_validate()

        # Reset the cron's lastcall
        accrual_cron = self.env['ir.cron'].sudo().env.ref('hr_holidays.hr_leave_allocation_cron_accrual')
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time('2023-01-26'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 22, 'The maximum number of days should be reached and kept.')

    def test_accrual_skipped_period(self):
        # Test that when an allocation is made in the past and the second level is technically reached
        #  that the first level is not skipped completely.
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': 15,
                'added_value_type': 'days',
                'frequency': 'biyearly',
                'maximum_leave': 100,
                'action_with_unused_accruals': 'postponed',
            }), (0, 0, {
                'start_count': 4,
                'start_type': 'month',
                'added_value': 10,
                'added_value_type': 'days',
                'frequency': 'biyearly',
                'maximum_leave': 500,
                'action_with_unused_accruals': 'postponed',
            })],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual Allocation - Test',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': datetime.date(2020, 8, 16),
        })
        allocation.action_confirm()
        allocation.action_validate()
        with freeze_time('2022-1-10'):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 30.82, 2, "Invalid number of days")

    def test_three_levels_accrual(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 2,
                'start_type': 'month',
                'added_value': 3,
                'added_value_type': 'days',
                'frequency': 'monthly',
                'maximum_leave': 3,
                'action_with_unused_accruals': 'postponed',
                'first_day': 31,
            }), (0, 0, {
                'start_count': 3,
                'start_type': 'month',
                'added_value': 6,
                'added_value_type': 'days',
                'frequency': 'monthly',
                'maximum_leave': 6,
                'action_with_unused_accruals': 'postponed',
                'first_day': 31,
            }), (0, 0, {
                'start_count': 4,
                'start_type': 'month',
                'added_value': 1,
                'added_value_type': 'days',
                'frequency': 'monthly',
                'maximum_leave': 100,
                'action_with_unused_accruals': 'postponed',
                'first_day': 31,
            })],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual Allocation - Test',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': datetime.date(2022, 1, 31),
        })
        allocation.action_confirm()
        allocation.action_validate()
        with freeze_time('2022-7-20'):
            allocation._update_accrual()
        # The first level gives 3 days
        # The second level could give 6 days but since the first level was already giving
        # 3 days, the second level gives 3 days to reach the second level's limit.
        # The third level gives 1 day since it only counts for one iteration.
        self.assertEqual(allocation.number_of_days, 7)

    def test_accrual_lost_previous_days(self):
        # Test that when an allocation with two levels is made and that the first level has it's action
        # with unused accruals set as lost that the days are effectively lost
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [
                (0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                }),
                (0, 0, {
                    'start_count': 1,
                    'start_type': 'year',
                    'added_value': 1,
                    'added_value_type': 'days',
                    'frequency': 'monthly',
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                }),
            ],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual Allocation - Test',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': datetime.date(2021, 1, 1),
        })
        allocation.action_confirm()
        allocation.action_validate()
        with freeze_time('2022-4-4'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4, "Invalid number of days")

    def test_accrual_lost_first_january(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [
                (0, 0, {
                    'start_count': 0,
                    'start_type': 'day',
                    'added_value': 3,
                    'added_value_type': 'days',
                    'frequency': 'yearly',
                    'maximum_leave': 12,
                    'action_with_unused_accruals': 'lost',
                })
            ],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual Allocation - Test',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': datetime.date(2019, 1, 1),
        })
        allocation.action_confirm()
        allocation.action_validate()
        with freeze_time('2022-4-1'):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 3, "Invalid number of days")

    def test_accrual_maximum_leaves(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'days',
                'frequency': 'daily',
                'maximum_leave': 5,
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

        with freeze_time(datetime.date(2021, 10, 3)):
            allocation.action_confirm()
            allocation.action_validate()
            allocation._update_accrual()

            self.assertEqual(allocation.number_of_days, 5, "Should accrue maximum 5 days")

    def test_accrual_maximum_leaves_no_limit(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'days',
                'frequency': 'daily',
                'maximum_leave': 0,
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

        with freeze_time(datetime.date(2021, 10, 3)):
            allocation.action_confirm()
            allocation.action_validate()
            allocation._update_accrual()

            self.assertEqual(allocation.number_of_days, 29, "No limits for accrued days")

    def test_accrual_leaves_taken_maximum(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'days',
                'frequency': 'weekly',
                'week_day': 'mon',
                'maximum_leave': 5,
            })],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': '2022-01-01',
        })
        allocation.action_confirm()
        allocation.action_validate()

        with freeze_time(datetime.date(2022, 3, 2)):
            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 5, "Maximum of 5 days accrued")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': '2022-03-07 00:00:00',
            'date_to': '2022-03-11 23:59:59',
        })
        leave.action_validate()

        with freeze_time(datetime.date(2022, 6, 1)):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "Should accrue 5 additional days")

    def test_accrual_leaves_taken_maximum_hours(self):
        accrual_plan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True).create({
            'name': 'Accrual Plan For Test',
            'level_ids': [(0, 0, {
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'hours',
                'frequency': 'weekly',
                'week_day': 'mon',
                'maximum_leave': 10,
            })],
        })
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 0,
            'allocation_type': 'accrual',
            'date_from': '2022-01-01',
        })
        allocation.action_confirm()
        allocation.action_validate()

        with freeze_time(datetime.date(2022, 4, 1)):
            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 10 / self.hours_per_day, "Maximum of 10 hours accrued")

        leave = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': '2022-03-07 00:00:00',
            'date_to': '2022-03-07 23:59:59'
        })
        leave.action_validate()

        with freeze_time(datetime.date(2022, 6, 1)):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 18 / self.hours_per_day, "Should accrue 8 additional hours")
