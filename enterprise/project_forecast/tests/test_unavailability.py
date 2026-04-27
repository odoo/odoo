# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import date, datetime
import pytz

from odoo import fields

from .common import TestCommonForecast


class TestUnavailabilityForForecasts(TestCommonForecast):

    @classmethod
    def setUpClass(cls):
        super(TestUnavailabilityForForecasts, cls).setUpClass()

        cls.setUpEmployees()
        cls.setUpProjects()
        cls.employee_bert.resource_calendar_id.tz = 'UTC'
        # extra employee to test _gantt_unavailability grouped by resource_id
        cls.employee_lionel = cls.env['hr.employee'].create({
            'name': 'lionel',
            'work_email': 'lionel@a.be',
            'tz': 'UTC'
        })
        cls.resource_lionel = cls.employee_lionel.resource_id

        # employee leaves
        leave_values = {
            'name': 'leave 1',
            'date_from': fields.Datetime.to_string(date(2019, 5, 5)),
            'date_to': fields.Datetime.to_string(date(2019, 5, 18)),
            'resource_id': cls.employee_bert.resource_id.id,
            'calendar_id': cls.employee_bert.resource_calendar_id.id,
        }
        cls.bert_leave = cls.env['resource.calendar.leaves'].create(leave_values)

    def test__gantt_unavailability_correctly_update_gantt_object(self):
        # create a few forecasts in the opera project
        values = {
            'project_id': self.project_opera.id,
            'allocated_hours': 8,
            'start_datetime': datetime(2019, 8, 6, 0, 0),
            'end_datetime': datetime(2019, 8, 8, 0, 0),
        }
        generated = {}
        for resource in [self.resource_bert, self.resource_lionel, self.resource_joseph]:
            generated[resource.id] = self.env['planning.slot'].create({'resource_id': resource.id, **values})

        unavailabilities = self.env['planning.slot']._gantt_unavailability(
            'resource_id',
            [self.resource_bert.id, self.resource_joseph.id, self.resource_lionel.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'month',
        )

        expected_unavailabilities = [
            {'start': datetime(2019, 1, 1, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 2, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 2, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 3, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 3, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 4, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 4, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 7, 0, 0, tzinfo=pytz.utc)},
        ]

        bert_unavailabilities = unavailabilities[self.resource_bert.id]
        lionel_unavailabilities = unavailabilities[self.resource_lionel.id]

        self.assertEqual(bert_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for bert')
        self.assertEqual(lionel_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for lionel')
