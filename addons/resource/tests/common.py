# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):

    def _define_calendar(self, name, attendances, tz):
        return self.env['resource.calendar'].create({
            'name': name,
            'tz': tz,
            'attendance_ids': [
                (0, 0, {
                    'name': '%s_%d' % (name, index),
                    'hour_from': att[0],
                    'hour_to': att[1],
                    'dayofweek': str(att[2]),
                })
                for index, att in enumerate(attendances)
            ],
        })
    def _define_calendar_2_weeks(self, name, attendances, tz):
        return self.env['resource.calendar'].create({
            'name': name,
            'tz': tz,
            'two_weeks_calendar': True,
            'attendance_ids': [
                (0, 0, {
                    'name': '%s_%d' % (name, index),
                    'hour_from': att[0],
                    'hour_to': att[1],
                    'dayofweek': str(att[2]),
                    'week_type': att[3],
                    'display_type': att[4],
                    'sequence': att[5],
                })
                for index, att in enumerate(attendances)
            ],
            'two_weeks_calendar': True,
        })

    def setUp(self):
        super().setUp()
        self.env.company.resource_calendar_id.tz = "Europe/Brussels"

        # UTC+1 winter, UTC+2 summer
        self.calendar_jean = self._define_calendar('40 Hours', [(8, 16, i) for i in range(5)], 'Europe/Brussels')
        # UTC+6
        self.calendar_patel = self._define_calendar('38 Hours', sum([((9, 12, i), (13, 17, i)) for i in range(5)], ()), 'Etc/GMT-6')
        # UTC-8 winter, UTC-7 summer
        self.calendar_john = self._define_calendar('8+12 Hours', [(8, 16, 1), (8, 13, 4), (16, 23, 4)], 'America/Los_Angeles')
        # UTC+1 winter, UTC+2 summer
        self.calendar_jules = self._define_calendar_2_weeks('Week 1: 30 Hours - Week 2: 16 Hours', [
            (0, 0, 0, '0', 'line_section', 0), (8, 16, 0, '0', False, 1), (9, 17, 1, '0', False, 2),
            (0, 0, 0, '1', 'line_section', 10), (8, 16, 0, '1', False, 11), (7, 15, 2, '1', False, 12),
            (8, 16, 3, '1', False, 13), (10, 16, 4, '1', False, 14)], 'Europe/Brussels')

        self.calendar_paul = self._define_calendar('Morning and evening shifts', sum([((2, 7, i), (10, 16, i)) for i in range(5)], ()), 'Brazil/DeNoronha')

        # Employee is linked to a resource.resource via resource.mixin
        self.jean = self.env['resource.test'].create({
            'name': 'Jean',
            'resource_calendar_id': self.calendar_jean.id,
        })
        self.patel = self.env['resource.test'].create({
            'name': 'Patel',
            'resource_calendar_id': self.calendar_patel.id,
        })
        self.john = self.env['resource.test'].create({
            'name': 'John',
            'resource_calendar_id': self.calendar_john.id,
        })
        self.jules = self.env['resource.test'].create({
            'name': 'Jules',
            'resource_calendar_id': self.calendar_jules.id,
        })

        self.paul = self.env['resource.test'].create({
            'name': 'Paul',
            'resource_calendar_id': self.calendar_paul.id,
        })

        self.two_weeks_resource = self._define_calendar_2_weeks(
            'Two weeks resource',
            [
                (0, 0, 0, '0', 'line_section', 0),
                (8, 16, 0, '0', False, 1),
                (8, 16, 1, '0', False, 2),
                (8, 16, 2, '0', False, 3),
                (8, 16, 3, '0', False, 4),
                (8, 16, 4, '0', False, 5),
                (0, 0, 0, '1', 'line_section', 10),
                (8, 16, 0, '1', False, 11),
                (8, 16, 1, '1', False, 12),
                (8, 16, 2, '1', False, 13),
                (8, 16, 3, '1', False, 14),
                (8, 16, 4, '1', False, 15)
            ],
            'Europe/Brussels'
        )
