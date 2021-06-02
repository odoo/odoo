# Part of Odoo. See LICENSE file for full copyright and licensing details.
import sys

from odoo.tools import cloc
from odoo.tests.common import TransactionCase

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

class TestCloc(TransactionCase):
    def test_parser(self):
        cl = cloc.Cloc()
        xml_count = cl.parse_xml(XML_TEST)
        self.assertEqual(xml_count, (18, 31))
        py_count = cl.parse_py(PY_TEST_NO_RETURN)
        self.assertEqual(py_count, (2, 2))
        py_count = cl.parse_py(PY_TEST)
        if sys.version_info >= (3, 8, 0):
            # Multi line str lineno return the begining of the str
            # in python 3.8, it result in a different count for
            # multi str used in expressions
            self.assertEqual(py_count, (7, 16))
        else:
            self.assertEqual(py_count, (8, 16))
        js_count = cl.parse_js(JS_TEST)
        self.assertEqual(js_count, (10, 17))
