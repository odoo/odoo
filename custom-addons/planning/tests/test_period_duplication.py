# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo.addons.planning.tests.common import TestCommonPlanning


class TestPeriodDuplication(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super(TestPeriodDuplication, cls).setUpClass()
        cls.setUpEmployees()
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),  # it was a slot on Sunday...
            'end_datetime': datetime(2019, 6, 3, 17, 0),
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 4, 8, 0),
            'end_datetime': datetime(2019, 6, 5, 17, 0),
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),
            'end_datetime': datetime(2019, 6, 3, 17, 0),
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2019, 6, 6, 17, 0, 0),
            'repeat_interval': 1,
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_joseph.id,
            'start_datetime': datetime(2020, 10, 19, 6, 0),
            'end_datetime': datetime(2020, 10, 19, 15, 0),
        })

    def test_dont_duplicate_recurring_slots(self):
        """Original week :  6/2/2019 -> 6/8/2019
           Destination week : 6/9/2019 -> 6/15/2019
            slots:
                6/2/2019 08:00 -> 6/2/2019 17:00
                6/4/2019 08:00 -> 6/5/2019 17:00
                6/3/2019 08:00 -> 6/3/2019 17:00 --> this one should be recurrent therefore not duplicated
        """
        employee = self.employee_bert

        self.assertEqual(len(self.get_by_employee(employee)), 3)
        self.assertEqual(sum(self.get_by_employee(employee).mapped('allocated_hours')), 16.0 + 8.0 + 8.0, 'duplicate has only duplicated slots that fit entirely in the period')

        self.env['planning.slot'].action_copy_previous_week('2019-06-09 00:00:00', [['start_datetime', '<=', '2020-04-04 21:59:59'], ['end_datetime', '>=', '2020-03-28 23:00:00']])

        self.assertEqual(len(self.get_by_employee(employee)), 5, 'duplicate has only duplicated slots that fit entirely in the period')

        duplicated_slots = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>', datetime(2019, 6, 9, 0, 0)),
            ('end_datetime', '<', datetime(2019, 6, 15, 23, 59)),
        ])
        self.assertEqual(len(duplicated_slots), 2, 'duplicate has only duplicated slots that fit entirely in the period')

        self.assertEqual(sum(self.get_by_employee(employee).mapped('allocated_hours')), 16.0 + 8.0 + 8.0 + 16.0 + 8.0, 'duplicate has only duplicated slots that fit entirely in the period')

    def test_duplication_should_preserve_local_time(self):
        """Original week: 10/19/2020 -> 10/23/2020
           Destination week: 10/26/2020 -> 10/30/2020
           Timezone: Europe/Brussels
            slots:
                10/19/2020 08:00 (CEST) -> 10/19/2020 17:00

           After copy, we need to have a slot on Monday 10/26 with the same time
                10/19/2020 08:00 (CET) -> 10/19/2020 17:00
        """
        employee = self.employee_joseph
        employee.tz = 'Europe/Brussels'
        self.env['planning.slot'].action_copy_previous_week('2020-10-26 00:00:00', [['start_datetime', '<=', '2020-10-25 23:59:59'], ['end_datetime', '>=', '2020-10-18 00:00:00']])

        duplicated_slots = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 26, 0, 0)),
            ('end_datetime', '<', datetime(2020, 10, 30, 23, 59)),
        ])
        self.assertEqual(1, len(duplicated_slots), 'one slot duplicated')
        self.assertEqual('2020-10-26 07:00:00', str(duplicated_slots[0].start_datetime),
                         'adjust GMT timestamp to account for DST shift')
