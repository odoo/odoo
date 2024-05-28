# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase
from odoo.osv.expression import normalize_domain
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
        expected_results = []
        expected_results.append([
            normalize_domain([('admin', '=', True)]),
            normalize_domain([('admin', '=', True), ('admin', '=', True)]),
            normalize_domain([('admin', '=', True)]),
            normalize_domain([('admin', '=', True)]),
            normalize_domain(['|', '|', ('admin', '=', 1), ('admin', '=', True), ('admin', '=', True)]),
            normalize_domain(['|', '|', '!', ('admin', '=', 1), ('admin', '=', True), '!', ('admin', '=', True)]),
            normalize_domain([('admin', '=', True)]),
            normalize_domain([['start_datetime', '<=', '2022-12-17 22:59:59'], ['end_datetime', '>=', '2022-12-10 23:00:00']]),
            normalize_domain([('admin', '=', 1), ('admin', '=', 1), '|', ('admin', '=', 1), ('admin', '=', 1)])
        ])
        expected_results.append([
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([]),
            normalize_domain([['start_datetime', '<=', '2022-12-17 22:59:59'], ['end_datetime', '>=', '2022-12-10 23:00:00']]),
            normalize_domain([])
        ])
        for idx, fields in enumerate(fields_to_remove):
            results = [normalize_domain(utils.filter_domain_leaf(dom, lambda field: field not in fields)) for dom in domains]
            self.assertEqual(results, expected_results[idx])

        # Testing field mapping 1
        self.assertEqual(
            [('field4', '!=', 'test')],
            normalize_domain(utils.filter_domain_leaf(
                ['|', ('field1', 'in', [1, 2]), '!', ('field2', '=', False), ('field3', '!=', 'test')],
                lambda field: field == 'field3',
                field_name_mapping={'field3': 'field4'},
            ))
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
