# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time

from odoo.tests import HttpCase, tagged

from odoo import fields
from .common import TestCommonPlanning

@tagged('post_install', '-at_install')
class TestControllersRoute(HttpCase, TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.cr, 'now', fields.datetime.now)
        with freeze_time('2023-6-1'):
            cls.setUpEmployees()

        calendar_bert = cls.env['resource.calendar'].create({
            'name': 'Calendar 2',
            'tz': 'UTC',
            'hours_per_day': 4,
            'attendance_ids': [
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'morning'}),
            ],
        })

        role_a = cls.env['planning.role'].create({'name': 'role a'})

        cls.employee_bert.resource_calendar_id = calendar_bert
        cls.resource_bert.write({'default_role_id': role_a})
        cls.slots = cls.env['planning.slot'].create([
            {
                'resource_id': cls.resource_bert.id,
                'resource_type': 'user',
                'start_datetime': datetime(2023, 6, 2, 8, 0),
                'end_datetime': datetime(2023, 6, 2, 17, 0),
            },
            {
                'resource_id': cls.resource_bert.id,
                'resource_type': 'user',
                'start_datetime': datetime(2023, 6, 3, 8, 0),
                'end_datetime': datetime(2023, 6, 3, 17, 0),
            },
            {
                'resource_id': cls.resource_bert.id,
                'resource_type': 'user',
                'start_datetime': datetime(2023, 6, 4, 8, 0),
                'end_datetime': datetime(2023, 6, 4, 17, 0),
            },
        ])

    def test_slot_ics_file_and_google_cal_url(self):

        url_res = self.slots[0]._get_slot_resource_urls()
        self.authenticate(None, None)
        ics_request = self.url_open(url_res['iCal'])
        self.assertEqual(ics_request.status_code, 200, "Response should = OK")
        decoded_content = ics_request.content.decode('utf-8')
        self.assertIn("DTSTART:20230602T080000Z", decoded_content, "The starting date of the shift should be in the ics file")
        self.assertIn("DTEND:20230602T170000Z", decoded_content, "The ending date of the shift should be in the ics file")
        self.assertIn("SUMMARY:role", decoded_content, "The summary of the ics file should contain the name of the employee and it's default role")
        self.assertIn("Role: role a", decoded_content, "The description of the ics file should contain the role of the employee")

        google_calendar_url = url_res['google_url']
        self.assertIn("dates=20230602T100000%2F20230602T190000", google_calendar_url, "The starting date of the shift should be in the google calendar url")
        self.assertIn("text=role+a", google_calendar_url, "The name of the employee and it's default role should be in the google calendar url title")

    def test_planning_ics_file(self):

        self.slots.action_planning_publish_and_send()
        start, end = min(self.slots.mapped('start_datetime')), max(self.slots.mapped('end_datetime'))
        planning_published = self.env['planning.planning'].search([
            ('start_datetime', "=", start),
            ('end_datetime', "=", end)
        ])
        url_plan = self.employee_bert._planning_get_url(planning_published)[self.employee_bert.id]
        req = self.url_open(url_plan+ ".ics")

        self.assertEqual(req.status_code, 200, "Response should = OK")
        decoded_content = req.content.decode('utf-8')
        self.assertEqual(decoded_content.count('BEGIN:VEVENT'), 3, "There should be 3 Calendar events present in the ics file")

    def test_planning_ics_file_without_assigned_employee(self):
        """
        Test that the planning ICS file can be generated when no employee is assigned.
        This ensures that a fallback timezone (current user's or UTC) is used
        when `resource_id` is not set on the slot.
        """
        self.slots[0].write({'resource_id': False})
        url_res = self.slots[0]._get_slot_resource_urls()
        self.authenticate(None, None)

        # open the ICS file
        ics_request = self.url_open(url_res['iCal'])
        self.assertEqual(ics_request.status_code, 200, "ICS export should return HTTP 200 OK")
        decoded_content = ics_request.content.decode('utf-8')

        self.assertIn("DTSTART:20230602T080000Z", decoded_content, "The starting date of the shift should be in the ics file")
        self.assertIn("DTEND:20230602T170000Z", decoded_content, "The ending date of the shift should be in the ics file")
        self.assertIn("SUMMARY:role", decoded_content, "The summary of the ics file should contain the name of the employee and it's default role")
        self.assertIn("Role: role a", decoded_content, "The description of the ics file should contain the role of the employee")
