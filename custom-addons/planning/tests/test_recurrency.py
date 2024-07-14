# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime, timedelta

from .common import TestCommonPlanning

import unittest
from odoo.exceptions import UserError
from odoo.tests import Form


class TestRecurrencySlotGeneration(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super(TestRecurrencySlotGeneration, cls).setUpClass()
        cls.setUpEmployees()

    def configure_recurrency_span(self, span_qty):
        self.env.company.write({
            'planning_generation_interval': span_qty,
        })

    # ---------------------------------------------------------
    # Repeat "until" mode
    # ---------------------------------------------------------

    def test_repeat_until(self):
        """ Normal case: Test slots get repeated at the right time with company limit
            Soft limit should be the earliest between `(now + planning_generation_interval)` and `repeat_until`
            In this case, task repeats forever so soft limit is `(now + planning_generation_interval)`
            planning_generation_interval: 1 month

            first run:
                now :                   2019-06-27
                initial_start :         2019-06-27
                generated slots:
                                        2019-06-27
                                        2019-07-4
                                        2019-07-11
                                        2019-07-18
                                        2019-07-25
                                        NOT 2019-08-01 because it hits the soft limit
            1st cron
                now :                   2019-07-11  2 weeks later
                last generated start :  2019-07-25
                repeat_until :          2022-06-27
                generated_slots:
                                        2019-08-01
                                        2019-08-08
                                        NOT 2019-08-15 because it hits the soft limit
        """
        with self._patch_now('2019-06-27 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            # since repeat span is 1 month, we should have 5 slots
            slot = self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 1,
            })
            generated_slots = self.get_by_employee(self.employee_joseph)
            first_generated_slots_dates = set(map(lambda slot: slot.start_datetime, generated_slots))
            expected_slot_dates = {
                datetime(2019, 6, 27, 8, 0, 0),
                datetime(2019, 7, 4, 8, 0, 0),
                datetime(2019, 7, 11, 8, 0, 0),
                datetime(2019, 7, 18, 8, 0, 0),
                datetime(2019, 7, 25, 8, 0, 0),
            }
            self.assertTrue(first_generated_slots_dates == expected_slot_dates, 'Initial run should have created expected slots')
            # TODO JEM: check same employee, attached to same reccurrence, same role, ...

            slot.write({
                'repeat_unit': 'week',
                'repeat_type': 'until',
                'repeat_until': datetime(2019, 9, 27, 15, 0, 0),
            })
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'The slot count for recurring shift who have repeat type until should be 5')

        # now run cron two weeks later, should yield two more slots
        # because the repeat_interval is 1 week
        with self._patch_now('2019-07-11 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            generated_slots = self.get_by_employee(self.employee_joseph)
            all_slots_dates = set(map(lambda slot: slot.start_datetime, generated_slots))
            new_expected_slots_dates = expected_slot_dates | {
                datetime(2019, 8, 1, 8, 0, 0),
                datetime(2019, 8, 8, 8, 0, 0),
            }
            self.assertTrue(all_slots_dates == new_expected_slots_dates, 'first cron run should have generated 2 more slots')

    def test_repeat_until_no_repeat(self):
        """create a recurrency with repeat until set which is less than next cron span, should
            stop repeating upon creation
            company_span:               1 month
            first run:
                now :                   2019-6-27
                initial_start :         2019-6-27
                repeat_until :          2019-6-29  
                generated slots:
                                        2019-6-27
                                        NOT 2019-7-4 because it's after the recurrency's repeat_until
        """
        with self._patch_now('2019-06-27 08:00:00'):

            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_interval': 1,
                'repeat_until': datetime(2019, 6, 29, 8, 0, 0),
            })

            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 1, 'first run should only have created 1 slot since repeat until is set at 1 week')

    def test_repeat_until_cron_idempotent(self):
        """Create a recurrency with repeat_until set, it allows a full first run, but not on next cron
            first run:
                now :                   2019-06-27
                initial_start :         2019-06-27
                repeat_end :            2019-07-10  recurrency's repeat_until
                generated slots:
                                        2019-06-27
                                        2019-07-4
                                        NOT 2019-07-11 because it hits the recurrency's repeat_until
            first cron:
                now:                    2019-07-12
                last generated start:   2019-07-4
                repeat_end:             2019-07-10  still recurrency's repeat_until
                generated slots:
                                        NOT 2019-07-11 because it still hits the repeat end
        """
        with self._patch_now('2019-06-27 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            # repeat until is big enough for the first pass to generate all 2 slots
            self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_interval': 1,
                'repeat_until': datetime(2019, 7, 10, 8, 0, 0),
            })
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 2, 'initial run should have generated 2 slots')

            # run the cron, since last generated slot is less than one week (one week being the repeat_interval) before repeat_until, the next
            # slots would be after repeat_until, so none will be generated.
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 2, 'running the cron right after should not generate new slots')

    def test_repeat_until_cron_generation(self):
        """Generate a recurrence with repeat_until that allows first run, then first cron.
            Check that if a cron is triggered, it doesn't generate more slots (since the date limit
            in generated slots has been reached).
            first run:
                now :                   2019-8-31
                initial_start :         2019-9-1
                repeat_end :            forever
                generated slots:
                                        2019-9-1
                                        2019-9-8
                                        2019-9-15
                                        2019-9-22
                                        2019-9-29
            first cron:
                now:                    2019-9-14  two weeks later
                repeat_end:             forever
                generated slots:
                                        2019-10-6
                                        2019-10-13
            second cron:
                now:                    2019-9-16  two days later
                last generated start:   2019-10-13
                repeat_end:             forever
                generated slots:
                                        NOT 2019-10-20 because all recurring slots are already generated in the company interval
        """
        with self._patch_now('2019-08-31 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            # first run, 5 slots generated (all the slots for one month, one month being the planning_generation_interval)
            self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 9, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 9, 1, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 1,
                'repeat_until': False,
            })
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'first run should have generated 5 slots')
        # run the cron, since last generated slot do not hit the soft limit, there will be 2 more
        with self._patch_now('2019-09-14 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 7, 'first cron should have generated 2 more slots')
        # run the cron again, since last generated slot do hit the soft limit, there won't be more
        with self._patch_now('2019-09-16 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 7, 'second cron should not generate any slots')

    def test_repeat_until_long_limit(self):
        """Since the recurrency cron is meant to run every week, make sure generation works accordingly when
            the company's repeat span is much larger
            first run:
                now :                   2019-6-1
                initial_start :         2019-6-1
                repeat_end :            2019-12-1  initial_start + 6 months
                generated slots:
                                        2019-6-1
                                        ...
                                        2019-11-30  (27 items)
            first cron:
                now:                    2019-6-8
                last generated start    2019-11-30
                repeat_end              2019-12-8
                generated slots:
                                        2019-12-7
            only one slot generated: since we are one week later, repeat_end is only one week later and slots are generated every week.
            So there is just enough room for one.
            This ensure slots are always generated up to x time in advance with x being the company's repeat span
        """
        with self._patch_now('2019-06-01 08:00:00'):
            self.configure_recurrency_span(6)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 1, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_interval': 1,
                'repeat_until': datetime(2020, 7, 25, 8, 0, 0),
            })
            # over 6 month, we should have generated 27 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 27, 'first run has generated 27 slots')
        # one week later, always having the slots generated 6 months in advance means we
        # have generated one more, which makes 28
        with self._patch_now('2019-06-08 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 28, 'second cron should only generate 1 more slot')

    def test_repat_until_cancel_repeat(self):
        with self._patch_now('2019-06-27 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            # since repeat span is 1 month, we should have 5 slots
            planning_slot = self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_interval': 1,
                'repeat_until': datetime(2019, 6, 29, 8, 0, 0),
            })
            planning_slot_form = Form(planning_slot)
            planning_slot_form.repeat = False
            planning_slot_form.save()
            self.assertFalse(planning_slot.repeat)

    def test_repeat_forever(self):
        """ Since the recurrency cron is meant to run every week, make sure generation works accordingly when
            both the company's repeat span and the repeat interval are much larger
            Company's span is 6 months and repeat_interval is 4 weeks
            first run:
                now :                   2019-5-16
                initial_start :         2019-6-1
                repeat_end :            2019-11-16  now + 6 months
                generated slots:
                                        2019-6-1
                                        2019-6-29
                                        2019-7-27
                                        2019-8-24
                                        2019-9-21
                                        2019-10-19
            first cron:
                now:                    2019-5-24
                last generated start    2019-10-19
                repeat_end              2019-11-24
                generated slots:
                                        2019-11-16
            second cron:
                now:                    2019-5-31
                last generated start    2019-11-16
                repeat_end              2019-12-01
                generated slots:
                                        N/A (we are still 6 months in advance)
        """
        with self._patch_now('2019-05-16 08:00:00'):
            self.configure_recurrency_span(6)

            self.assertFalse(self.get_by_employee(self.employee_joseph))

            self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 1, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 4,
            })

            # over 6 months (which spans 26 weeks), we should have generated 6 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 6, 'first run should generate 7 slots')

        # one week later, always having the slots generated 6 months in advance means we
        # have generated one more, which makes 8
        with self._patch_now('2019-05-24 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 7, 'first cron should generate one more slot')

        # again one week later, we are now up-to-date so there should still be 8 slots
        with self._patch_now('2019-05-31 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 7, 'second run should not generate any slots')

    def test_number_of_repetitions(self):
        """ Since the recurrency cron is meant to run every week, make sure generation works accordingly when
            both the company's repeat span and the repeat interval are much larger
            Company's span is 1 month and repeat_interval is 1 week

            Test Case:
            ---------
            First Automated Run:
                now :                   2020-4-20
                initial_start :         2020-4-20
                repeat_end :            2020-05-25  now + 1 month
                generated slots:
                                        2020-4-20
                                        2020-4-27
                                        2020-5-04
                                        2020-5-11
                                        2020-5-18
            First Cron:
                now:                    2020-4-27
                last generated start    2020-5-18
                repeat_end              2020-05-25
                generated slots:
                                        2020-05-25
            Second Cron:
                now:                    2020-5-4
                last generated start    2020-05-25
                repeat_end              2020-05-25
                generated slots:
        """
        with self._patch_now('2020-04-20 08:00:00'):
            self.configure_recurrency_span(1)

            self.env['planning.slot'].create({
                'start_datetime': datetime(2020, 4, 20, 8, 0, 0),
                'end_datetime': datetime(2020, 4, 20, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_interval': 1,
                'repeat_type': 'x_times',
                'repeat_number': 6,
            })

            # we should have generated 5 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'first run should generated 5 slots')

        # one week later, always having the slots generated 1 month in advance means we have generated one more, which makes 6
        with self._patch_now('2020-04-27 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 6, 'first cron should generate one more slot')

        # again one week later, we are now up-to-date so there should still be 6 slots
        with self._patch_now('2020-05-04 08:00:00'):
            self.env['planning.recurrency']._cron_schedule_next()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 6, 'second run should not generate any slots')

    @unittest.skip
    def kkktest_slot_remove_all(self):
        with self._patch_now('2019-06-01 08:00:00'):
            self.configure_recurrency_span(6)
            initial_start_dt = datetime(2019, 6, 1, 8, 0, 0)
            initial_end_dt = datetime(2019, 6, 1, 17, 0, 0)
            slot_values = {
                'resource_id': self.resource_joseph.id,
            }

            recurrency = self.env['planning.recurrency'].create({
                'repeat_interval': 1,
            })
            self.assertFalse(self.get_by_employee(self.employee_joseph))
            recurrency.create_slot(initial_start_dt, initial_end_dt, slot_values)

            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 27, 'first run has generated 27 slots')
            recurrency.action_remove_all()
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 0, 'calling remove after on any slot from the recurrency remove all slots linked to the recurrency')

    def test_recurrency_interval_type(self):
        """ Since the recurrency cron is meant to run every week, make sure generation works accordingly when
            both the company's repeat span and the repeat interval are much larger
            Company's span is 12 month and repeat_interval is 1 and repeat_unit are day/week/month/year
            Test Case:
            ---------
                - create slot with repeat_unit set as day
                - delete extra slots except original one
                - update repeat_unit to week and repeat_until according slots we need to generate
                - delete extra slots except original one
                - date repeat_unit to month and repeat_until according slots we need to generate
                - delete extra slots except original one
                - update repeat_unit to year and repeat_until according slots we need to generates
        """

        with self._patch_now('2020-04-20 08:00:00'):
            self.configure_recurrency_span(12)

            slot = self.env['planning.slot'].create({
                        'start_datetime': datetime(2020, 4, 20, 8, 0, 0),
                        'end_datetime': datetime(2020, 4, 20, 17, 0, 0),
                        'resource_id': self.resource_joseph.id,
                        'repeat': True,
                        'repeat_interval': 1,
                        'repeat_unit': 'day',
                        'repeat_type': 'until',
                        'repeat_until': datetime(2020, 4, 24, 8, 0, 0),
                    })

            # generated 5 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'first run should generated 5 slots')

            def _modify_slot(repeat_unit, repeat_until):
                slot.write({
                    'repeat_unit': repeat_unit,
                    'repeat_until': repeat_until,
                })

            _modify_slot('week', datetime(2020, 5, 11, 8, 0, 0)) # generated 4 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 4, 'After change unit to week generated slots should be 4')

            _modify_slot('month', datetime(2020, 8, 31, 8, 0, 0)) # generated 5 slots
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'After change unit to month generated slots should be 5')

            _modify_slot('year', datetime(2020, 4, 26, 8, 0, 0)) # generated 1 slot
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 1, 'After change unit to year generated slots should be 1')

    # ---------------------------------------------------------
    # Recurring Slot Misc
    # ---------------------------------------------------------

    def test_recurring_slot_company(self):
        with self._patch_now('2019-06-01 08:00:00'):
            initial_company = self.env['res.company'].create({'name': 'original'})
            initial_company.write({
                'planning_generation_interval': 2,
            })
            # Should be able to create a slot with a company_id != employee.company_id
            slot1 = self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 1, 17, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 1,
                'company_id': initial_company.id,
            })

            # put the employee in the second company
            self.employee_bert.write({'company_id': initial_company.id})

            slot1 = self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 1, 17, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 1,
                'company_id': initial_company.id,
            })

            other_company = self.env['res.company'].create({'name': 'other'})
            other_company.write({
                'planning_generation_interval': 1,
            })
            self.employee_joseph.write({'company_id': other_company.id})
            slot2 = self.env['planning.slot'].create({
                'start_datetime': datetime(2019, 6, 1, 8, 0, 0),
                'end_datetime': datetime(2019, 6, 1, 17, 0, 0),
                'resource_id': self.resource_joseph.id,
                'repeat': True,
                'repeat_type': 'forever',
                'repeat_interval': 1,
                'company_id': other_company.id,
            })

            # initial company's recurrency should have created 9 slots since it's span is two month
            # other company's recurrency should have create 5 slots since it's span is one month
            self.assertEqual(len(self.get_by_employee(self.employee_bert)), 10, 'There will be a 10 slots because becuase other companys slot will become open slots')
            self.assertEqual(len(self.get_by_employee(self.employee_joseph)), 5, 'other company\'s span is one month, so only 5 slots')

            self.assertEqual(slot1.company_id, slot1.recurrency_id.company_id, "Recurrence and slots (1) must have the same company")
            self.assertEqual(slot1.recurrency_id.company_id, slot1.recurrency_id.slot_ids.mapped('company_id'), "All slots in the same recurrence (1) must have the same company")
            self.assertEqual(slot2.company_id, slot2.recurrency_id.company_id, "Recurrence and slots (2) must have the same company")
            self.assertEqual(slot2.recurrency_id.company_id, slot2.recurrency_id.slot_ids.mapped('company_id'), "All slots in the same recurrence (1) must have the same company")

    def test_empty_recurrency(self):
        """ Check empty recurrency is removed by cron """
        with self._patch_now('2020-06-27 08:00:00'):
            # insert empty recurrency
            empty_recurrency_id = self.env['planning.recurrency'].create({
                'repeat_interval': 1,
                'repeat_type': 'forever',
                'repeat_until': False,
                'last_generated_end_datetime': datetime(2019, 6, 27, 8, 0, 0)
            }).id

            self.assertEqual(len(list(filter(lambda recu: recu.id == empty_recurrency_id, self.env['planning.recurrency'].search([])))), 1, "the empty recurrency we created should be in the db")
            self.env['planning.recurrency']._cron_schedule_next()
            # cron with no slot gets deleted (there is no original slot to copy from)
            self.assertEqual(len(list(filter(lambda recu: recu.id == empty_recurrency_id, self.env['planning.recurrency'].search([])))), 0, 'the empty recurrency we created should not be in the db anymore')
            recurrencies = self.env['planning.recurrency'].search([])
            self.assertFalse(len(list(filter(lambda recu: len(recu.slot_ids) == 0, recurrencies))), 'cron with no slot gets deleted (there is no original slot to copy from)')

    def test_recurrency_change_date(self):
        with self._patch_now('2020-01-01 08:00:00'):
            slot = self.env['planning.slot'].create({
                'start_datetime': datetime(2020, 1, 1, 8, 0, 0),
                'end_datetime': datetime(2020, 1, 1, 17, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2020, 2, 29, 17, 0, 0),
                'repeat_interval': 1,
                'repeat_unit': 'week',
            })
            self.assertEqual(len(self.get_by_employee(self.employee_bert)), 9, 'There are 9 weeks between start_datetime and repeat_until')

            slot.update({'repeat_type': 'forever'})
            self.assertEqual(slot.recurrency_id.repeat_until, False, 'Repeat forever should not have a date')
            self.assertEqual(len(self.get_by_employee(self.employee_bert)), 26, 'There are 26 weeks in 6 months (max duration of shift generation)')

    def test_recurrency_past(self):
        with self._patch_now('2020-01-01 08:00:00'):
            with self.assertRaises(UserError):
                slot = self.env['planning.slot'].create({
                    'start_datetime': datetime(2020, 1, 1, 8, 0, 0),
                    'end_datetime': datetime(2020, 1, 1, 17, 0, 0),
                    'resource_id': self.resource_joseph.id,
                    'repeat': True,
                    'repeat_type': 'until',
                    'repeat_until': datetime(2019, 12, 25, 17, 0, 0),
                    'repeat_interval': 1,
                })

    def test_recurrency_timezone(self):
        """
        We need to calculate the recurrency in the user's timezone
        (this is important if repeating a slot beyond a dst boundary - we need to keep the same (local) time)

            company_span:           1 week
                now :                   10/20/2020
                initial_start :         10/20/2020 08:00 CEST (06:00 GMT)
                repeat_end :            far away
                generated slots:
                                        10/20/2020 08:00 CEST
                                        10/27/2020 08:00 CET (07:00 GMT)
        """
        # with self._patch_now('2019-01-01 08:00:00'):
        #     self.configure_recurrency_span(1)
        with self._patch_now('2020-10-19 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_bert))

            self.env.user.tz = 'Europe/Brussels'
            slot = self.env['planning.slot'].create({
                'start_datetime': datetime(2020, 10, 20, 6, 0, 0),
                'end_datetime': datetime(2020, 10, 20, 15, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2022, 6, 27, 15, 0, 0),
                'repeat_interval': 1,
            })
            slots = self.get_by_employee(self.employee_bert).sorted('start_datetime')
            self.assertEqual('2020-10-20 06:00:00', str(slots[0].start_datetime))
            self.assertEqual('2020-10-27 07:00:00', str(slots[1].start_datetime))

    def test_recurrency_timezone_at_dst(self):
        """
        Check we don't crash if we try to recur ON the DST boundary
        (because 02:30 happens twice on 10/25/20:
         - 10/25/2020 00:30 GMT is 02:30 CEST,
         - 10/25/2020 01:30 GMT is 02:30 CET)

            company_span:           1 week
                now :                   10/17/2020
                initial_start :         10/25/2020 02:30 CEST (00:30 GMT)
                repeat_end :            far away
                generated slots:
                                        10/25/2020 02:30 CEST (00:30 GMT)
                                        11/01/2020 02:30 CET (01:30 GMT)
        """
        # with self._patch_now('2019-01-01 08:00:00'):
        #     self.configure_recurrency_span(1)
        with self._patch_now('2020-10-17 08:00:00'):
            self.configure_recurrency_span(1)

            self.assertFalse(self.get_by_employee(self.employee_bert))

            self.env.user.tz = 'Europe/Brussels'
            slot = self.env['planning.slot'].create({
                'start_datetime': datetime(2020, 10, 25, 0, 30, 0),
                'end_datetime': datetime(2020, 10, 25, 9, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2022, 6, 27, 15, 0, 0),
                'repeat_interval': 1,
            })
            slots = self.get_by_employee(self.employee_bert).sorted('start_datetime')
            self.assertEqual('2020-10-25 00:30:00', str(slots[0].start_datetime))
            self.assertEqual('2020-11-01 01:30:00', str(slots[1].start_datetime))

    def test_recurrence_update(self):
        with self._patch_now('2020-10-17 08:00:00'):
            self.configure_recurrency_span(1)
            slot = self.env['planning.slot'].create({
                'name': 'coucou',
                'start_datetime': datetime(2020, 10, 25, 0, 30, 0),
                'end_datetime': datetime(2020, 10, 25, 9, 0, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2020, 12, 25, 0, 0, 0),
                'repeat_interval': 1,
            })

        all_slots = slot.recurrency_id.slot_ids
        other_slots = all_slots - slot

        slot.write({
            'name': 'cuicui',
        })
        self.assertEqual(slot.name, 'cuicui', 'This slot should be modified')
        self.assertTrue(all(slot.name == 'coucou' for slot in other_slots), 'Other slots should not be modified')

        slot.write({
            'name': 'cuicui',
            'recurrence_update': 'all',
        })
        self.assertTrue(all(slot.name == 'cuicui' for slot in all_slots), 'All slots should be modified')

        other_slots[0].write({
            'name': 'coucou',
            'recurrence_update': 'subsequent',
        })
        self.assertEqual(slot.name, 'cuicui', 'This slot should not be modified')
        self.assertTrue(all(slot.name == 'coucou' for slot in other_slots), 'Other slots should be modified')

    def test_recurrence_with_already_planned_shift(self):
        with self._patch_now('2020-01-01 08:00:00'):
            PlanningSlot = self.env['planning.slot']
            dummy, slot = PlanningSlot.create([{
                'start_datetime': datetime(2020, 1, 8, 8, 0),
                'end_datetime': datetime(2020, 1, 8, 17, 0),
                'resource_id': self.resource_bert.id,
            }, {
                'start_datetime': datetime(2020, 1, 6, 8, 0),
                'end_datetime': datetime(2020, 1, 6, 17, 0),
                'resource_id': self.resource_bert.id,
                'repeat': True,
                'repeat_unit': 'day',
                'repeat_type': 'until',
                'repeat_until': datetime(2020, 1, 10, 15, 0),
                'repeat_interval': 1,
            }])

            open_shift_count = PlanningSlot.search_count([('resource_id', '=', False), ('recurrency_id', '=', slot.recurrency_id.id)])
            self.assertEqual(open_shift_count, 1, 'Open shift should be created instead of recurring shift if resource already has a shift planned')
            self.assertEqual(len(self.get_by_employee(self.employee_bert)), 5, 'There should be 5 shifts: 1 already planned shift and 4 recurring shifts')

    def test_recurrency_last_day_of_month(self):
        self.configure_recurrency_span(1)
        self.env.user.tz = 'UTC'
        slot = self.env['planning.slot'].create({
            'name': 'coucou',
            'start_datetime': datetime(2020, 1, 31, 8, 0),
            'end_datetime': datetime(2020, 1, 31, 9, 0),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2020, 6, 1, 0, 0),
            'repeat_interval': 1,
            'repeat_unit': 'month',
        })
        self.assertEqual(
            slot.recurrency_id.slot_ids.mapped('start_datetime'),
            [
                datetime(2020, 1, 31, 8, 0),
                datetime(2020, 2, 29, 8, 0),
                datetime(2020, 3, 31, 8, 0),
                datetime(2020, 4, 30, 8, 0),
                datetime(2020, 5, 31, 8, 0),
            ],
            'The slots should occur at the last day of each month'
        )

    def test_recurrency_occurring_slots(self):
        self.configure_recurrency_span(1)
        self.env.user.tz = 'UTC'
        slot = self.env['planning.slot'].create([{
            'name': 'coucou',
            'start_datetime': datetime(2020, 1, 31, 8, 0),
            'end_datetime': datetime(2020, 1, 31, 9, 0),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'x_times',
            'repeat_number': 2,
            'repeat_interval': 1,
            'repeat_unit': 'month',
        }, {
            'name': 'concurrent slot',
            'start_datetime': datetime(2020, 2, 29, 8, 0),
            'end_datetime': datetime(2020, 2, 29, 11, 0),
            'resource_id': self.resource_bert.id,
        }])

        self.assertFalse(
            slot.recurrency_id.slot_ids[1].resource_id,
            'The second slot should be an open shift as the resource has a concurrent shift'
        )

    def test_recurrency_date_change_week(self):
        first_slot_dt = datetime(2020, 11, 27)
        first_slot = self.env['planning.slot'].create({
            'start_datetime': first_slot_dt + timedelta(hours=8),
            'end_datetime': first_slot_dt + timedelta(hours=9),
            'repeat': True,
            'repeat_type': 'x_times',
            'repeat_number': 3,
            'repeat_interval': 1,
            'repeat_unit': 'week',
        })
        first_slot.recurrency_id.slot_ids[1].write({
            'start_datetime': first_slot_dt + timedelta(days=9, hours=8),
            'end_datetime': first_slot_dt + timedelta(days=9, hours=9),
        })
        first_slot.write({
            'start_datetime': first_slot_dt + timedelta(days=-1, hours=8),
            'end_datetime': first_slot_dt + timedelta(days=-1, hours=9),
            'recurrence_update': 'all',
        })
        self.assertTrue(
            slot.start_datetime.weekday() == 1
            for slot in first_slot.recurrency_id.slot_ids
        )

    def test_recurrency_date_change_month(self):
        first_slot_dt = datetime(2020, 11, 27)
        first_slot = self.env['planning.slot'].create({
            'start_datetime': first_slot_dt + timedelta(hours=8),
            'end_datetime': first_slot_dt + timedelta(hours=9),
            'repeat': True,
            'repeat_type': 'x_times',
            'repeat_number': 3,
            'repeat_interval': 1,
            'repeat_unit': 'month',
        })
        first_slot.recurrency_id.slot_ids[1].write({
            'start_datetime': first_slot_dt + timedelta(days=2, hours=8),
            'end_datetime': first_slot_dt + timedelta(days=2, hours=9),
        })
        first_slot.write({
            'start_datetime': first_slot_dt + timedelta(days=-10, hours=8),
            'end_datetime': first_slot_dt + timedelta(days=-10, hours=9),
            'recurrence_update': 'all',
        })
        self.assertTrue(
            slot.start_datetime.day == 17 and slot._get_slot_duration() == 1
            for slot in first_slot.recurrency_id.slot_ids
        )
