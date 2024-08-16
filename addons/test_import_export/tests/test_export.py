import json
from datetime import date
from unittest.mock import patch

from odoo import http
from odoo.tests import common, tagged
from odoo.tools.misc import get_lang
from odoo.addons.web.controllers.export import ExportXlsxWriter


class XlsxCreatorCase(common.HttpCase):

    def setUp(self):
        super().setUp()
        self.model_name = 'export.aggregator'
        self.model = self.env[self.model_name]

        self.session = self.authenticate('admin', 'admin')

        self.worksheet = {}  # mock worksheet

        self.default_params = {
            'domain': [],
            'fields': [{'name': field.name, 'label': field.string} for field in self.model._fields.values()],
            'groupby': [],
            'ids': False,
            'import_compat': False,
            'model': self.model_name,
        }

    def _mock_write(self, row, column, value, style=None):
        if isinstance(value, float):
            decimal_places = style.num_format[::-1].find('.')
            style_format = "{:." + str(decimal_places) + "f}"
            self.worksheet[row, column] = style_format.format(value)
        else:
            self.worksheet[row, column] = str(value)

    def make(self, values, context=None):
        return self.model.with_context(**(context or {})).create(values)

    def export(self, values, fields=[], params={}, context=None):
        self.worksheet = {}
        self.make(values, context=context)

        if fields and 'fields' not in params:
            params['fields'] = [
                {
                    'name': self.model._fields[f].name,
                    'label': self.model._fields[f].string,
                    'type': self.model._fields[f].type,
                }
                for f in fields
            ]

        with patch.object(ExportXlsxWriter, 'write', self._mock_write):
            self.url_open(
                '/web/export/xlsx',
                data={
                    'data': json.dumps(dict(self.default_params, **params)),
                    'csrf_token': http.Request.csrf_token(self),
                },
            )
        return self.worksheet

    def assertExportEqual(self, value, expected):
        for row in range(len(expected)):
            for column in range(len(expected[row])):
                cell_value = value.pop((row, column), '')
                expected_value = expected[row][column]
                self.assertEqual(cell_value, expected_value, "Cell %s, %s have a wrong value" % (row, column))
        self.assertFalse(value, "There are unexpected cells in the export")


@tagged('post_install', '-at_install')
class TestExport(XlsxCreatorCase):

    def test_int_monetary_float(self):
        # FIXME the currency is actually not used but still change the behavior of the export (see ExportXlsxWriter.__init__)
        self.env['res.currency'].create(
            {
                'name': "bottlecap",
                'symbol': "b",
                'rounding': 0.001,
                'decimal_places': 3,
            }
        )

        values = [
            {'int_sum': 1, 'float_monetary': 60739.2000000004, 'bool_and': True, 'float_min': 60739.2000000004},
            {'int_sum': 2, 'float_monetary': 999.9995999, 'bool_and': True, 'float_min': 999.9995999},
            {'int_sum': 0, 'float_monetary': 0.0, 'bool_and': False, 'float_min': 0.0},
            {},
        ]
        export = self.export(
            values,
            fields=['int_sum', 'float_monetary', 'bool_and', 'float_min'],
        )
        # FIXME assertExportEqual doesn't test the real information show in the export file
        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Monetary', 'Bool And', 'Float Min'],
                ['1', '60739.200', 'True', '60739.20'],
                ['2', '1000.000', 'True', '1000.00'],
                ['0', '0.000', 'False', '0.00'],
                ['0', '0.000', 'False', '0.00'],
            ],
        )


@tagged('-at_install', 'post_install')
class TestGroupedExport(XlsxCreatorCase):

    def test_archived_groupped(self):
        values = [
            {'int_sum': 1, 'active': False},
        ]
        export = self.export(values, fields=['int_sum', 'active'], params={'groupby': ['int_sum']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Active'],
                ['1 (1)', ''],
            ],
        )

    def test_int_sum_max(self):
        values = [
            {'int_sum': 10, 'int_max': 20},
            {'int_sum': 10, 'int_max': 50},
            {'int_sum': 20, 'int_max': 30},
        ]
        export = self.export(values, fields=['int_sum', 'int_max'], params={'groupby': ['int_sum', 'int_max']})
        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Int Max'],
                ['10 (2)', '50'],
                ['    20 (1)', '20'],
                ['10', '20'],
                ['    50 (1)', '50'],
                ['10', '50'],
                ['20 (1)', '30'],
                ['    30 (1)', '30'],
                ['20', '30'],
            ],
        )

        export = self.export([], fields=['int_max', 'int_sum'], params={'groupby': ['int_sum', 'int_max']})

        self.assertExportEqual(
            export,
            [
                ['Int Max', 'Int Sum'],
                ['10 (2)', '20'],
                ['    20 (1)', '10'],
                ['20', '10'],
                ['    50 (1)', '10'],
                ['50', '10'],
                ['20 (1)', '20'],
                ['    30 (1)', '20'],
                ['30', '20'],
            ],
        )

    def test_float_min(self):
        values = [
            {'int_sum': 10, 'float_min': 111.0},
            {'int_sum': 10, 'float_min': 222.0},
            {'int_sum': 20, 'float_min': 333.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_min'], params={'groupby': ['int_sum', 'float_min']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Min'],
                ['10 (2)', '111.00'],
                ['    111.0 (1)', '111.00'],
                ['10', '111.00'],
                ['    222.0 (1)', '222.00'],
                ['10', '222.00'],
                ['20 (1)', '333.00'],
                ['    333.0 (1)', '333.00'],
                ['20', '333.00'],
            ],
        )

    def test_float_avg(self):
        values = [
            {'int_sum': 10, 'float_avg': 100.0},
            {'int_sum': 10, 'float_avg': 200.0},
            {'int_sum': 20, 'float_avg': 300.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'float_avg']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Avg'],
                ['10 (2)', '150.00'],
                ['    100.0 (1)', '100.00'],
                ['10', '100.00'],
                ['    200.0 (1)', '200.00'],
                ['10', '200.00'],
                ['20 (1)', '300.00'],
                ['    300.0 (1)', '300.00'],
                ['20', '300.00'],
            ],
        )

    def test_float_avg_nested(self):
        """With more than one nested level (avg aggregation)"""
        values = [
            {'int_sum': 10, 'int_max': 30, 'float_avg': 100.0},
            {'int_sum': 10, 'int_max': 30, 'float_avg': 200.0},
            {'int_sum': 10, 'int_max': 20, 'float_avg': 600.0},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'int_max', 'float_avg']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Avg'],
                ['10 (3)', '300.00'],
                ['    20 (1)', '600.00'],
                ['        600.0 (1)', '600.00'],
                ['10', '600.00'],
                ['    30 (2)', '150.00'],
                ['        100.0 (1)', '100.00'],
                ['10', '100.00'],
                ['        200.0 (1)', '200.00'],
                ['10', '200.00'],
            ],
        )

    def test_float_avg_nested_no_value(self):
        """With more than one nested level (avg aggregation is done on 0, not False)"""
        values = [
            {'int_sum': 10, 'int_max': 20, 'float_avg': False},
            {'int_sum': 10, 'int_max': 30, 'float_avg': False},
            {'int_sum': 10, 'int_max': 30, 'float_avg': False},
        ]
        export = self.export(values, fields=['int_sum', 'float_avg'], params={'groupby': ['int_sum', 'int_max', 'float_avg']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Avg'],
                ['10 (3)', '0.00'],
                ['    20 (1)', '0.00'],
                ['        Undefined (1)', '0.00'],
                ['10', '0.00'],
                ['    30 (2)', '0.00'],
                ['        Undefined (2)', '0.00'],
                ['10', '0.00'],
                ['10', '0.00'],
            ],
        )

    def test_date_max(self):
        values = [
            {'int_sum': 10, 'date_max': date(2019, 1, 1)},
            {'int_sum': 10, 'date_max': date(2000, 1, 1)},
            {'int_sum': 20, 'date_max': date(1980, 1, 1)},
        ]
        export = self.export(values, fields=['int_sum', 'date_max'], params={'groupby': ['int_sum', 'date_max:month']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Date Max'],
                ['10 (2)', '2019-01-01'],
                ['    January 2000 (1)', '2000-01-01'],
                ['10', '2000-01-01'],
                ['    January 2019 (1)', '2019-01-01'],
                ['10', '2019-01-01'],
                ['20 (1)', '1980-01-01'],
                ['    January 1980 (1)', '1980-01-01'],
                ['20', '1980-01-01'],
            ],
        )

    def test_bool_and(self):
        values = [
            {'int_sum': 10, 'bool_and': True},
            {'int_sum': 10, 'bool_and': True},
            {'int_sum': 20, 'bool_and': True},
            {'int_sum': 20, 'bool_and': False},
        ]
        export = self.export(values, fields=['int_sum', 'bool_and'], params={'groupby': ['int_sum', 'bool_and']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Bool And'],
                ['10 (2)', 'True'],
                ['    True (2)', 'True'],
                ['10', 'True'],
                ['10', 'True'],
                ['20 (2)', 'False'],
                ['    False (1)', 'False'],
                ['20', 'False'],
                ['    True (1)', 'True'],
                ['20', 'True'],
            ],
        )

    def test_bool_or(self):
        values = [
            {'int_sum': 10, 'bool_or': True},
            {'int_sum': 10, 'bool_or': False},
            {'int_sum': 20, 'bool_or': False},
            {'int_sum': 20, 'bool_or': False},
        ]
        export = self.export(values, fields=['int_sum', 'bool_or'], params={'groupby': ['int_sum', 'bool_or']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Bool Or'],
                ['10 (2)', 'True'],
                ['    False (1)', 'False'],
                ['10', 'False'],
                ['    True (1)', 'True'],
                ['10', 'True'],
                ['20 (2)', 'False'],
                ['    False (2)', 'False'],
                ['20', 'False'],
                ['20', 'False'],
            ],
        )

    def test_many2one(self):
        values = [
            {'int_sum': 10, 'many2one': self.env['export.integer'].create({}).id},
            {'int_sum': 10},
        ]
        export = self.export(values, fields=['int_sum', 'many2one'], params={'groupby': ['int_sum', 'many2one']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Many2One'],
                ['10 (2)', ''],
                ['    export.integer:4 (1)', ''],
                ['10', 'export.integer:4'],
                ['    Undefined (1)', ''],
                ['10', ''],
            ],
        )

    def test_nested_records(self):
        """
        aggregated values currently not supported for nested record export, but it should not crash
        e.g. export 'many2one/const'
        """
        values = [
            {
                'int_sum': 10,
                'date_max': date(2019, 1, 1),
                'many2one': self.env['export.integer'].create({}).id,
            },
            {
                'int_sum': 10,
                'date_max': date(2000, 1, 1),
                'many2one': self.env['export.integer'].create({}).id,
            },
        ]
        export = self.export(
            values,
            params={
                'groupby': ['int_sum', 'date_max:month'],
                'fields': [
                    {'name': 'int_sum', 'label': 'Int Sum', 'type': 'integer'},
                    {'name': 'date_max', 'label': 'Date Max', 'type': 'date'},
                    {'name': 'many2one/value', 'label': 'Many2One/Value', 'type': 'many2one'},
                ],
            },
        )

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Date Max', 'Many2One/Value'],
                ['10 (2)', '2019-01-01', ''],
                ['    January 2000 (1)', '2000-01-01', ''],
                ['10', '2000-01-01', '4'],
                ['    January 2019 (1)', '2019-01-01', ''],
                ['10', '2019-01-01', '4'],
            ],
        )

    def test_one2many(self):
        values = [
            {
                'int_sum': 10,
                'one2many': [
                    (0, 0, {'value': 8}),
                    (0, 0, {'value': 9}),
                ],
            }
        ]
        export = self.export(
            values,
            params={
                'groupby': ['int_sum'],
                'fields': [
                    {'name': 'int_sum', 'label': 'Int Sum', 'type': 'integer'},
                    {'name': 'one2many/value', 'label': 'One2many/Value', 'type': 'integer'},
                ],
            },
        )
        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'One2many/Value'],
                ['10 (1)', ''],
                ['10', '8'],
                ['', '9'],
            ],
        )

    def test_unset_date_values(self):
        values = [
            {'int_sum': 10, 'date_max': date(2019, 1, 1)},
            {'int_sum': 10, 'date_max': False},
        ]
        # Group and aggregate by date, but date fields are not set for all records
        export = self.export(values, fields=['int_sum', 'date_max'], params={'groupby': ['int_sum', 'date_max:month']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Date Max'],
                ['10 (2)', '2019-01-01'],
                ['    January 2019 (1)', '2019-01-01'],
                ['10', '2019-01-01'],
                ['    Undefined (1)', ''],
                ['10', ''],
            ],
        )

    def test_float_representation(self):
        currency = self.env['res.currency'].create(
            {
                'name': "bottlecap",
                'symbol': "b",
                'rounding': 0.001,
                'decimal_places': 3,
            }
        )

        values = [
            {'int_sum': 1, 'currency_id': currency.id, 'float_monetary': 60739.2000000004},
            {'int_sum': 2, 'currency_id': currency.id, 'float_monetary': 2.0},
            {'int_sum': 3, 'currency_id': currency.id, 'float_monetary': 999.9995999},
            {'int_sum': 3, 'currency_id': currency.id, 'float_monetary': 0.0},
            {'currency_id': currency.id},
        ]
        export = self.export(values, fields=['int_sum', 'float_monetary'], params={'groupby': ['int_sum', 'float_monetary']})
        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Monetary'],
                ['1 (1)', '60739.200'],
                ['    60739.2 (1)', '60739.200'],
                ['1', '60739.200'],
                ['2 (1)', '2.000'],
                ['    2.0 (1)', '2.000'],
                ['2', '2.000'],
                ['3 (2)', '1000.000'],
                ['    Undefined (1)', '0.000'],
                ['3', '0.000'],
                ['    1000.0 (1)', '1000.000'],
                ['3', '1000.000'],
                ['Undefined (1)', '0.000'],
                ['    Undefined (1)', '0.000'],
                ['0', '0.000'],
            ],
        )

    def test_decimal_separator(self):
        """The decimal separator of the language used shouldn't impact the float representation in the exported xlsx"""
        lang_data = get_lang(self.env)
        lang = self.env['res.lang'].browse(lang_data.id)
        lang.decimal_point = ','
        lang.thousands_sep = '.'

        values = [
            {'int_sum': 1, 'float_min': 86420.864},
        ]
        export = self.export(values, fields=['int_sum', 'float_min'], params={'groupby': ['int_sum', 'float_min']})

        self.assertExportEqual(
            export,
            [
                ['Int Sum', 'Float Min'],
                ['1 (1)', '86420.86'],
                ['    86420.864 (1)', '86420.86'],
                ['1', '86420.86'],
            ],
        )
