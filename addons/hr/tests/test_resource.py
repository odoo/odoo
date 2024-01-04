# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import utc

from odoo.addons.resource.models.utils import Intervals

from .common import TestHrCommon


class TestResource(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestResource, cls).setUpClass()
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.employee_niv = cls.env['hr.employee'].create({
            'name': 'Sharlene Rhodes',
            'departure_date': '2022-06-01',
            'resource_calendar_id': cls.calendar_40h.id,
        })
        cls.employee_niv_create_date = '2021-01-01 10:00:00'
        cls.env.cr.execute("UPDATE hr_employee SET create_date=%s WHERE id=%s",
                           (cls.employee_niv_create_date, cls.employee_niv.id))

    def test_calendars_validity_within_period_default(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
        )
        interval = Intervals([(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
            self.env['resource.calendar.attendance']
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[self.employee_niv.resource_id.id]), "Niv should only have one calendar")
        niv_entry = calendars[self.employee_niv.resource_id.id]
        niv_calendar = next(iter(niv_entry))
        self.assertEqual(niv_calendar, self.calendar_40h, "It should be Niv's Calendar")
        self.assertFalse(niv_entry[niv_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[niv_calendar], "Calendar validity should cover all interval")

    def test_calendars_validity_within_period_creation(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            utc.localize(datetime(2020, 12, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 1, 31, 17, 0, 0)),
        )
        interval = Intervals([(
            utc.localize(datetime(2020, 12, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 1, 31, 17, 0, 0)),
            self.env['resource.calendar.attendance']
        )])
        niv_entry = calendars[self.employee_niv.resource_id.id]
        self.assertFalse(niv_entry[self.calendar_40h] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[self.calendar_40h], "Calendar validity should cover all interval")
