# -*- encoding: utf-8 -*-
import unittest

from openerp.tests.common import TransactionCase, can_import
from openerp.modules.module import get_module_resource


from .. import models

ID_FIELD = {
    'id': 'id',
    'name': 'id',
    'string': "External ID",
    'required': False,
    'fields': [],
}

def make_field(name='value', string='unknown', required=False, fields=[]):
    return [
        ID_FIELD,
        {'id': name, 'name': name, 'string': string, 'required': required, 'fields': fields},
    ]

def sorted_fields(fields):
    """ recursively sort field lists to ease comparison """
    recursed = [dict(field, fields=sorted_fields(field['fields'])) for field in fields]
    return sorted(recursed, key=lambda field: field['id'])

class BaseImportCase(TransactionCase):
    def assertEqualFields(self, fields1, fields2):
        self.assertEqual(sorted_fields(fields1), sorted_fields(fields2))

class test_basic_fields(BaseImportCase):
    def get_fields(self, field):
        return self.registry('base_import.import')\
            .get_fields(self.cr, self.uid, 'base_import.tests.models.' + field)

    def test_base(self):
        """ A basic field is not required """
        self.assertEqualFields(self.get_fields('char'), make_field())

    def test_required(self):
        """ Required fields should be flagged (so they can be fill-required) """
        self.assertEqualFields(self.get_fields('char.required'), make_field(required=True))

    def test_readonly(self):
        """ Readonly fields should be filtered out"""
        self.assertEqualFields(self.get_fields('char.readonly'), [ID_FIELD])

    def test_readonly_states(self):
        """ Readonly fields with states should not be filtered out"""
        self.assertEqualFields(self.get_fields('char.states'), make_field())

    def test_readonly_states_noreadonly(self):
        """ Readonly fields with states having nothing to do with
        readonly should still be filtered out"""
        self.assertEqualFields(self.get_fields('char.noreadonly'), [ID_FIELD])

    def test_readonly_states_stillreadonly(self):
        """ Readonly fields with readonly states leaving them readonly
        always... filtered out"""
        self.assertEqualFields(self.get_fields('char.stillreadonly'), [ID_FIELD])

    def test_m2o(self):
        """ M2O fields should allow import of themselves (name_get),
        their id and their xid"""
        self.assertEqualFields(self.get_fields('m2o'), make_field(fields=[
            {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': []},
            {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': False, 'fields': []},
        ]))
    
    def test_m2o_required(self):
        """ If an m2o field is required, its three sub-fields are
        required as well (the client has to handle that: requiredness
        is id-based)
        """
        self.assertEqualFields(self.get_fields('m2o.required'), make_field(required=True, fields=[
            {'id': 'value', 'name': 'id', 'string': 'External ID', 'required': True, 'fields': []},
            {'id': 'value', 'name': '.id', 'string': 'Database ID', 'required': True, 'fields': []},
        ]))

class test_o2m(BaseImportCase):
    def get_fields(self, field):
        return self.registry('base_import.import')\
            .get_fields(self.cr, self.uid, 'base_import.tests.models.' + field)

    def test_shallow(self):
        self.assertEqualFields(self.get_fields('o2m'), make_field(fields=[
            ID_FIELD,
            # FIXME: should reverse field be ignored?
            {'id': 'parent_id', 'name': 'parent_id', 'string': 'unknown', 'required': False, 'fields': [
                {'id': 'parent_id', 'name': 'id', 'string': 'External ID', 'required': False, 'fields': []},
                {'id': 'parent_id', 'name': '.id', 'string': 'Database ID', 'required': False, 'fields': []},
            ]},
            {'id': 'value', 'name': 'value', 'string': 'unknown', 'required': False, 'fields': []},
        ]))

class test_match_headers_single(TransactionCase):
    def test_match_by_name(self):
        match = self.registry('base_import.import')._match_header(
            'f0', [{'name': 'f0'}], {})

        self.assertEqual(match, [{'name': 'f0'}])

    def test_match_by_string(self):
        match = self.registry('base_import.import')._match_header(
            'some field', [{'name': 'bob', 'string': "Some Field"}], {})

        self.assertEqual(match, [{'name': 'bob', 'string': "Some Field"}])

    def test_nomatch(self):
        match = self.registry('base_import.import')._match_header(
            'should not be', [{'name': 'bob', 'string': "wheee"}], {})

        self.assertEqual(match, [])

    def test_recursive_match(self):
        f = {
            'name': 'f0',
            'string': "My Field",
            'fields': [
                {'name': 'f0', 'string': "Sub field 0", 'fields': []},
                {'name': 'f1', 'string': "Sub field 2", 'fields': []},
            ]
        }
        match = self.registry('base_import.import')._match_header(
            'f0/f1', [f], {})

        self.assertEqual(match, [f, f['fields'][1]])

    def test_recursive_nomatch(self):
        """ Match first level, fail to match second level
        """
        f = {
            'name': 'f0',
            'string': "My Field",
            'fields': [
                {'name': 'f0', 'string': "Sub field 0", 'fields': []},
                {'name': 'f1', 'string': "Sub field 2", 'fields': []},
            ]
        }
        match = self.registry('base_import.import')._match_header(
            'f0/f2', [f], {})

        self.assertEqual(match, [])

class test_match_headers_multiple(TransactionCase):
    def test_noheaders(self):
        self.assertEqual(
            self.registry('base_import.import')._match_headers(
                [], [], {}),
            (None, None)
        )
    def test_nomatch(self):
        self.assertEqual(
            self.registry('base_import.import')._match_headers(
                iter([
                    ['foo', 'bar', 'baz', 'qux'],
                    ['v1', 'v2', 'v3', 'v4'],
                ]),
                [],
                {'headers': True}),
            (
                ['foo', 'bar', 'baz', 'qux'],
                dict.fromkeys(range(4))
            )
        )

    def test_mixed(self):
        self.assertEqual(
            self.registry('base_import.import')._match_headers(
                iter(['foo bar baz qux/corge'.split()]),
                [
                    {'name': 'bar', 'string': 'Bar'},
                    {'name': 'bob', 'string': 'Baz'},
                    {'name': 'qux', 'string': 'Qux', 'fields': [
                        {'name': 'corge', 'fields': []},
                     ]}
                ],
                {'headers': True}),
            (['foo', 'bar', 'baz', 'qux/corge'], {
                0: None,
                1: ['bar'],
                2: ['bob'],
                3: ['qux', 'corge'],
            })
        )

class test_preview(TransactionCase):
    def make_import(self):
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'res.users',
            'file': u"로그인,언어\nbob,1\n".encode('euc_kr'),
            'file_type': 'text/csv',
            'file_name': 'kr_data.csv',
        })
        return Import, id

    def test_encoding(self):
        Import, id = self.make_import()
        result = Import.parse_preview(self.cr, self.uid, id, {
                'quoting': '"',
                'separator': ',',
        })
        self.assertTrue('error' in result)

    def test_csv_errors(self):
        Import, id = self.make_import()

        result = Import.parse_preview(self.cr, self.uid, id, {
                'quoting': 'foo',
                'separator': ',',
                'encoding': 'euc_kr',
        })
        self.assertTrue('error' in result)

        result = Import.parse_preview(self.cr, self.uid, id, {
                'quoting': '"',
                'separator': 'bob',
                'encoding': 'euc_kr',
        })
        self.assertTrue('error' in result)

    def test_csv_success(self):
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n'
                    'bar,3,4\n'
                    'qux,5,6\n',
            'file_type': 'text/csv'
        })

        result = Import.parse_preview(self.cr, self.uid, id, {
            'quoting': '"',
            'separator': ',',
            'headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue'], 2: None})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        # Order depends on iteration order of fields_get
        self.assertItemsEqual(result['fields'], [
            ID_FIELD,
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required':False, 'fields': []},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required':True, 'fields': []},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required':False, 'fields': []},
        ])
        self.assertEqual(result['preview'], [
            ['foo', '1', '2'],
            ['bar', '3', '4'],
            ['qux', '5', '6'],
        ])
        # Ensure we only have the response fields we expect
        self.assertItemsEqual(result.keys(), ['matches', 'headers', 'fields', 'preview'])

    @unittest.skipUnless(can_import('xlrd'), "XLRD module not available")
    def test_xls_success(self):

        Import = self.registry('base_import.import')
        xls_file_path = get_module_resource('base_import', 'tests', 'test.xls')
        file_content = open(xls_file_path, 'rb').read()
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': file_content,
            'file_type': 'application/vnd.ms-excel'
        })

        result = Import.parse_preview(self.cr, self.uid, id, {
            'headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue'], 2: None})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            ID_FIELD,
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required':False, 'fields': []},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required':True, 'fields': []},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required':False, 'fields': []},
        ])
        self.assertEqual(result['preview'], [
            ['foo', '1', '2'],
            ['bar', '3', '4'],
            ['qux', '5', '6'],
        ])
        # Ensure we only have the response fields we expect
        self.assertItemsEqual(result.keys(), ['matches', 'headers', 'fields', 'preview'])

    @unittest.skipUnless(can_import('xlrd.xlsx'), "XLRD/XLSX not available")
    def test_xlsx_success(self):
        Import = self.registry('base_import.import')
        xlsx_file_path = get_module_resource('base_import', 'tests', 'test.xlsx')
        file_content = open(xlsx_file_path, 'rb').read()
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': file_content,
            'file_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        result = Import.parse_preview(self.cr, self.uid, id, {
            'headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue'], 2: None})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            ID_FIELD,
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required':False, 'fields': []},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required':True, 'fields': []},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required':False, 'fields': []},
        ])
        self.assertEqual(result['preview'], [
            ['foo', '1', '2'],
            ['bar', '3', '4'],
            ['qux', '5', '6'],
        ])
        # Ensure we only have the response fields we expect
        self.assertItemsEqual(result.keys(), ['matches', 'headers', 'fields', 'preview'])

    @unittest.skipUnless(can_import('odf'), "ODFPY not available")
    def test_ods_success(self):
        Import = self.registry('base_import.import')
        ods_file_path = get_module_resource('base_import', 'tests', 'test.ods')
        file_content = open(ods_file_path, 'rb').read()
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': file_content,
            'file_type': 'application/vnd.oasis.opendocument.spreadsheet'
        })

        result = Import.parse_preview(self.cr, self.uid, id, {
            'headers': True,
        })
        self.assertIsNone(result.get('error'))
        self.assertEqual(result['matches'], {0: ['name'], 1: ['somevalue'], 2: None})
        self.assertEqual(result['headers'], ['name', 'Some Value', 'Counter'])
        self.assertItemsEqual(result['fields'], [
            ID_FIELD,
            {'id': 'name', 'name': 'name', 'string': 'Name', 'required':False, 'fields': []},
            {'id': 'somevalue', 'name': 'somevalue', 'string': 'Some Value', 'required':True, 'fields': []},
            {'id': 'othervalue', 'name': 'othervalue', 'string': 'Other Variable', 'required':False, 'fields': []},
        ])
        self.assertEqual(result['preview'], [
            ['foo', '1', '2'],
            ['bar', '3', '4'],
            ['aux', '5', '6'],
        ])
        # Ensure we only have the response fields we expect
        self.assertItemsEqual(result.keys(), ['matches', 'headers', 'fields', 'preview'])

class test_convert_import_data(TransactionCase):
    """ Tests conversion of base_import.import input into data which
    can be fed to Model.import_data
    """
    def test_all(self):
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n'
                    'bar,3,4\n'
                    'qux,5,6\n',
            'file_type': 'text/csv'

        })
        record = Import.browse(self.cr, self.uid, id)
        data, fields = Import._convert_import_data(
            record, ['name', 'somevalue', 'othervalue'],
            {'quoting': '"', 'separator': ',', 'headers': True,})

        self.assertItemsEqual(fields, ['name', 'somevalue', 'othervalue'])
        self.assertItemsEqual(data, [
            ('foo', '1', '2'),
            ('bar', '3', '4'),
            ('qux', '5', '6'),
        ])

    def test_filtered(self):
        """ If ``False`` is provided as field mapping for a column,
        that column should be removed from importable data
        """
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n'
                    'bar,3,4\n'
                    'qux,5,6\n',
            'file_type': 'text/csv'
        })
        record = Import.browse(self.cr, self.uid, id)
        data, fields = Import._convert_import_data(
            record, ['name', False, 'othervalue'],
            {'quoting': '"', 'separator': ',', 'headers': True,})

        self.assertItemsEqual(fields, ['name', 'othervalue'])
        self.assertItemsEqual(data, [
            ('foo', '2'),
            ('bar', '4'),
            ('qux', '6'),
        ])

    def test_norow(self):
        """ If a row is composed only of empty values (due to having
        filtered out non-empty values from it), it should be removed
        """
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n'
                    ',3,\n'
                    ',5,6\n',
            'file_type': 'text/csv'
        })
        record = Import.browse(self.cr, self.uid, id)
        data, fields = Import._convert_import_data(
            record, ['name', False, 'othervalue'],
            {'quoting': '"', 'separator': ',', 'headers': True,})

        self.assertItemsEqual(fields, ['name', 'othervalue'])
        self.assertItemsEqual(data, [
            ('foo', '2'),
            ('', '6'),
        ])

    def test_empty_rows(self):
        Import = self.registry('base_import.import')
        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value\n'
                    'foo,1\n'
                    '\n'
                    'bar,2\n'
                    '     \n'
                    '\t \n',
            'file_type': 'text/csv'
        })
        record = Import.browse(self.cr, self.uid, id)
        data, fields = Import._convert_import_data(
            record, ['name', 'somevalue'],
            {'quoting': '"', 'separator': ',', 'headers': True,})

        self.assertItemsEqual(fields, ['name', 'somevalue'])
        self.assertItemsEqual(data, [
            ('foo', '1'),
            ('bar', '2'),
        ])

    def test_nofield(self):
        Import = self.registry('base_import.import')

        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n',
            'file_type': 'text/csv'

        })

        record = Import.browse(self.cr, self.uid, id)
        self.assertRaises(
            ValueError,
            Import._convert_import_data,
            record, [],
            {'quoting': '"', 'separator': ',', 'headers': True,})

    def test_falsefields(self):
        Import = self.registry('base_import.import')

        id = Import.create(self.cr, self.uid, {
            'res_model': 'base_import.tests.models.preview',
            'file': 'name,Some Value,Counter\n'
                    'foo,1,2\n',
            'file_type': 'text/csv'
        })

        record = Import.browse(self.cr, self.uid, id)
        self.assertRaises(
            ValueError,
            Import._convert_import_data,
            record, [False, False, False],
            {'quoting': '"', 'separator': ',', 'headers': True,})

class test_failures(TransactionCase):
    def test_big_attachments(self):
        """
        Ensure big fields (e.g. b64-encoded image data) can be imported and
        we're not hitting limits of the default CSV parser config
        """
        import csv, cStringIO
        from PIL import Image

        im = Image.new('RGB', (1920, 1080))
        fout = cStringIO.StringIO()

        writer = csv.writer(fout, dialect=None)
        writer.writerows([
            ['name', 'db_datas'],
            ['foo', im.tobytes().encode('base64')]
        ])

        Import = self.env['base_import.import']
        imp = Import.create({
            'res_model': 'ir.attachment',
            'file': fout.getvalue(),
            'file_type': 'text/csv'
        })
        [results] = imp.do(
            ['name', 'db_datas'],
            {'headers': True, 'separator': ',', 'quoting': '"'})
        self.assertFalse(
            results, "results should be empty on successful import")
