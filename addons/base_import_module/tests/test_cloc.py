# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from odoo.tools import cloc
from odoo.tests import tagged, TransactionCase

VALID_XML = """
<templates id="template" xml:space="preserve">
    <t t-name="stock_barcode.LineComponent">
        <div t-if="line.picking_id and line.picking_id.origin" name="origin">
            <i class="oi oi-fw oi-filled" data-icon="description"/>
            <span t-out="line.picking_id.origin" />
        </div>
    </t>
</templates>
"""
VALID_XML_2 = """<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <template id="template_2">
        <t t-name="stock_barcode.LineComponent">
            <div t-if="line.picking_id and line.picking_id.origin" name="origin">
                <i class="oi oi-fw oi-filled" data-icon="description"/>
                <span t-out="line.picking_id.origin" />
            </div>
        </t>
    </template>
    <record id="base.view_company_form" model="ir.ui.view">
        <field name="active" eval="True"/>
    </record>
</odoo>
"""

JS_TEST = r'''
/*
comment
*/

function() {
    return 1+2; // comment
}

function() {
    hello = 4; /*
        comment
    */
    console.log(hello);
    regex = /\/*h/;
    legit_code_counted = 1;
    regex2 = /.*/;
}
'''

SCSS_TEST = '''
/*
  Comment
*/

// Standalone list views
.o_content > .o_list_view > .table-responsive > .table {
    // List views always have the table-sm class, maybe we should remove
    // it (and consider it does not exist) and change the default table paddings
    @include o-list-view-full-width-padding($base-x: $table-cell-padding-x-sm, $base-y: $table-cell-padding-y-sm, $ratio: 2);
    &:not(.o_list_table_grouped) {
        @include media-breakpoint-up(xl) {
            @include o-list-view-full-width-padding($base-x: $table-cell-padding-x-sm, $base-y: $table-cell-padding-y-sm, $ratio: 2.5);
        }
    }

    .o_optional_columns_dropdown_toggle {
        padding: 8px 10px;
    }
}

#content, #footer, #supplement {
   text-overflow: '/*';
   left: 510px;
   width: 200px;
   text-overflow: '*/';
}
'''


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestClocFields(TransactionCase):
    def create_xml_id(self, module, name, rec):
        self.env['ir.model.data'].create({
            'name': name,
            'model': rec._name,
            'res_id': rec.id,
            'module': module,
        })

    def create_field(self, name):
        field = self.env['ir.model.fields'].with_context(studio=True).create({
            'name': name,
            'field_description': name,
            'model': 'res.partner',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'ttype': 'integer',
            'store': False,
            'compute': "for rec in self: rec['x_invoice_count'] = 10",
        })
        # Simulate the effect of https://github.com/odoo/odoo/commit/9afce4805fc8bac45fdba817488aa867fddff69b
        # Updating a module create xml_id of the module even for manual field if it's the original module
        # of the model
        self.create_xml_id('base', name, field)
        return field

    def create_server_action(self, name):
        return self.env['ir.actions.server'].create({
            'name': name,
            'code': """
    for rec in records:
        rec['name'] = test
                """,
            'state': 'code',
            'type': 'ir.actions.server',
            'model_id': self.env.ref('base.model_res_partner').id,
        })

    def create_studio_module(self):
        # Studio module does not exist at this stage, so we simulate it
        # Check for existing module in case the test run on an existing database
        if not self.env['ir.module.module'].search([('name', '=', 'studio_customization')]):
            self.env['ir.module.module'].create({
                'author': 'Odoo S.A.',
                'imported': True,
                'latest_version': '13.0.1.0.0',
                'name': 'studio_customization',
                'state': 'installed',
                'summary': 'Studio Customization',
            })

    def test_ignore_auto_generated_computed_field(self):
        """
            Check that we count custom fields with no module or studio not auto generated
            Having an xml_id but no existing module is consider as not belonging to a module
        """
        f1 = self.create_field('x_invoice_count')
        self.create_xml_id('studio_customization', 'invoice_count', f1)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 0, 'Studio auto generated count field should not be counted in cloc')
        f2 = self.create_field('x_studio_custom_field')
        self.create_xml_id('studio_customization', 'studio_custom', f2)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 1, 'Count other studio computed field')
        self.create_field('x_custom_field')
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 2, 'Count fields without xml_id')
        f4 = self.create_field('x_custom_field_export')
        self.create_xml_id('__export__', 'studio_custom', f4)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 3, 'Count fields with xml_id but without module')

    def test_several_xml_id(self):
        sa = self.create_server_action("Test double xml_id")
        self.create_xml_id("__export__", "first", sa)
        self.create_xml_id("base", "second", sa)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 2, 'Count Should count SA with a non standard xml_id')
        self.create_xml_id("__import__", "third", sa)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 2, 'SA with several xml_id should be counted only once')

    def test_cloc_exclude_xml_id(self):
        sa = self.create_server_action("Test double xml_id")
        self.create_xml_id("__cloc_exclude__", "sa_first", sa)
        self.create_xml_id("__upgrade__", "sa_second", sa)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 0, 'Should not count SA with cloc_exclude xml_id')

        f1 = self.create_field('x_invoice_count')
        self.create_xml_id("__cloc_exclude__", "field_first", f1)
        self.create_xml_id("__upgrade__", "field_second", f1)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 0, 'Should not count Field with cloc_exclude xml_id')

    def test_field_no_xml_id(self):
        self.env['ir.model.fields'].create({
            'name': "x_no_xml_id",
            'field_description': "no_xml_id",
            'model': 'res.partner',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'ttype': 'integer',
            'store': False,
            'compute': "for rec in self: rec['x_invoice_count'] = 10",
        })
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 1, 'Should count field with no xml_id at all')

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
        self.create_xml_id('imported_module', 'import_field', f1)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('imported_module', 0), 1, 'Count fields with xml_id of imported module')

    def test_fields_from_studio(self):
        self.create_studio_module()
        f1 = self.create_field('x_field_count')
        self.create_xml_id('studio_customization', 'field_count', f1)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('studio_customization', 0), 0, "Don't count field generated by studio")
        f2 = self.create_field('x_studio_manual_field')
        self.create_xml_id('studio_customization', 'manual_field', f2)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('studio_customization', 0), 1, "Count manual field created via studio")

    def test_fields_module_name(self):
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
        self.create_xml_id('imported_module', 'import_field', f1)
        self.create_xml_id('__export__', 'import_field', f1)

        sa = self.create_server_action("Test imported double xml_id")
        self.create_xml_id("imported_module", "first", sa)
        self.create_xml_id("__export__", "second", sa)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('imported_module', 0), 3)

    def test_count_qweb_imported_module(self):
        self.env['ir.module.module'].create({
            'author': 'Odoo S.A.',
            'imported': True,
            'latest_version': '15.0.1.0.0',
            'name': 'test_imported_module',
            'state': 'installed',
            'summary': 'Test imported module for cloc',
        })
        self.create_studio_module()

        qweb_view = self.env['ir.ui.view'].create({
            "name": "Qweb Test",
            "type": "qweb",
            "mode": "primary",
            "arch_base": "<html>\n  <body>\n    <t t-out=\"Hello World\"/>\n  </body>\n</html>",
        })
        self.create_xml_id('test_imported_module', "qweb_view_test", qweb_view)

        # Add qweb view from non imported module
        qweb_view = self.env['ir.ui.view'].create({
            "name": "Qweb Test",
            "type": "qweb",
            "arch_base": "<html>\n  <body>\n    <t t-out=\"Hello World\"/>\n  </body>\n</html>",
        })
        self.create_xml_id("studio_customization", "qweb_view_test", qweb_view)

        # Add form view from module
        form_view = self.env['ir.ui.view'].create({
            "name": "Test partner",
            "type": "form",
            "model": "res.partner",
            "arch_base": "<form>\n  <field name=\"name\" \n         invisible=\"1\" />\n</form>",
        })
        self.create_xml_id("test_imported_module", "form_view_test", form_view)

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
            'author': 'Odoo S.A.',
        })

        stream = BytesIO()
        with ZipFile(stream, 'w') as archive:
            archive.writestr('test_imported_module/__manifest__.py', manifest_content)
            archive.writestr('test_imported_module/static/src/js/test.js', JS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.scss', SCSS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.xml', VALID_XML)

        # Import test module
        self.env['ir.module.module']._import_zipfile(stream)
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 35)

    def test_exclude_qweb(self):
        self.env['ir.module.module'].create({
            'author': 'Odoo S.A.',
            'imported': True,
            'latest_version': '15.0.1.0.0',
            'name': 'test_imported_module',
            'state': 'installed',
            'summary': 'Test imported module for cloc',
        })

        qweb_view = self.env['ir.ui.view'].create({
            "name": "Qweb Test",
            "type": "qweb",
            "mode": "primary",
            "arch_base": "<html>\n  <body>\n    <t t-out=\"Hello World\"/>\n  </body>\n</html>",
        })
        self.create_xml_id('test_imported_module', "qweb_view_test", qweb_view)
        self.create_xml_id('__cloc_exclude__', "qweb_view_test", qweb_view)

        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 0, "Do not count view with cloc_exclude")

    def test_exclude_attachment_imported_module(self):
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
            'author': 'Odoo S.A.',
        })

        stream = BytesIO()
        with ZipFile(stream, 'w') as archive:
            archive.writestr('test_imported_module/__manifest__.py', manifest_content)
            archive.writestr('test_imported_module/static/src/js/test.js', JS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.scss', SCSS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.xml', VALID_XML)

        id_names = [
            'attachment_/test_imported_module/static/src/js/test_js',
            'attachment_/test_imported_module/static/src/js/test_scss',
            'attachment_/test_imported_module/static/src/js/test_xml',
        ]

        # Import test module
        self.env['ir.module.module']._import_zipfile(stream)
        # Create exclude xml_id
        for name in id_names:
            rec = self.env.ref(f'test_imported_module.{name}')
            self.create_xml_id('__cloc_exclude__', name, rec)

        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 0)

    def test_exclude_cloc_imported_module(self):
        manifest_content = json.dumps({
            'name': 'test_imported_module',
            'description': 'Test',
            'data': ['data/test.xml'],
            'assets': {
                'web.assets_backend': [
                    'test_imported_module/static/src/js/test.js',
                    'test_imported_module/static/src/js/test.scss',
                    'test_imported_module/static/src/js/test.xml',
                ]
            },
            'cloc_exclude': [
                    'static/**/*',
                    'data/test.xml',
            ],
            'license': 'LGPL-3',
            'author': 'Odoo S.A.',
        })

        stream = BytesIO()
        with ZipFile(stream, 'w', compression=ZIP_DEFLATED) as archive:
            archive.writestr('test_imported_module/__manifest__.py', manifest_content)
            archive.writestr('test_imported_module/static/src/js/test.js', JS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.scss', SCSS_TEST)
            archive.writestr('test_imported_module/static/src/js/test.xml', VALID_XML)
            archive.writestr('test_imported_module/data/test.xml', VALID_XML_2)
        # Import test module
        self.env['ir.module.module']._import_zipfile(stream)

        # Import a second time to upgrade, test that it does not raise error
        self.env['ir.module.module']._import_zipfile(stream)

        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('test_imported_module', 0), 0)

        # Uninstall data module
        self.env['ir.module.module'].search([('name', '=', 'test_imported_module')]).module_uninstall()

        # Check that the database is cleaned after uninstallation
        attachments = self.env['ir.attachment'].search([('url', 'ilike', 'test_imported_module/static/src/js/test_js')])
        self.assertFalse(attachments, "No more attachment from assets should remain in the db")

        assets_data = self.env['ir.model.data'].search([
            ('model', '=', 'ir.asset'),
            ('module', '=', 'test_imported_module'),
        ])
        self.assertFalse(
            self.env['ir.asset'].search([('id', 'in', assets_data.mapped('res_id'))]),
            "No more assets should remain in the db",
        )

        irmodeldata = self.env['ir.model.data'].search([('module', '=', '__cloc_exclude__')])
        self.assertTrue(
            len(irmodeldata) == 1 and irmodeldata.res_id == self.env.ref('base.view_company_form').id,
            "Only base form view should remain excluded",
        )
