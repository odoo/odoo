# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):

    @classmethod
    def _define_calendar(cls, name, attendances, tz):
        return cls.env['resource.calendar'].create({
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

    @classmethod
    def _define_calendar_2_weeks(cls, name, attendances, tz):
        return cls.env['resource.calendar'].create({
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
        })

    @classmethod
    def setUpClass(cls):
        super(TestResourceCommon, cls).setUpClass()

        # UTC+1 winter, UTC+2 summer
        cls.calendar_jean = cls._define_calendar('40 Hours', [(8, 16, i) for i in range(5)], 'Europe/Brussels')
        # UTC+6
        cls.calendar_patel = cls._define_calendar('38 Hours', sum([((9, 12, i), (13, 17, i)) for i in range(5)], ()), 'Etc/GMT-6')
        # UTC-8 winter, UTC-7 summer
        cls.calendar_john = cls._define_calendar('8+12 Hours', [(8, 16, 1), (8, 13, 4), (16, 23, 4)], 'America/Los_Angeles')
        # UTC+1 winter, UTC+2 summer
        cls.calendar_jules = cls._define_calendar_2_weeks('Week 1: 30 Hours - Week 2: 16 Hours', [
            (0, 0, 0, '0', 'line_section', 0), (8, 16, 0, '0', False, 1), (9, 17, 1, '0', False, 2),
            (0, 0, 0, '1', 'line_section', 10), (8, 16, 0, '1', False, 11), (7, 15, 2, '1', False, 12),
            (8, 16, 3, '1', False, 13), (10, 16, 4, '1', False, 14)], 'Europe/Brussels')

        cls.calendar_paul = cls._define_calendar('Morning and evening shifts', sum([((2, 7, i), (10, 16, i)) for i in range(5)], ()), 'Brazil/DeNoronha')

        # Employee is linked to a resource.resource via resource.mixin
        cls.jean = cls.env['resource.test'].create({
            'name': 'Jean',
            'resource_calendar_id': cls.calendar_jean.id,
        })
        cls.patel = cls.env['resource.test'].create({
            'name': 'Patel',
            'resource_calendar_id': cls.calendar_patel.id,
        })
        cls.john = cls.env['resource.test'].create({
            'name': 'John',
            'resource_calendar_id': cls.calendar_john.id,
        })
        cls.jules = cls.env['resource.test'].create({
            'name': 'Jules',
            'resource_calendar_id': cls.calendar_jules.id,
        })

        cls.paul = cls.env['resource.test'].create({
            'name': 'Paul',
            'resource_calendar_id': cls.calendar_paul.id,
        })

        cls.two_weeks_resource = cls._define_calendar_2_weeks(
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
