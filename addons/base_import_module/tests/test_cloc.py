# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from io import BytesIO
from zipfile import ZipFile

from odoo.tools import cloc
from odoo.addons.base.tests import test_cloc

VALID_XML = """
<templates id="template" xml:space="preserve">
    <t t-name="stock_barcode.LineComponent">
        <div t-if="line.picking_id and line.picking_id.origin" name="origin">
            <i class="fa fa-fw fa-file" />
            <span t-esc="line.picking_id.origin" />
        </div>
    </t>
</templates>
"""

class TestClocFields(test_cloc.TestClocCustomization):

    def test_fields_from_import_module(self):
        """
            Check that custom computed fields installed with an imported module
            is counted as customization
        """
        self.env['ir.module.module'].create({
            'name': 'imported_module',
            'state': 'installed',
            'imported': True,
        })
        f1 = self.create_field('x_imported_field')
        self.create_xml_id('import_field', 'ir.model.fields', f1.id, 'imported_module')
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('imported_module', 0), 1, 'Count fields with xml_id of imported module')
        f2 = self.create_field('x_base_field')
        self.create_xml_id('base_field', 'ir.model.fields', f2.id, 'base')
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('base', 0), 0, "Don't count fields from standard module")

    def test_count_qweb_imported_module(self):
        self.env['ir.module.module'].create({
            'author': 'Odoo',
            'imported': True,
            'latest_version': '15.0.1.0.0',
            'name': 'test_imported_module',
            'state': 'installed',
            'summary': 'Test imported module for cloc',
        })
        # Studio module does not exist at this stage, so we simulate it
        # Check for existing module in case the test run on an existing database
        if not self.env['ir.module.module'].search([('name', '=', 'studio_customization')]):
            self.env['ir.module.module'].create({
                'author': 'Odoo',
                'imported': True,
                'latest_version': '15.0.1.0.0',
                'name': 'studio_customization',
                'state': 'installed',
                'summary': 'Studio Customization',
            })
        qweb_view = self.env['ir.ui.view'].create({
            "name": "Qweb Test",
            "type": "qweb",
            "mode": "primary",
            "arch_base": "<html>\n  <body>\n    <t t-out=\"Hello World\"/>\n  </body>\n</html>",
        })
        self.create_xml_id("qweb_view_test", 'ir.ui.view', qweb_view.id, 'test_imported_module')

        # Add qweb view from non imported module
        qweb_view = self.env['ir.ui.view'].create({
            "name": "Qweb Test",
            "type": "qweb",
            "arch_base": "<html>\n  <body>\n    <t t-out=\"Hello World\"/>\n  </body>\n</html>",
        })
        self.create_xml_id("qweb_view_test", 'ir.ui.view', qweb_view.id)

        # Add form view from module
        form_view = self.env['ir.ui.view'].create({
            "name": "Test partner",
            "type": "form",
            "model": "res.partner",
            "arch_base": "<form>\n  <field name=\"name\" \n         invisible=\"1\" />\n</form>",
        })
        self.create_xml_id("form_view_test", 'ir.ui.view', form_view.id, 'test_imported_module')

        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 5, "Count only qweb view from imported module")
        self.assertEqual(cl.code.get('studio_customization', 0), 0, "Do not count from studio_customization module")

    def test_count_attachment_imported_module(self):
        manifest_content = json.dumps({
            'name': 'test_imported_module',
            'description': 'Test',
            'assets': {
                'web.assets_backend': [
                    'test_imported_module/static/src/js/test.js',
                    'test_imported_module/static/src/css/test.scss',
                ]
            },
            'license': 'LGPL-3',
        })

        stream = BytesIO()
        with ZipFile(stream, 'w') as archive:
            archive.writestr('test_imported_module/__manifest__.py', manifest_content)
            archive.writestr('test_imported_module/static/src/js/test.js', test_cloc.JS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.scss', test_cloc.SCSS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.xml', VALID_XML)

        # Import test module
        self.env['ir.module.module'].import_zipfile(stream)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 35)
