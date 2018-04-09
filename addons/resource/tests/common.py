# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):

    def _define_calendar(self, name, attendances, tz):
        cal = self.env['resource.calendar'].create({
            'name': name,
            'tz': tz,
            'attendance_ids': [(5, 0, 0)],
        })

        for n, att in enumerate(attendances):
            self.env['resource.calendar.attendance'].create({
                'name': '%s_%d' % (name, n),
                'calendar_id': cal.id,
                'dayofweek': str(att[2]),
                'hour_from': att[0],
                'hour_to': att[1],
            })

        return cal

    def setUp(self):
        super(TestResourceCommon, self).setUp()

        # UTC+1 winter, UTC+2 summer
        self.calendar_1 = self._define_calendar('40 Hours', [(8, 16, i) for i in range(5)], 'Europe/Brussels')
        # UTC+6
        self.calendar_2 = self._define_calendar('38 Hours', sum([((9, 12, i), (13, 17, i)) for i in range(5)], ()), 'Etc/GMT-6')
        # UTC-8 winter, UTC-7 summer
        self.calendar_3 = self._define_calendar('8+12 Hours', [(8, 16, 1), (8, 13, 4), (16, 23, 4)], 'America/Los_Angeles')

        # Employee is linked to a resource.resource via resource.mixin
        Resource = self.env['resource.test']

        self.jean = Resource.create({
            'name': 'Jean',
            'resource_calendar_id': self.calendar_1.id,
        })
        self.patel = Resource.create({
            'name': 'Patel',
            'resource_calendar_id': self.calendar_2.id,
        })
        self.john = Resource.create({
            'name': 'John',
            'resource_calendar_id': self.calendar_3.id,
        })
