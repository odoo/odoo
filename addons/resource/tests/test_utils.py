# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.osv.expression import normalize_domain
from odoo.addons.resource.models import utils


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
