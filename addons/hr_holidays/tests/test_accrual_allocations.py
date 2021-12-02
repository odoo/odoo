# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

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
        with freeze_time(datetime.date(2021, 9, 5)):
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
            calendar_emp = self.env['resource.calendar'].create({
                'name': '40 Hours',
                'tz': self.employee_emp.tz,
                'attendance_ids': [
                    (0, 0, {
                        'name': '%s_%d' % ('40 Hours', index),
                        'hour_from': 8,
                        'hour_to': 12,
                        'dayofweek': str(index),
                        'day_period': 'morning'
                    }, {
                        'name': '%s_%d' % ('40 Hours', index),
                        'hour_from': 13,
                        'hour_to': 18,
                        'dayofweek': str(index),
                        'day_period': 'afternoon'
                    }) for index in range(5)
                ],
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
                'state': 'validate',
            })
            allocation_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan_based_on_worked_time.id,
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'number_of_days': 0,
                'allocation_type': 'accrual',
                'state': 'validate',
            })
            self.setAllocationCreateDate(allocation_not_worked_time.id, '2021-08-01 00:00:00')
            self.setAllocationCreateDate(allocation_worked_time.id, '2021-08-01 00:00:00')
            holiday_type = self.env['hr.leave.type'].create({
                'name': 'Paid Time Off',
                'requires_allocation': 'no',
                'responsible_id': self.user_hrmanager_id,
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
            self.assertAlmostEqual(allocation_worked_time.number_of_days, 3.42857, 4, 'There should be 3.42857 days allocated.')
            self.assertEqual(allocation_not_worked_time.nextcall, datetime.date(2021, 9, 13), 'The next call date of the cron should be the September 13th')
            self.assertEqual(allocation_worked_time.nextcall, datetime.date(2021, 9, 13), 'The next call date of the cron should be the September 13th')

        with freeze_time(next_date + relativedelta(days=7)):
            next_date = datetime.date(2021, 9, 20)
            self.env['hr.leave.allocation']._update_accrual()
            self.assertAlmostEqual(allocation_not_worked_time.number_of_days, 9.2857, 4, 'There should be 9.2857 days allocated.')
            self.assertEqual(allocation_not_worked_time.nextcall, next_date, 'The next call date of the cron should be September 20th')
            self.assertAlmostEqual(allocation_worked_time.number_of_days, 8.42857, 4, 'There should be 8.42857 days allocated.')
            self.assertEqual(allocation_worked_time.nextcall, next_date, 'The next call date of the cron should be September 20th')

    def test_check_max_value(self):
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

    def test_accrual_transition_immediately(self):
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
            self.assertEqual(allocation.number_of_days, 0, 'There number of days should be reset')

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
        self.assertEqual(allocation.number_of_days, 15, 'The maximum number of days should be reached and kept.')

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
        self.assertAlmostEqual(allocation.number_of_days, 30.79, 2, "Invalid number of days")

    def test_future_accrual(self):
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

        with freeze_time(datetime.date(2021, 9, 5)):
            allocation.action_confirm()
            allocation.action_validate()

            self.assertFalse(allocation.nextcall)
            self.assertEqual(allocation.number_of_days, 0)

            self.assertEqual(allocation.holiday_status_id.additional_leaves, 0)
            self.assertEqual(allocation.holiday_status_id.remaining_leaves, 0)

            with_future_accrual = allocation.with_context(employee_id=self.employee_emp.id, future_accrual_date=datetime.date(2021, 9, 30))
            self.assertAlmostEqual(with_future_accrual.holiday_status_id.additional_leaves, 3.29, 2, 'Should show 3.29 future leaves')
            self.assertEqual(with_future_accrual.holiday_status_id.remaining_leaves, 0, 'Remaining leaves should stay')

            self.assertFalse(with_future_accrual.nextcall, 'Allocation should not change')
            self.assertEqual(with_future_accrual.number_of_days, 0, 'Allocation should not change')

            self.assertFalse(allocation.nextcall, 'Allocation should not change')
            self.assertEqual(allocation.number_of_days, 0, 'Allocation should not change')

    def test_cancel_future_accrual(self):
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

        with freeze_time(datetime.date(2021, 9, 5)):
            allocation.action_confirm()
            allocation.action_validate()

            self.assertEqual(allocation.number_of_days, 0)

            with self.assertRaises(ValidationError):
                self.env['hr.leave'].with_user(self.user_employee).create({
                    'name': 'future leave',
                    'employee_id': self.employee_emp.id,
                    'holiday_status_id': self.leave_type.id,
                    'date_from': '2021-09-06',
                    'date_to': '2021-09-07',
                    'number_of_days': 1,
                    'state': 'confirm',
                })

            with_future_accrual = allocation.with_context(employee_id=self.employee_emp.id, future_accrual_date=datetime.date(2021, 9, 13))
            self.assertAlmostEqual(with_future_accrual.holiday_status_id.additional_leaves, 1.29, 2, 'Should return 1.29 future leaves')

            # The Time Off can be requested / validated using future accrued leave
            leave = self.env['hr.leave'].with_user(self.user_employee).create({
                'name': 'future leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': '2021-09-14',
                'date_to': '2021-09-15',
                'number_of_days': 1,
                'state': 'confirm',
            })
            leave.with_user(self.user_hrmanager_id).action_validate()

            accrual_plan.level_ids[0].added_value_type = 'hours'
            self.assertAlmostEqual(with_future_accrual.holiday_status_id.additional_leaves, 0.16, 2, 'Should return 0.16 future leaves')

        self.assertEqual(leave.state, 'validate', 'The leave should be validated')

        with freeze_time(datetime.date(2021, 9, 13)):
            allocation._update_accrual()

            self.assertEqual(leave.state, 'refuse', 'The leave should be refused')
