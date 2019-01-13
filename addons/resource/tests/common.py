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

    def setUp(self):
        super(TestResourceCommon, self).setUp()

        # UTC+1 winter, UTC+2 summer
        self.calendar_jean = self._define_calendar('40 Hours', [(8, 16, i) for i in range(5)], 'Europe/Brussels')
        # UTC+6
        self.calendar_patel = self._define_calendar('38 Hours', sum([((9, 12, i), (13, 17, i)) for i in range(5)], ()), 'Etc/GMT-6')
        # UTC-8 winter, UTC-7 summer
        self.calendar_john = self._define_calendar('8+12 Hours', [(8, 16, 1), (8, 13, 4), (16, 23, 4)], 'America/Los_Angeles')

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
