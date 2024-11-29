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

    def test_availability_hr_infos_resource(self):
        """ Ensure that all the hr infos needed to display the avatar popover card
            are available on the model resource.resource, even if the employee is archived
        """
        user = self.env['res.users'].create([{
            'name': 'Test user',
            'login': 'test',
            'email': 'test@odoo.perso',
            'phone': '+32488990011',
        }])
        department = self.env['hr.department'].create([{
            'name': 'QA',
        }])
        resource = self.env['resource.resource'].create([{
            'name': 'Test resource',
            'user_id': user.id,
        }])
        employee = self.env['hr.employee'].create([{
            'name': 'Test employee',
            'active': False,
            'user_id': user.id,
            'job_title': 'Tester',
            'department_id': department.id,
            'work_email': 'test@odoo.pro',
            'work_phone': '+32800100100',
            'resource_id': resource.id,
        }])
        for field in 'email', 'phone', 'im_status':
            self.assertEqual(resource[field], user[field])
        for field in 'job_title', 'department_id', 'work_email', 'work_phone', 'show_hr_icon_display', 'hr_icon_display':
            self.assertEqual(resource[field], employee[field])
