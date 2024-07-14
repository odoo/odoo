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
        # extra employee to test gantt_unavailability grouped by resource_id
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

    def test_gantt_unavailability_correctly_update_gantt_object_single_group_by(self):
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

        rows = [{
            'groupedBy': ["resource_id"],
            'records': [generated[self.resource_bert.id].read()[0]],
            'name': "Bert",
            'resId': self.resource_bert.id,
            'rows': []
        }, {
            'groupedBy': ["resource_id"],
            'records': [generated[self.resource_joseph.id].read()[0]],
            'name': "Bert",
            'resId': self.resource_joseph.id,
            'rows': []
        }, {
            'groupedBy': ["resource_id"],
            'records': [generated[self.resource_lionel.id].read()[0]],
            'name': "Bert",
            'resId': self.resource_lionel.id,
            'rows': []
        }]

        gantt_processed_rows = self.env['planning.slot'].gantt_unavailability(
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'month',
            'user_id, stage_id',
            rows
        )

        expected_unavailabilities = [
            {'start': datetime(2019, 1, 1, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 2, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 2, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 3, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 3, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 4, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 4, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 7, 0, 0, tzinfo=pytz.utc)},
        ]

        bert_unavailabilities = gantt_processed_rows[0]['unavailabilities']
        lionel_unavailabilities = gantt_processed_rows[1]['unavailabilities']

        self.assertEqual(bert_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for bert')
        self.assertEqual(lionel_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for lionel')

    def test_gantt_unavailability_correctly_update_gantt_object_multiple_group_by(self):
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
        rows = [{
            'groupedBy': ["project_id", "resource_id"],
            'records': list(map(lambda x: x.read()[0], generated.values())),
            'name': "Opera project",
            'resId': 9,
            'rows': [{
                'groupedBy': ["resource_id"],
                'records': [generated[self.resource_bert.id].read()[0]],
                'name': "Bert",
                'resId': self.resource_bert.id,
                'rows': []
            }, {
                'groupedBy': ["resource_id"],
                'records': [generated[self.resource_joseph.id].read()[0]],
                'name': "Bert",
                'resId': self.resource_joseph.id,
                'rows': []
            }, {
                'groupedBy': ["resource_id"],
                'records': [generated[self.resource_lionel.id].read()[0]],
                'name': "Bert",
                'resId': self.resource_lionel.id,
                'rows': []
            }]
        }]
        gantt_processed_rows = self.env['planning.slot'].gantt_unavailability(
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'month',
            'user_id, stage_id',
            rows
        )

        expected_unavailabilities = [
            {'start': datetime(2019, 1, 1, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 2, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 2, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 3, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 3, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 4, 8, 0, tzinfo=pytz.utc)},
            {'start': datetime(2019, 1, 4, 17, 0, tzinfo=pytz.utc), 'stop': datetime(2019, 1, 7, 0, 0, tzinfo=pytz.utc)},
        ]

        bert_unavailabilities = gantt_processed_rows[0]['rows'][0]['unavailabilities']
        lionel_unavailabilities = gantt_processed_rows[0]['rows'][1]['unavailabilities']

        self.assertEqual(bert_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for bert')
        self.assertEqual(lionel_unavailabilities, expected_unavailabilities, 'the gantt object was tranformed for lionel')
