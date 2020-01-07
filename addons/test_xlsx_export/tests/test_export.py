# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import date
from unittest.mock import patch

from odoo import http
from odoo.tests import common
from odoo.addons.web.controllers.main import ExportXlsxWriter
from odoo.addons.test_mail.tests.common import mail_new_test_user


class XlsxCreatorCase(common.HttpCase):
    model_name = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None

    def setUp(self):
        super().setUp()
        self.model = self.env[self.model_name]

        mail_new_test_user(self.env, login='fof', password='123456789')
        self.authenticate('fof', '123456789')

        self.worksheet = {}  # mock worksheet

        self.default_params = {
            'domain': [],
            'fields': [{'name': field.name, 'label': field.string} for field in self.model._fields.values()],
            'groupby': [],
            'ids': False,
            'import_compat': False,
            'model': self.model._name,
        }

    def _mock_write(self, row, column, value, style=None):
        self.worksheet[row, column] = str(value)

    def make(self, values, context=None):
        return self.model.with_context(**(context or {})).create(values)

    def export(self, values, fields=[], params={}, context=None):
        self.worksheet = {}
        self.make(values, context=context)

        if fields and 'fields' not in params:
            params['fields'] = [{
                'name': self.model._fields[f].name,
                'label': self.model._fields[f].string,
            } for f in fields]

        with patch.object(ExportXlsxWriter, 'write', self._mock_write):
            self.url_open('/web/export/xlsx', data={
                'data': json.dumps(dict(self.default_params, **params)),
                'token': 'dummy',
                'csrf_token': http.WebRequest.csrf_token(self),
            })
        return self.worksheet

    def assertExportEqual(self, value, expected):
        for row in range(len(expected)):
            for column in range(len(expected[row])):
                cell_value = value.pop((row, column), '')
                expected_value = expected[row][column]
                self.assertEqual(cell_value, expected_value, "Cell %s, %s have a wrong value" % (row, column))
        self.assertFalse(value, "There are unexpected cells in the export")


class TestGroupedExport(XlsxCreatorCase):
    model_name = 'export.group_operator'

    def test_int_sum_max(self):
        values = [
            {'int_sum': 10, 'int_max': 20},
            {'int_sum': 10, 'int_max': 50},
            {'int_sum': 20,'int_max': 30},
        ]
        export = self.export(values, fields=['int_sum', 'int_max'], params={'groupby': ['int_sum', 'int_max']})
        self.assertExportEqual(export, [
            ['Int Sum'      ,'Int Max'],
            ['10 (2)'       ,'50'],
            ['    20 (1)'   ,'20'],
            ['10'           ,'20'],
            ['    50 (1)'   ,'50'],
            ['10'           ,'50'],
            ['20 (1)'       ,'30'],
            ['    30 (1)'   ,'30'],
            ['20'           ,'30'],
        ])

        export = self.export([], fields=['int_max', 'int_sum'], params={'groupby': ['int_sum', 'int_max']})

        self.assertExportEqual(export, [
            ['Int Max'      ,'Int Sum'],
            ['10 (2)'       ,'20'],
            ['    20 (1)'   ,'10'],
            ['20'           ,'10'],
            ['    50 (1)'   ,'10'],
            ['50'           ,'10'],
            ['20 (1)'       ,'20'],
            ['    30 (1)'   ,'20'],
            ['30'           ,'20'],
        ])

    def test_float_min(self):
        values = [
            {'int_sum': 10, 'float_min': 111.0},
            {'int_sum': 10, 'float_min': 222.0},
            {'int_sum': 20, 'float_min': 333.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_min'], params={'groupby': ['int_sum', 'float_min']})

        self.assertExportEqual(export, [
            ['Int Sum'      ,'Float Min'],
            ['10 (2)'       ,'111.0'],
            ['    111.0 (1)','111.0'],
            ['10'           ,'111.0'],
            ['    222.0 (1)','222.0'],
            ['10'           ,'222.0'],
            ['20 (1)'       ,'333.0'],
            ['    333.0 (1)','333.0'],
            ['20'           ,'333.0'],
        ])

    def test_float_avg(self):
        values = [
            {'int_sum': 10, 'float_avg': 100.0},
            {'int_sum': 10, 'float_avg': 200.0},
            {'int_sum': 20, 'float_avg': 300.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'float_avg']})

        self.assertExportEqual(export, [
            ['Int Sum'      ,'Float Avg'],
            ['10 (2)'       ,'150.0'],
            ['    100.0 (1)','100.0'],
            ['10'           ,'100.0'],
            ['    200.0 (1)','200.0'],
            ['10'           ,'200.0'],
            ['20 (1)'       ,'300.0'],
            ['    300.0 (1)','300.0'],
            ['20'           ,'300.0'],
        ])

    def test_float_avg_nested(self):
        """ With more than one nested level (avg aggregation) """
        values = [
            {'int_sum': 10, 'int_max': 30, 'float_avg': 100.0},
            {'int_sum': 10, 'int_max': 30, 'float_avg': 200.0},
            {'int_sum': 10, 'int_max': 20, 'float_avg': 600.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'int_max', 'float_avg']})

        self.assertExportEqual(export, [
            ['Int Sum'          ,'Float Avg'],
            ['10 (3)'           ,'300.0'],
            ['    20 (1)'       ,'600.0'],
            ['        600.0 (1)','600.0'],
            ['10'               ,'600.0'],
            ['    30 (2)'       ,'150.0'],
            ['        100.0 (1)','100.0'],
            ['10'               ,'100.0'],
            ['        200.0 (1)','200.0'],
            ['10'               ,'200.0'],
        ])

    def test_float_avg_nested_no_value(self):
        """ With more than one nested level (avg aggregation is done on 0, not False) """
        values = [
            {'int_sum': 10, 'int_max': 20, 'float_avg': False},
            {'int_sum': 10, 'int_max': 30, 'float_avg': False},
            {'int_sum': 10, 'int_max': 30, 'float_avg': False},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'int_max', 'float_avg']})

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Float Avg'],
            ['10 (3)'               ,'0.0'],
            ['    20 (1)'           ,'0.0'],
            ['        Undefined (1)','0.0'],
            ['10'                   ,'0.0'],
            ['    30 (2)'           ,'0.0'],
            ['        Undefined (2)','0.0'],
            ['10'                   ,'0.0'],
            ['10'                   ,'0.0'],
        ])

    def test_date_max(self):
        values = [
            {'int_sum': 10, 'date_max': date(2019, 1, 1)},
            {'int_sum': 10, 'date_max': date(2000, 1, 1)},
            {'int_sum': 20, 'date_max': date(1980, 1, 1)},
        ]
        export = self.export(values, fields=['int_sum', 'date_max'], params={'groupby': ['int_sum', 'date_max:month']})

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Date Max'],
            ['10 (2)'               ,'2019-01-01'],
            ['    January 2000 (1)' ,'2000-01-01'],
            ['10'                   ,'2000-01-01'],
            ['    January 2019 (1)' ,'2019-01-01'],
            ['10'                   ,'2019-01-01'],
            ['20 (1)'               ,'1980-01-01'],
            ['    January 1980 (1)' ,'1980-01-01'],
            ['20'                   ,'1980-01-01'],
        ])

    def test_bool_and(self):
        values = [
            {'int_sum': 10, 'bool_and': True},
            {'int_sum': 10, 'bool_and': True},
            {'int_sum': 20, 'bool_and': True},
            {'int_sum': 20, 'bool_and': False},
        ]
        export = self.export(values, fields=['int_sum', 'bool_and'], params={'groupby': ['int_sum', 'bool_and']})

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Bool And'],
            ['10 (2)'               ,'True'],
            ['    True (2)'         ,'True'],
            ['10'                   ,'True'],
            ['10'                   ,'True'],
            ['20 (2)'               ,'False'],
            ['    False (1)'        ,'False'],
            ['20'                   ,'False'],
            ['    True (1)'         ,'True'],
            ['20'                   ,'True'],
        ])

    def test_bool_or(self):
        values = [
            {'int_sum': 10, 'bool_or': True},
            {'int_sum': 10, 'bool_or': False},
            {'int_sum': 20, 'bool_or': False},
            {'int_sum': 20, 'bool_or': False},
        ]
        export = self.export(values, fields=['int_sum', 'bool_or'], params={'groupby': ['int_sum', 'bool_or']})

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Bool Or'],
            ['10 (2)'               ,'True'],
            ['    False (1)'        ,'False'],
            ['10'                   ,'False'],
            ['    True (1)'         ,'True'],
            ['10'                   ,'True'],
            ['20 (2)'               ,'False'],
            ['    False (2)'        ,'False'],
            ['20'                   ,'False'],
            ['20'                   ,'False'],
        ])

    def test_many2one(self):
        values = [
            {'int_sum': 10, 'many2one': self.env['export.integer'].create({}).id},
            {'int_sum': 10},
        ]
        export = self.export(values, fields=['int_sum', 'many2one'], params={'groupby': ['int_sum', 'many2one']})

        self.assertExportEqual(export, [
            ['Int Sum'                  ,'Many2One'],
            ['10 (2)'                   ,''],
            ['    export.integer:4 (1)' ,''],
            ['10'                       ,'export.integer:4'],
            ['    Undefined (1)'        ,''],
            ['10'                       ,'False'],
        ])

    def test_nested_records(self):
        """
        aggregated values currently not supported for nested record export, but it should not crash
        e.g. export 'many2one/const'
        """
        values = [{'int_sum': 10,
            'date_max': date(2019, 1, 1),
            'many2one': self.env['export.integer'].create({}).id,
        }, {
            'int_sum': 10,
            'date_max': date(2000, 1, 1),
            'many2one': self.env['export.integer'].create({}).id,
        },]
        export = self.export(values,
                    params={
                        'groupby': ['int_sum', 'date_max:month'],
                        'fields': [
                            {'name': 'int_sum', 'label': 'Int Sum'},
                            {'name': 'date_max', 'label': 'Date Max'},
                            {'name': 'many2one/value', 'label': 'Many2One/Value'},
                        ]
                    })

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Date Max'     ,'Many2One/Value'],
            ['10 (2)'               ,'2019-01-01'   ,''],
            ['    January 2000 (1)' ,'2000-01-01'   ,''],
            ['10'                   ,'2000-01-01'   ,'4'],
            ['    January 2019 (1)' ,'2019-01-01'   ,''],
            ['10'                   ,'2019-01-01'   ,'4'],
        ])

    def test_one2many(self):
        values = [{
            'int_sum': 10,
            'one2many': [
                (0, 0, {'value': 8}),
                (0, 0, {'value': 9}),
            ],
        }]
        export = self.export(values,
                    params={
                        'groupby': ['int_sum',],
                        'fields': [
                            {'name': 'int_sum', 'label': 'Int Sum'},
                            {'name': 'one2many/value', 'label': 'One2many/Value'},
                        ]
                    })
        self.assertExportEqual(export, [
            ['Int Sum'  ,'One2many/Value'],
            ['10 (1)'   ,''],
            ['10'       ,'8'],
            [''         ,'9'],
        ])

    def test_unset_date_values(self):
        values = [
            {'int_sum': 10, 'date_max': date(2019, 1, 1)},
            {'int_sum': 10, 'date_max': False},
        ]
        # Group and aggregate by date, but date fields are not set for all records
        export = self.export(values, fields=['int_sum', 'date_max'], params={'groupby': ['int_sum', 'date_max:month']})

        self.assertExportEqual(export, [
            ['Int Sum'              ,'Date Max'],
            ['10 (2)'               ,'2019-01-01'],
            ['    January 2019 (1)' ,'2019-01-01'],
            ['10'                   ,'2019-01-01'],
            ['    Undefined (1)'    ,''],
            ['10'                   ,''],
        ])
