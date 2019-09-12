# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..controllers.list_controller import TableListExporter
from odoo.tests.common import HttpCase

class WorksheetMock(dict):

    def write(self, x, y, value, style=None):
        if (x, y) in self:
            raise Exception("Cannot rewrite cell [{}, {}]".format(x, y))
        self[x, y] = value

class ListController(HttpCase):

    def test_list_download(self):
        controller = TableListExporter()

        columns = [
            {'field': "foo", 'string': "Foo"},
            {'field': "bar", 'string': "Bar"},
            {'field': "int_field", 'aggregateValue': 19, 'string': "int_field"},
        ]
        groups = [{
            # Group "yop"
            'isGrouped': True,
            'count': 1,
            'aggregateValues': {'int_field': 19},
            'hideHeader': False,
            'value': "yop",
            'data': [{
                # Group "yop > true"
                'isGrouped': False,
                'count': 1,
                'aggregateValues': {'int_field': 10},
                'hideHeader': False,
                'value': "true",
                'data': [{'foo': "yop", 'bar': "True", 'int_field': 10}],
            }, {
                # Group "yop > false"
                'isGrouped': False,
                'count': 10,
                'aggregateValues': {'int_field': 9},
                'hideHeader': False,
                'value': "false",
                'data': [],
            }],
        }]

        worksheet = WorksheetMock()
        controller._write_worksheet(worksheet, {'columns': columns, 'groups': groups})

        # Header
        self.assertEqual(worksheet[0, 0], 'Foo')
        self.assertEqual(worksheet[0, 1], 'Bar')
        self.assertEqual(worksheet[0, 2], 'int_field')

        # Main group
        self.assertEqual(worksheet[1, 0], 'yop (1)', "Group header")
        self.assertEqual(worksheet[1, 2], 19, "int_field aggregate value")

        # First sub-group (open)
        self.assertEqual(worksheet[2, 0], '>true (1)', "subgroup header")
        self.assertEqual(worksheet[2, 2], 10, "int_field aggregate value")

        # data
        self.assertEqual(worksheet[3, 0], 'yop')
        self.assertEqual(worksheet[3, 1], 'True')
        self.assertEqual(worksheet[3, 2], 10)

        # second sub-group (closed)
        self.assertEqual(worksheet[4, 0], '>false (10)', "second sub-group header")
        self.assertEqual(worksheet[4, 2], 9, "int_field aggregate value")

        self.assertEqual(worksheet[5, 2], 19, "main list int_field aggregate value")
