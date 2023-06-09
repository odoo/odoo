# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import os
import tempfile
import zipfile

from unittest.mock import patch

from odoo.addons import __path__ as __addons_path__
from odoo.tools import mute_logger
from odoo.tests.common import TransactionCase, HttpCase

class TestImportModule(TransactionCase):
    def import_zipfile(self, files):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as zipf:
            for path, data in files:
                zipf.writestr(path, data)
        return self.env['ir.module.module'].import_zipfile(archive)

    def test_import_zip(self):
        """Assert the behaviors expected by the module import feature using a ZIP archive"""
        files = [
            ('foo/__manifest__.py', b"{'data': ['data.xml', 'res.partner.csv', 'data.sql']}"),
            ('foo/data.xml', b"""
                <data>
                    <record id="foo" model="res.partner">
                        <field name="name">foo</field>
                    </record>
                </data>
            """),
            ('foo/res.partner.csv',
                b'"id","name"\n' \
                b'bar,bar'
            ),
            ('foo/data.sql', b"INSERT INTO res_partner (active, name) VALUES (true, 'baz');"),
            ('foo/static/css/style.css', b".foo{color: black;}"),
            ('foo/static/js/foo.js', b"console.log('foo')"),
            ('bar/__manifest__.py', b"{'data': ['data.xml']}"),
            ('bar/data.xml', b"""
                <data>
                    <record id="foo" model="res.country">
                        <field name="name">foo</field>
                    </record>
                </data>
            """),
        ]
        self.import_zipfile(files)
        self.assertEqual(self.env.ref('foo.foo')._name, 'res.partner')
        self.assertEqual(self.env.ref('foo.foo').name, 'foo')
        self.assertEqual(self.env.ref('foo.bar')._name, 'res.partner')
        self.assertEqual(self.env.ref('foo.bar').name, 'bar')
        self.assertEqual(self.env['res.partner'].search_count([('name', '=', 'baz')]), 1)

        self.assertEqual(self.env.ref('bar.foo')._name, 'res.country')
        self.assertEqual(self.env.ref('bar.foo').name, 'foo')

        for path, data in files:
            if path.split('/')[1] == 'static':
                static_attachment = self.env['ir.attachment'].search([('url', '=', '/%s' % path)])
                self.assertEqual(static_attachment.name, os.path.basename(path))
                self.assertEqual(static_attachment.datas, base64.b64encode(data))

    def test_import_zip_invalid_manifest(self):
        """Assert the expected behavior when import a ZIP module with an invalid manifest"""
        files = [
            ('foo/__manifest__.py', b"foo")
        ]
        with mute_logger("odoo.addons.base_import_module.models.ir_module"):
            result = self.import_zipfile(files)
        self.assertIn("Error while importing module 'foo'", result[0])

    def test_import_zip_data_not_in_manifest(self):
        """Assert a data file not mentioned in the manifest is not imported"""
        files = [
            ('foo/__manifest__.py', b"{'data': ['foo.xml']}"),
            ('foo/foo.xml', b"""
                <data>
                    <record id="foo" model="res.partner">
                        <field name="name">foo</field>
                    </record>
                </data>
            """),
            ('foo/bar.xml', b"""
                <data>
                    <record id="bar" model="res.partner">
                        <field name="name">bar</field>
                    </record>
                </data>
            """),
        ]
        self.import_zipfile(files)
        self.assertEqual(self.env.ref('foo.foo').name, 'foo')
        self.assertFalse(self.env.ref('foo.bar', raise_if_not_found=False))

    def test_import_zip_ignore_unexpected_data_extension(self):
        """Assert data files using an unexpected extensions are correctly ignored"""
        files = [
            ('foo/__manifest__.py', b"{'data': ['res.partner.xls']}"),
            ('foo/res.partner.xls',
                b'"id","name"\n' \
                b'foo,foo'
            ),
        ]
        with self.assertLogs('odoo.addons.base_import_module.models.ir_module') as log_catcher:
            self.import_zipfile(files)
            self.assertEqual(len(log_catcher.output), 1)
            self.assertIn('module foo: skip unsupported file res.partner.xls', log_catcher.output[0])
            self.assertFalse(self.env.ref('foo.foo', raise_if_not_found=False))

    def test_import_zip_extract_only_useful(self):
        """Assert only the data and static files are extracted of the ZIP archive during the module import"""
        files = [
            ('foo/__manifest__.py', b"{'data': ['data.xml', 'res.partner.xls']}"),
            ('foo/data.xml', b"""
                <data>
                    <record id="foo" model="res.partner">
                        <field name="name">foo</field>
                    </record>
                </data>
            """),
            ('foo/res.partner.xls',
                b'"id","name"\n' \
                b'foo,foo'
            ),
            ('foo/static/css/style.css', b".foo{color: black;}"),
            ('foo/foo.py', b"foo = 42"),
        ]
        extracted_files = []
        addons_path = []
        origin_import_module = type(self.env['ir.module.module'])._import_module
        def _import_module(self, *args, **kwargs):
            _module, path = args
            for root, _dirs, files in os.walk(path):
                for file in files:
                    extracted_files.append(os.path.relpath(os.path.join(root, file), path))
            addons_path.extend(__addons_path__)
            return origin_import_module(self, *args, **kwargs)
        with patch.object(type(self.env['ir.module.module']), '_import_module', _import_module):
            self.import_zipfile(files)
        self.assertIn(
            '__manifest__.py', extracted_files,
            "__manifest__.py must be in the extracted files")
        self.assertIn(
            'data.xml', extracted_files,
            "data.xml must be in the extracted files as its in the manifest's data")
        self.assertIn(
            'static/css/style.css', extracted_files,
            "style.css must be in the extracted files as its in the static folder")
        self.assertNotIn(
            'res.partner.xls', extracted_files,
            "res.partner.xls must not be in the extracted files as it uses an unsupported extension of data file")
        self.assertNotIn(
            'foo.py', extracted_files,
            "foo.py must not be in the extracted files as its not the manifest's data")
        self.assertFalse(
            set(addons_path).difference(__addons_path__),
            'No directory must be added in the addons path during import')

    def test_import_module_addons_path(self):
        """Assert it's possible to import a module using directly `_import_module` without zip from the addons path"""
        files = [
            ('foo/__manifest__.py', b"{'data': ['data.xml']}"),
            ('foo/data.xml', b"""
                <data>
                    <record id="foo" model="res.partner">
                        <field name="name">foo</field>
                    </record>
                </data>
            """),
            ('foo/static/css/style.css', b".foo{color: black;}"),
        ]
        with tempfile.TemporaryDirectory() as module_dir:
            for path, data in files:
                os.makedirs(os.path.join(module_dir, os.path.dirname(path)), exist_ok=True)
                with open(os.path.join(module_dir, path), 'wb') as fp:
                    fp.write(data)
            try:
                __addons_path__.append(module_dir)
                self.env['ir.module.module']._import_module('foo', os.path.join(module_dir, 'foo'))
            finally:
                __addons_path__.remove(module_dir)

        self.assertEqual(self.env.ref('foo.foo')._name, 'res.partner')
        self.assertEqual(self.env.ref('foo.foo').name, 'foo')
        static_path, static_data = files[2]
        static_attachment = self.env['ir.attachment'].search([('url', '=', '/%s' % static_path)])
        self.assertEqual(static_attachment.name, os.path.basename(static_path))
        self.assertEqual(static_attachment.datas, base64.b64encode(static_data))


class TestImportModuleHttp(TestImportModule, HttpCase):
    def test_import_module_icon(self):
        """Assert import a module with an icon result in the module displaying the icon in the apps menu,
        and with the base module icon if module without icon"""
        files = [
            ('foo/__manifest__.py', b"{'name': 'foo'}"),
            ('foo/static/description/icon.png', b"foo_icon"),
            ('bar/__manifest__.py', b"{'name': 'bar'}"),
        ]
        self.import_zipfile(files)
        foo_icon_path, foo_icon_data = files[1]
        # Assert icon of module foo, which must be the icon provided in the zip
        self.assertEqual(self.url_open('/' + foo_icon_path).content, foo_icon_data)
        # Assert icon of module bar, which must be the icon of the base module as none was provided
        self.assertEqual(self.env.ref('base.module_bar').icon_image, self.env.ref('base.module_base').icon_image)
