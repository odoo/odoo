# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import cloc
from odoo.tests import TransactionCase, tagged

XML_TEST = """<!-- Comment -->
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <node>Line</node>
    <!-- Comment -->
    <node>Line</node>
    <!-- Comment
        Multi
    Line -->
    <![CDATA[
        Line
    ]]>
    <![CDATA[
        <!-- comment in CDATA -->
        cdata Line
    yes6]]>
    <![CDATA[<!-- not a comment-->]]>
    <![CDATA[<!-- not a comment
     but counted as is
    -->]]>
    <!-- <![CDATA[ This is a valid comment ]]> -->
    <!-- <![CDATA[ Multi line
    comment]]> -->
    <record id="my_id" model="model">
        <field name="name">name</field>
    </record>
    <![CDATA[ <!-- no a comment]]>
    <node>not a comment but found as is</node>
    <!-- comment -->
    <node>After closed comment back to normal</node>
</odoo>
"""

PY_TEST_NO_RETURN = '''line = 1
line = 2'''

PY_TEST = '''
# comment 1

def func(): # eol comment 3
    """ docstring
    """
    pass

def query():
    long_query = """
        SELECT *
        FROM table
        WHERE id = 1;
    """
    return query

print(i.lineno, i, getattr(i,'s',None), getattr(i,'value',None))
'''

JS_TEST = '''
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

CSS_TEST = '''
/*
  Comment
*/

p {
  text-align: center;
  color: red;
  text-overflow: ' /* ';
}


#content, #footer, #supplement {
   position: absolute;
   left: 510px;
   width: 200px;
   text-overflow: ' */ ';
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
    @include o-list-view-full-width-padding($base: $table-cell-padding-sm, $ratio: 2);
    &:not(.o_list_table_grouped) {
        @include media-breakpoint-up(xl) {
            @include o-list-view-full-width-padding($base: $table-cell-padding-sm, $ratio: 2.5);
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

class TestClocCustomization(TransactionCase):
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
            'model_id': self.env.ref('base.model_res_partner').id,
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
            'model_id': self.env.ref('base.model_res_partner').id,
            'ttype': 'integer',
            'store': False,
            'compute': "for rec in self: rec['x_invoice_count'] = 10",
        })
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 1, 'Should count field with no xml_id at all')


class TestClocParser(TransactionCase):

    def test_parser(self):
        cl = cloc.Cloc()
        xml_count = cl.parse_xml(XML_TEST)
        self.assertEqual(xml_count, (18, 31))
        py_count = cl.parse_py(PY_TEST_NO_RETURN)
        self.assertEqual(py_count, (2, 2))
        py_count = cl.parse_py(PY_TEST)
        if self._python_version >= (3, 8, 0):
            # Multi line str lineno return the begining of the str
            # in python 3.8, it result in a different count for
            # multi str used in expressions
            self.assertEqual(py_count, (7, 16))
        else:
            self.assertEqual(py_count, (8, 16))
        js_count = cl.parse_js(JS_TEST)
        self.assertEqual(js_count, (10, 17))
        css_count = cl.parse_css(CSS_TEST)
        self.assertEqual(css_count, (11, 17))
        scss_count = cl.parse_scss(SCSS_TEST)
        self.assertEqual(scss_count, (17, 26))


@tagged('post_install', '-at_install')
class TestClocStdNoCusto(TransactionCase):

    def test_no_custo_install(self):
        """
            Make sure after the installation of module
            no database customization is counted
        """
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('odoo/studio', 0), 0, 'Module should not generate customization in database')
