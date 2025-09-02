# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.fields import Datetime, Domain
from odoo.tests.common import TransactionCase
from odoo.addons.resource.models import utils
from odoo.tests import Form


class TestExpression(TransactionCase):

    def test_filter_domain_leaf(self):
        domains = [
            ['|', ('skills', '=', 1), ('admin', '=', True)],
            ['|', ('skills', '=', 1), ('admin', '=', True), '|', ('skills', '=', 2), ('admin', '=', True)],
            ['|', ('skills', '=', 1), ('skills', '=', 2), '|', ('skills', '=', 2), ('admin', '=', True)],
            ['|', '|', ('skills', '=', 1), ('skills', '=', True), '|', ('skills', '=', 2), ('admin', '=', True)],
            ['|', '|', ('admin', '=', 1), ('admin', '=', True), '&', ('skills', '=', 2), ('admin', '=', True)],
            ['|', '|', '!', ('admin', '=', 1), ('admin', '=', True), '!', '&', '!', ('skills', '=', 2), ('admin', '=', True)],
            ['&', '!', ('skills', '=', 2), ('admin', '=', True)],
            [['start_datetime', '<=', '2022-12-17 22:59:59'], ['end_datetime', '>=', '2022-12-10 23:00:00']],
            [('admin', '=', 1), ('admin', '=', 1), '|', ('admin', '=', 1), ('admin', '=', 1), ('skills', '=', 2)]
        ]
        fields_to_remove = [['skills'], ['admin', 'skills']]
        expected_results = [
            [
                [('admin', '=', True)],
                [('admin', '=', True), ('admin', '=', True)],
                [('admin', '=', True)],
                [('admin', '=', True)],
                ['|', '|', ('admin', '=', 1), ('admin', '=', True), ('admin', '=', True)],
                ['|', '|', '!', ('admin', '=', 1), ('admin', '=', True), '!', ('admin', '=', True)],
                [('admin', '=', True)],
                [['start_datetime', '<=', '2022-12-17 22:59:59'], ['end_datetime', '>=', '2022-12-10 23:00:00']],
                [('admin', '=', 1), ('admin', '=', 1), '|', ('admin', '=', 1), ('admin', '=', 1)],
            ],
            [
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [['start_datetime', '<=', '2022-12-17 22:59:59'], ['end_datetime', '>=', '2022-12-10 23:00:00']],
                [],
            ],
        ]
        for idx, fields in enumerate(fields_to_remove):
            results = [utils.filter_domain_leaf(dom, lambda field: field not in fields) for dom in domains]
            self.assertEqual(results, [Domain(expected) for expected in expected_results[idx]])

        # Testing field mapping 1
        self.assertEqual(
            Domain('field4', '!=', 'test'),
            utils.filter_domain_leaf(
                ['|', ('field1', 'in', [1, 2]), '!', ('field2', '=', False), ('field3', '!=', 'test')],
                lambda field: field == 'field3',
                field_name_mapping={'field3': 'field4'},
            )
        )

    def test_resource_calendar_leave_compute_date_to(self):
        """
        Test date_to is computed when date_from is changed,
        except when it already has a valid value.
        """
        date_from = Datetime.from_string('2024-05-01 00:00:00')
        date_to = Datetime.from_string('2024-05-03 23:59:59')
        leave = self.env['resource.calendar.leaves'].create({
            'date_from': date_from,
            'date_to': date_to,
        })

        leave.date_from -= relativedelta(minutes=5)
        self.assertEqual(leave.date_to, date_to, "date_to shouldn't get recomputed if still valid")

        leave.date_from += relativedelta(years=5)
        self.assertGreater(leave.date_to, date_to, "date_to should get recomputed when invalid")

    def test_resource_creation_with_date_from(self):
        """
        Test resource creation with a date_from.
        AssertError is raised when date_from is not provided.
        """

        with self.assertRaises(AssertionError):
            with Form(self.env['resource.calendar.leaves']) as res:
                res.date_from = False
                res.date_to = Datetime.now()

        with Form(self.env['resource.calendar.leaves']) as res:
            date_from = Datetime.now()
            date_to = Datetime.now() + relativedelta(hours=24)
            res.date_from = date_from
            res.date_to = date_to

            self.assertFalse(res.id, 'The resource does not have an id before saving')
            res.save()
            self.assertTrue(res.id, 'The resource was successfully created')
            self.assertEqual(res.date_from, Datetime.to_string(date_from))
            self.assertEqual(res.date_to, Datetime.to_string(date_to))

    def test_duration_based_hours_per_week(self):
        """
        Test that the hours per week in duration based calendar is correctly computed.
        """
        calendar = self.env['resource.calendar'].create({
            'name': 'Duration Based Calendar',
            'two_weeks_calendar': False,
            'tz': 'Europe/Brussels',
            'company_id': False,
            'duration_based': True,
            'attendance_ids': [(5, 0, 0),
                ## Hours Per Week: 31, Avg hours_per_day = 6.2
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'duration_hours': 4, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'duration_hours': 4, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'duration_hours': 5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'duration_hours': 4, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'duration_hours': 5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'duration_hours': 3, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Full Day', 'dayofweek': '4', 'duration_hours': 6, 'day_period': 'full_day'}),
            ],
        })

        with Form(calendar) as res:
            self.assertEqual(res.hours_per_week, 31)
            self.assertAlmostEqual(res.hours_per_day, 31 / 5, 2)
            self.assertEqual(res.attendance_ids._records[0].get('hour_from'), 8)
            self.assertEqual(res.attendance_ids._records[0].get('hour_to'), 12)
            self.assertEqual(res.attendance_ids._records[4].get('hour_from'), 12)
            self.assertEqual(res.attendance_ids._records[4].get('hour_to'), 17)
            self.assertEqual(res.attendance_ids._records[6].get('hour_from'), 9)
            self.assertEqual(res.attendance_ids._records[6].get('hour_to'), 15)

        calendar.attendance_ids[0].unlink()
        with Form(calendar) as res:
            self.assertEqual(res.hours_per_week, 27)
            self.assertAlmostEqual(res.hours_per_day, 27 / 5, 2)

        calendar.write({'attendance_ids': [(0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'duration_hours': 5, 'day_period': 'morning'})]})
        with Form(calendar) as res:
            self.assertEqual(res.hours_per_week, 32)
            self.assertAlmostEqual(res.hours_per_day, 32 / 5, 2)

        calendar.attendance_ids[0]['duration_hours'] = 6.0
        with Form(calendar) as res:
            self.assertEqual(res.hours_per_week, 34)
            self.assertAlmostEqual(res.hours_per_day, 34 / 5, 2)

        calendar.attendance_ids[2].unlink()
        calendar.attendance_ids[2]['day_period'] = 'full_day'
        calendar.attendance_ids[2]['duration_hours'] = 8.0
        with Form(calendar) as res:
            self.assertEqual(res.hours_per_week, 33)
            self.assertAlmostEqual(res.hours_per_day, 33 / 5, 2)
