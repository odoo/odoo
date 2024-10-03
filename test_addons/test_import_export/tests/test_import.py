import base64
import csv
import difflib
import io
import pprint
import unittest

from PIL import Image

from odoo.tests.common import TransactionCase, can_import, RecordCapturer
from odoo.tools import mute_logger
from odoo.tools.misc import file_open
from odoo.addons.base_import.models.base_import import ImportValidationError


def get_id_field(model_name):
    return {
        'id': 'id',
        'name': 'id',
        'string': "External ID",
        'required': False,
        'fields': [],
        'type': 'id',
        'model_name': model_name,
    }


def make_field(name='value', string='Value', required=False, fields=None, field_type='id', model_name=None, comodel_name=None):
    if fields is None:
        fields = []
    field = {'id': name, 'name': name, 'string': string, 'required': required, 'fields': fields, 'type': field_type}
    if model_name:
        field['model_name'] = model_name
    if comodel_name:
        field['comodel_name'] = comodel_name
    return [
        get_id_field(model_name),
        field,
    ]


def sorted_fields(fields):
    """ recursively sort field lists to ease comparison """
    recursed = [dict(field, fields=sorted_fields(field['fields'])) for field in fields]
    return sorted(recursed, key=lambda field: field['id'])


class BaseImportCase(TransactionCase):

    def assertEqualFields(self, fields1, fields2):
        f1 = sorted_fields(fields1)
        f2 = sorted_fields(fields2)
        assert f1 == f2, '\n'.join(difflib.unified_diff(
            pprint.pformat(f1).splitlines(),
            pprint.pformat(f2).splitlines()
        ))


class TestBasicFields(BaseImportCase):

    def get_fields(self, field):
        return self.env['base_import.import'].get_fields_tree(f"import.{field}")

    def test_base(self):
        """ A basic field is not required """
        self.assertEqualFields(self.get_fields('char'), make_field(field_type='char', model_name='import.char'))

    def test_required(self):
        """ Required fields should be flagged (so they can be fill-required) """
        self.assertEqualFields(self.get_fields('char.required'), make_field(required=True, field_type='char', model_name='import.char.required'))

    def test_readonly(self):
        """ Readonly fields should be filtered out"""
        self.assertEqualFields(self.get_fields('char.readonly'), [get_id_field("import.char.readonly")])

    def test_readonly_states_noreadonly(self):
        """ Readonly fields with states having nothing to do with
        readonly should still be filtered out"""
        self.assertEqualFields(self.get_fields('char.noreadonly'), [get_id_field("import.char.noreadonly")])

    def test_readonly_states_stillreadonly(self):
        """ Readonly fields with readonly states leaving them readonly
        always... filtered out"""
        self.assertEqualFields(self.get_fields('char.stillreadonly'), [get_id_field("import.char.stillreadonly")])

    def test_m2o(self):
        """ M2O fields should allow import of themselves (display_name),
        their id and their xid"""
        self.assertEqualFields(self.get_fields('m2o'), make_field(
            field_type='many2one', comodel_name='import.m2o.related', model_name='import.m2o',
            fields=[
                {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': [], 'type': 'id', 'model_name': 'import.m2o'},
                {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': False, 'fields': [], 'type': 'id', 'model_name': 'import.m2o'},
        ]))

    def test_m2o_required(self):
        """ If an m2o field is required, its three sub-fields are
        required as well (the client has to handle that: requiredness
        is id-based)
        """
        self.assertEqualFields(self.get_fields('m2o.required'), make_field(
            field_type='many2one', required=True, comodel_name='import.m2o.required.related', model_name='import.m2o.required',
            fields=[
                {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': True, 'fields': [], 'type': 'id', 'model_name': 'import.m2o.required'},
                {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': True, 'fields': [], 'type': 'id', 'model_name': 'import.m2o.required'},
        ]))


class TestO2M(BaseImportCase):

    def get_fields(self, field):
        return self.env['base_import.import'].get_fields_tree(f"import.{field}")

    def test_shallow(self):
        self.assertEqualFields(
            self.get_fields('o2m'), [
                get_id_field("import.o2m"),
                {'id': 'name', 'name': 'name', 'string': "Name", 'required': False, 'fields': [], 'type': 'char', 'model_name': 'import.o2m'},
                {
                    'id': 'value', 'name': 'value', 'string': 'Value', 'model_name': 'import.o2m',
                    'required': False, 'type': 'one2many', 'comodel_name': 'import.o2m.child',
                    'fields': [
                        get_id_field("import.o2m.child"),
                        {
                            'id': 'parent_id', 'name': 'parent_id', 'model_name': 'import.o2m.child',
                            'string': 'Parent', 'type': 'many2one', 'comodel_name': 'import.o2m',
                            'required': False, 'fields': [
                                {'id': 'parent_id', 'name': 'id', 'model_name': 'import.o2m.child',
                                 'string': 'External ID', 'required': False,
                                 'fields': [], 'type': 'id'},
                                {'id': 'parent_id', 'name': '.id', 'model_name': 'import.o2m.child',
                                 'string': 'Database ID', 'required': False,
                                 'fields': [], 'type': 'id'},
                            ]
                        },
                        {'id': 'value', 'name': 'value', 'string': 'Value',
                         'required': False, 'fields': [], 'type': 'integer', 'model_name': 'import.o2m.child',
                        },
                    ]
                }
            ]
        )


class TestMatchHeadersSingle(TransactionCase):

    def test_match_by_name(self):
        match = self.env['base_import.import']._get_mapping_suggestion('f0', [{'name': 'f0'}], [], {})
        self.assertEqual(match, {'field_path': ['f0'], 'distance': 0})

    def test_match_by_string(self):
        match = self.env['base_import.import']._get_mapping_suggestion('some field', [{'name': 'bob', 'string': "Some Field"}], [], {})
        self.assertEqual(match, {'field_path': ['bob'], 'distance': 0})

    def test_nomatch(self):
        match = self.env['base_import.import']._get_mapping_suggestion('should not be', [{'name': 'bob', 'string': "wheee", 'model_name': 'base_import.import'}], [], {})
        self.assertEqual(match, {})

    def test_close_match(self):
        match = self.env['base_import.import']._get_mapping_suggestion('bobe', [{'name': 'bob', 'type': 'char', 'string': "wheee", 'model_name': 'base_import.import'}], ['char'], {})
        self.assertEqual(match, {'field_path': ['bob'], 'distance': 0.1428571428571429})

    def test_distant_match(self):
        Import = self.env['base_import.import']
        header, field_string = 'same Folding', 'Some Field'
        match = Import._get_mapping_suggestion(header, [{'name': 'bob', 'string': field_string, 'type': 'char', 'model_name': 'base_import.import'}], ['char'], {})
        string_field_dist = Import._get_distance(header.lower(), field_string.lower())
        self.assertEqual(string_field_dist, 0.36363636363636365)
        self.assertEqual(match, {})  # if distance >= 0.2, no match returned

    def test_recursive_match(self):
        f = {
            'name': 'f0',
            'string': "My Field",
            'fields': [
                {'name': 'f0', 'string': "Sub field 0", 'fields': [], 'model_name': 'base_import.import'},
                {'name': 'f1', 'string': "Sub field 2", 'fields': [], 'model_name': 'base_import.import'},
            ]
        }
        match = self.env['base_import.import']._get_mapping_suggestion('f0/f1', [f], [], {})
        self.assertEqual(match, {'field_path': [f['name'], f['fields'][1]['name']]})

    def test_recursive_nomatch(self):
        """ Match first level, fail to match second level
        """
        f = {
            'name': 'f0',
            'string': "My Field",
            'fields': [
                {'name': 'f0', 'string': "Sub field 0", 'fields': [], 'model_name': 'base_import.import'},
                {'name': 'f1', 'string': "Sub field 2", 'fields': [], 'model_name': 'base_import.import'},
            ]
        }
        match = self.env['base_import.import']._get_mapping_suggestion('f0/f2', [f], [], {})
        self.assertEqual(match, {})


class TestMatchHeadersMultiple(TransactionCase):

    def test_noheaders(self):
        self.assertEqual(
            self.env['base_import.import']._get_mapping_suggestions([], {}, []), {}
        )

    def test_nomatch(self):
        self.assertEqual(
            self.env['base_import.import']._get_mapping_suggestions(
                ['foo', 'bar', 'baz', 'qux'],
                {
                    (0, 'foo'): ['int'],
                    (1, 'bar'): ['char'],
                    (2, 'baz'): ['text'],
                    (3, 'qux'): ['many2one']
                },
                {}),
            {
                (0, 'foo'): None,
                (1, 'bar'): None,
                (2, 'baz'): None,
                (3, 'qux'): None
            }
        )

    def test_mixed(self):
        self.assertEqual(
            self.env['base_import.import']._get_mapping_suggestions(
                'foo bar baz qux/corge'.split(),
                {
                    (0, 'foo'): ['int'],
                    (1, 'bar'): ['char'],
                    (2, 'baz'): ['text'],
                    (3, 'qux/corge'): ['text']
                },
                [
                    {'name': 'bar', 'string': 'Bar', 'type': 'char', 'model_name': 'base_import.import'},
                    {'name': 'bob', 'string': 'Baz', 'type': 'text', 'model_name': 'base_import.import'},
                    {'name': 'qux', 'string': 'Qux', 'type': 'many2one', 'fields': [
                        {'name': 'corge', 'type': 'text', 'fields': [], 'model_name': 'base_import.import'},
                     ], 'model_name': 'base_import.import'}
                ]),
            {
                (0, 'foo'): None,
                (1, 'bar'): {'field_path': ['bar'], 'distance': 0},
                (2, 'baz'): {'field_path': ['bob'], 'distance': 0},
                (3, 'qux/corge'): {'field_path': ['qux', 'corge']}
            }
        )


class TestColumnMapping(TransactionCase):

    def test_column_mapping(self):
        import_record = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b"Name,Some Value,value\n"
                    b"chhagan,10,1\n"
                    b"magan,20,2\n",
            'file_type': 'text/csv',
            'file_name': 'data.csv',
        })
        import_record.execute_import(
            ['name', 'somevalue', 'othervalue'],
            ['Name', 'Some Value', 'value'],
            {'quoting': '"', 'separator': ',', 'has_headers': True},
            True
        )
        fields = self.env['base_import.mapping'].search_read(
            [('res_model', '=', 'import.preview')],
            ['column_name', 'field_name']
        )
        self.assertItemsEqual([f['column_name'] for f in fields], ['Name', 'Some Value', 'value'])
        self.assertItemsEqual([f['field_name'] for f in fields], ['somevalue', 'name', 'othervalue'])

    def test_fuzzy_match_distance(self):
        values_to_test = [
            ('opportunities', 'opportinuties'),
            ('opportunities', 'opportunate'),
            ('opportunities', 'operable'),
            ('opportunities', 'purchasing'),
            ('lead_id', 'laed_id'),
            ('lead_id', 'leen_id'),
            ('lead_id', 'let_id_be'),
            ('lead_id', 'not related'),
        ]

        Import = self.env['base_import.import']
        max_distance = 0.2  # see FUZZY_MATCH_DISTANCE. We don't use it here to avoid making test work after modifying this constant.
        for value in values_to_test:
            distance = Import._get_distance(value[0].lower(), value[1].lower())
            model_fields_info = [{'name': value[0], 'string': value[0], 'type': 'char', 'model_name': 'base_import.import'}]
            match = self.env['base_import.import']._get_mapping_suggestion(value[1], model_fields_info, ['char'], {})

            self.assertEqual(
                bool(match), distance < max_distance
            )


class TestPreview(TransactionCase):

    def make_import(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.users',
            'file': "로그인,언어\nbob,1\n".encode('euc_kr'),
            'file_type': 'text/csv',
            'file_name': 'kr_data.csv',
        })
        return import_wizard

    @mute_logger('odoo.addons.base_import.models.base_import')
    def test_encoding(self):
        import_wizard = self.make_import()
        result = import_wizard.parse_preview({
            'quoting': '"',
            'separator': ',',
        })
        self.assertFalse('error' in result)

    @mute_logger('odoo.addons.base_import.models.base_import')
    def test_csv_errors(self):
        import_wizard = self.make_import()

        result = import_wizard.parse_preview({
            'quoting': 'foo',
            'separator': ',',
        })
        self.assertTrue('error' in result)

        result = import_wizard.parse_preview({
            'quoting': '"',
            'separator': 'bob',
        })
        self.assertTrue('error' in result)

    def test_csv_success(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,,\n'
                    b'bar,,4\n'
                    b'qux,5,6\n',
            'file_type': 'text/csv'
        })

        result = import_wizard.parse_preview({
            'quoting': '"',
            'separator': ',',
            'has_headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue']})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        # Order depends on iteration order of fields_get
        self.assertItemsEqual(result['fields'], [
            get_id_field('import.preview'),
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required': False, 'fields': [], 'type': 'char', 'model_name': 'import.preview'},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required': True, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required': False, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
        ])
        self.assertEqual(result['preview'], [['foo', 'bar', 'qux'], ['5'], ['4', '6']])

    @unittest.skipUnless(can_import('xlrd'), "XLRD module not available")
    def test_xls_success(self):
        file_content = file_open('test_import_export/data/test_import.xls', 'rb').read()
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': file_content,
            'file_type': 'application/vnd.ms-excel'
        })

        result = import_wizard.parse_preview({
            'has_headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue']})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            get_id_field('import.preview'),
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required': False, 'fields': [], 'type': 'char', 'model_name': 'import.preview'},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required': True, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required': False, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
        ])
        self.assertEqual(result['preview'], [['foo', 'bar', 'qux'], ['1', '3', '5'], ['2', '4', '6']])

    @unittest.skipUnless(can_import('xlrd.xlsx') or can_import('openpyxl'), "XLRD/XLSX not available")
    def test_xlsx_success(self):
        file_content = file_open('test_import_export/data/test_import.xlsx', 'rb').read()
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': file_content,
            'file_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        result = import_wizard.parse_preview({
            'has_headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue']})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            get_id_field('import.preview'),
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required': False, 'fields': [], 'type': 'char', 'model_name': 'import.preview'},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required': True, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required': False, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
        ])
        self.assertEqual(result['preview'], [['foo', 'bar', 'qux'], ['1', '3', '5'], ['2', '4', '6']])

    @unittest.skipUnless(can_import('odf'), "ODFPY not available")
    def test_ods_success(self):
        file_content = file_open('test_import_export/data/test_import.ods', 'rb').read()
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': file_content,
            'file_type': 'application/vnd.oasis.opendocument.spreadsheet'
        })

        result = import_wizard.parse_preview({
            'has_headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue']})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            get_id_field('import.preview'),
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required': False, 'fields': [], 'type': 'char', 'model_name': 'import.preview'},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required': True, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required': False, 'fields': [], 'type': 'integer', 'model_name': 'import.preview'},
        ])
        self.assertEqual(result['preview'], [['foo', 'bar', 'aux'], ['1', '3', '5'], ['2', '4', '6']])


class test_convert_import_data(TransactionCase):
    """ Tests conversion of base_import.import input into data which
    can be fed to Model.load
    """
    def test_all(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,1,2\n'
                    b'bar,3,4\n'
                    b'qux,5,6\n',
            'file_type': 'text/csv'

        })
        data, fields = import_wizard._convert_import_data(
            ['name', 'somevalue', 'othervalue'],
            {'quoting': '"', 'separator': ',', 'has_headers': True}
        )

        self.assertItemsEqual(fields, ['name', 'somevalue', 'othervalue'])
        self.assertItemsEqual(data, [
            ['foo', '1', '2'],
            ['bar', '3', '4'],
            ['qux', '5', '6'],
        ])

    def test_date_fields(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.complex',
            'file': 'c,d,create_date\n'
                    '"foo","2013年07月18日","2016-10-12 06:06"\n',
            'file_type': 'text/csv'

        })

        results = import_wizard.execute_import(
            ['c', 'd', 'create_date'],
            [],
            {
                'date_format': '%Y年%m月%d日',
                'datetime_format': '%Y-%m-%d %H:%M',
                'quoting': '"',
                'separator': ',',
                'has_headers': True
            }
        )

        # if results empty, no errors
        self.assertItemsEqual(results['messages'], [])

    def test_date_fields_no_options(self):
        self.env['res.lang']._activate_lang('de_DE')
        import_wizard = self.env['base_import.import'].with_context(lang='de_DE').create({
            'res_model': 'import.complex',
            'file': 'c,d,dt\n'
                    '"foo","15.10.2023","15.10.2023 15:15:15"\n',
            'file_type': 'text/csv',
        })

        opts = {
            'date_format': '',
            'datetime_format': '',
            'quoting': '"',
            'separator': ',',
            'float_decimal_separator': '.',
            'float_thousand_separator': ',',
            'has_headers': True,
        }
        result_parse = import_wizard.parse_preview({**opts})

        opts = result_parse['options']
        results = import_wizard.execute_import(
            ['c', 'd', 'dt'],
            [],
            {**opts},
        )

        # if results empty, no errors
        self.assertItemsEqual(results['messages'], [])

    def test_parse_relational_fields(self):
        """ Ensure that relational fields float and date are correctly
        parsed during the import call.
        """
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.complex',
            'file': 'name,parent_id/id,parent_id/date,parent_id/partner_latitude\n'
                    '"foo","__export__.res_partner_1","2017年10月12日","5,69"\n',
            'file_type': 'text/csv'

        })
        options = {
            'date_format': '%Y年%m月%d日',
            'quoting': '"',
            'separator': ',',
            'float_decimal_separator': ',',
            'float_thousand_separator': '.',
            'has_headers': True
        }
        data, import_fields = import_wizard._convert_import_data(
            ['name', 'parent_id/.id', 'parent_id/d', 'parent_id/f'],
            options
        )
        result = import_wizard._parse_import_data(data, import_fields, options)
        # Check if the data 5,69 as been correctly parsed.
        self.assertEqual(float(result[0][-1]), 5.69)
        self.assertEqual(str(result[0][-2]), '2017-10-12')

    def test_parse_scientific_notation(self):
        """ Ensure that scientific notation is correctly converted to decimal """
        import_wizard = self.env['base_import.import']

        test_options = {}
        test_data = [
            ["1E+05"],
            ["1.20E-05"],
            ["1,9e5"],
            ["9,5e-5"],
        ]
        expected_result = [
            ["100000.000000"],
            ["0.000012"],
            ["190000.000000"],
            ["0.000095"],
        ]

        import_wizard._parse_float_from_data(test_data, 0, 'test-name', test_options)
        self.assertEqual(test_data, expected_result)

    def test_filtered(self):
        """ If ``False`` is provided as field mapping for a column,
        that column should be removed from importable data
        """
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,1,2\n'
                    b'bar,3,4\n'
                    b'qux,5,6\n',
            'file_type': 'text/csv'
        })
        data, fields = import_wizard._convert_import_data(
            ['name', False, 'othervalue'],
            {'quoting': '"', 'separator': ',', 'has_headers': True}
        )

        self.assertItemsEqual(fields, ['name', 'othervalue'])
        self.assertItemsEqual(data, [
            ['foo', '2'],
            ['bar', '4'],
            ['qux', '6'],
        ])

    def test_norow(self):
        """ If a row is composed only of empty values (due to having
        filtered out non-empty values from it), it should be removed
        """
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,1,2\n'
                    b',3,\n'
                    b',5,6\n',
            'file_type': 'text/csv'
        })
        data, fields = import_wizard._convert_import_data(
            ['name', False, 'othervalue'],
            {'quoting': '"', 'separator': ',', 'has_headers': True}
        )

        self.assertItemsEqual(fields, ['name', 'othervalue'])
        self.assertItemsEqual(data, [
            ['foo', '2'],
            ['', '6'],
        ])

    def test_empty_rows(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value\n'
                    b'foo,1\n'
                    b'\n'
                    b'bar,2\n'
                    b'     \n'
                    b'\t \n',
            'file_type': 'text/csv'
        })
        data, fields = import_wizard._convert_import_data(
            ['name', 'somevalue'],
            {'quoting': '"', 'separator': ',', 'has_headers': True}
        )

        self.assertItemsEqual(fields, ['name', 'somevalue'])
        self.assertItemsEqual(data, [
            ['foo', '1'],
            ['bar', '2'],
        ])

    def test_nofield(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,1,2\n',
            'file_type': 'text/csv'

        })
        self.assertRaises(ImportValidationError, import_wizard._convert_import_data, [], {'quoting': '"', 'separator': ',', 'has_headers': True})

    def test_falsefields(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': b'name,Some Value,Counter\n'
                    b'foo,1,2\n',
            'file_type': 'text/csv'
        })

        self.assertRaises(
            ImportValidationError,
            import_wizard._convert_import_data,
            [False, False, False],
            {'quoting': '"', 'separator': ',', 'has_headers': True})

    def test_newline_import(self):
        """
        Ensure importing keep newlines
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=1)

        data_row = ["\tfoo\n\tbar", " \"hello\" \n\n 'world' "]

        writer.writerow(["name", "Some Value"])
        writer.writerow(data_row)

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file': output.getvalue().encode(),
            'file_type': 'text/csv',
        })
        data, _ = import_wizard._convert_import_data(
            ['name', 'somevalue'],
            {'quoting': '"', 'separator': ',', 'has_headers': True}
        )

        self.assertItemsEqual(data, [data_row])

    def test_set_empty_value_import(self):
        partners_before = self.env['res.partner'].search([])
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.partner',
            'file': """foo,US,person\n
foo1,Invalid Country,person\n
foo2,US,persons\n""",
            'file_type': 'text/csv'
        })

        results = import_wizard.execute_import(
            ['name', 'country_id', 'company_type'],
            [],
            {
                'quoting': '"',
                'separator': ',',
                'import_set_empty_fields': ['country_id', 'company_type'],
            }
        )
        partners_now = self.env['res.partner'].search([]) - partners_before
        self.assertEqual(len(results['ids']), 3, "should have imported the first 3 records in full, got %s" % results['ids'])

        self.assertEqual(partners_now[0].name, 'foo', "New partner's name should be foo")
        self.assertEqual(partners_now[0].country_id.id, self.env.ref('base.us').id, "Foo partner's country should be US")
        self.assertEqual(partners_now[0].company_type, 'person', "Foo partner's country should be person")

        self.assertEqual(partners_now[1].country_id.id, False, "foo1 partner's country should be False")

        self.assertEqual(partners_now[2].company_type, False, "foo2 partner's country should be False")
        # if results empty, no errors
        self.assertItemsEqual(results['messages'], [])

    def test_skip_record_import(self):
        partners_before = self.env['res.partner'].search([])
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.partner',
            'file': """foo,US,0,person\n
foo1,Invalid Country,0,person\n
foo2,US,False Value,person\n
foo3,US,0,persons\n""",
            'file_type': 'text/csv'
        })

        results = import_wizard.execute_import(
            ['name', 'country_id', 'is_company', 'company_type'],
            [],
            {
                'quoting': '"',
                'separator': ',',
                'import_skip_records': ['country_id', 'is_company', 'company_type']
            }
        )
        partners_now = self.env['res.partner'].search([]) - partners_before

        self.assertEqual(len(results['ids']), 1, "should have imported the first record in full, got %s" % results['ids'])
        self.assertEqual(partners_now.name, 'foo', "New partner's name should be foo")
        # if results empty, no errors
        self.assertItemsEqual(results['messages'], [])

    def test_multi_mapping(self):
        """ Test meant specifically for the '_handle_multi_mapping' that allows mapping multiple
        columns to the same field and merging the values together.

        It makes sure that values of type Char and Many2many are correctly merged. """

        tag1, tag2, tag3 = self.env['res.partner.category'].create([{
            'name': 'tag1',
        }, {
            'name': 'tag2',
        }, {
            'name': 'tag3',
        }])

        file_partner_values = [
            ['Mitchel', 'US', 'Admin', 'The Admin User', 'tag1,tag2', 'tag3'],
            ['Marc', 'US', 'Demo', 'The Demo User', '', 'tag3'],
            ['Joel', 'US', 'Portal', '', 'tag1', 'tag3'],
        ]

        with RecordCapturer(self.env['res.partner'], []) as capture:
            import_wizard = self.env['base_import.import'].create({
                'res_model': 'res.partner',
                'file': '\n'.join([';'.join(partner_values) for partner_values in file_partner_values]),
                'file_type': 'text/csv',
            })

            results = import_wizard.execute_import(
                ['name', 'country_id', 'name', 'name', 'category_id', 'category_id'],
                [],
                {
                    'quoting': '"',
                    'separator': ';',
                },
            )

        # if result is empty, no import error
        self.assertItemsEqual(results['messages'], [])

        partners = capture.records

        self.assertEqual(3, len(partners))
        self.assertEqual('Mitchel Admin The Admin User', partners[0].name)
        self.assertEqual('Marc Demo The Demo User', partners[1].name)
        self.assertEqual('Joel Portal', partners[2].name)

        self.assertEqual(tag1 | tag2 | tag3, partners[0].category_id)
        self.assertEqual(tag3, partners[1].category_id)
        self.assertEqual(tag1 | tag3, partners[2].category_id)


class TestBatching(TransactionCase):
    def _makefile(self, rows):
        f = io.StringIO()
        writer = csv.writer(f, quoting=1)
        writer.writerow(['name', 'counter'])
        for i in range(rows):
            writer.writerow(['n_%d' % i, str(i)])
        return f.getvalue().encode()

    def test_recognize_batched(self):
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.preview',
            'file_type': 'text/csv',
        })

        import_wizard.file = self._makefile(10)
        result = import_wizard.parse_preview({
            'quoting': '"',
            'separator': ',',
            'has_headers': True,
            'limit': 100,
        })
        self.assertIsNone(result.get('error'))
        self.assertIs(result['batch'], False)

        result = import_wizard.parse_preview({
            'quoting': '"',
            'separator': ',',
            'has_headers': True,
            'limit': 5,
        })
        self.assertIsNone(result.get('error'))
        self.assertIs(result['batch'], True)

    def test_limit_on_lines(self):
        """ The limit option should be a limit on the number of *lines*
        imported at at time, not the number of *records*. This is relevant
        when it comes to embedded o2m.

        A big question is whether we want to round up or down (if the limit
        brings us inside a record). Rounding up (aka finishing up the record
        we're currently parsing) seems like a better idea:

        * if the first record has so many sub-lines it hits the limit we still
          want to import it (it's probably extremely rare but it can happen)
        * if we have one line per record, we probably want to import <limit>
          records not <limit-1>, but if we stop in the middle of the "current
          record" we'd always ignore the last record (I think)
        """
        f = io.StringIO()
        writer = csv.writer(f, quoting=1)
        writer.writerow(['name', 'value/value'])
        for record in range(10):
            writer.writerow(['record_%d' % record, '0'])
            for row in range(1, 10):
                writer.writerow(['', str(row)])

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'import.o2m',
            'file_type': 'text/csv',
            'file_name': 'things.csv',
            'file': f.getvalue().encode(),
        })
        opts = {'quoting': '"', 'separator': ',', 'has_headers': True}
        preview = import_wizard.parse_preview({**opts, 'limit': 15})
        self.assertIs(preview['batch'], True)

        results = import_wizard.execute_import(
            ['name', 'value/value'], [],
            {**opts, 'limit': 5}
        )
        self.assertFalse(results['messages'])
        self.assertEqual(len(results['ids']), 1, "should have imported the first record in full, got %s" % results['ids'])
        self.assertEqual(results['nextrow'], 10)

        results = import_wizard.execute_import(
            ['name', 'value/value'], [],
            {**opts, 'limit': 15}
        )
        self.assertFalse(results['messages'])
        self.assertEqual(len(results['ids']), 2, "should have importe the first two records, got %s" % results['ids'])
        self.assertEqual(results['nextrow'], 20)

    def test_batches(self):
        partners_before = self.env['res.partner'].search([])
        opts = {'has_headers': True, 'separator': ',', 'quoting': '"'}

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.partner',
            'file_type': 'text/csv',
            'file_name': 'clients.csv',
            'file': b"""name,email
a,a@example.com
b,b@example.com
,
c,c@example.com
d,d@example.com
e,e@example.com
f,f@example.com
g,g@example.com
"""
        })

        results = import_wizard.execute_import(['name', 'email'], [], {**opts, 'limit': 1})
        self.assertFalse(results['messages'])
        self.assertEqual(len(results['ids']), 1)
        # titlerow is ignored by lastrow's counter
        self.assertEqual(results['nextrow'], 1)
        partners_1 = self.env['res.partner'].search([]) - partners_before
        self.assertEqual(partners_1.name, 'a')

        results = import_wizard.execute_import(['name', 'email'], [], {**opts, 'limit': 2, 'skip': 1})
        self.assertFalse(results['messages'])
        self.assertEqual(len(results['ids']), 2)
        # empty row should also be ignored
        self.assertEqual(results['nextrow'], 3)
        partners_2 = self.env['res.partner'].search([]) - (partners_before | partners_1)
        self.assertEqual(partners_2.mapped('name'), ['b', 'c'])

        results = import_wizard.execute_import(['name', 'email'], [], {**opts, 'limit': 10, 'skip': 3})
        self.assertFalse(results['messages'])
        self.assertEqual(len(results['ids']), 4)
        self.assertEqual(results['nextrow'], 0)
        partners_3 = self.env['res.partner'].search([]) - (partners_before | partners_1 | partners_2)
        self.assertEqual(partners_3.mapped('name'), ['d', 'e', 'f', 'g'])


class test_failures(TransactionCase):
    def test_big_attachments(self):
        """
        Ensure big fields (e.g. b64-encoded image data) can be imported and
        we're not hitting limits of the default CSV parser config
        """
        im = Image.new('RGB', (1920, 1080))
        fout = io.StringIO()

        writer = csv.writer(fout, dialect=None)
        writer.writerows([
            ['name', 'db_datas'],
            ['foo', base64.b64encode(im.tobytes()).decode('ascii')]
        ])

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'ir.attachment',
            'file': fout.getvalue().encode(),
            'file_type': 'text/csv'
        })
        results = import_wizard.execute_import(
            ['name', 'db_datas'],
            [],
            {'has_headers': True, 'separator': ',', 'quoting': '"'})
        self.assertFalse(results['messages'], "results should be empty on successful import")
