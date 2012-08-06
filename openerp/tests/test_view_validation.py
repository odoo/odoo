# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_view_validation.py

from lxml import etree
from StringIO import StringIO
import unittest2

import openerp
from openerp.tools.view_validation import *

invalid_form = etree.parse(StringIO('''\
<form>
    <label></label>
    <group>
        <div>
            <page></page>
            <label colspan="True"></label>
            <field></field>
        </div>
    </group>
    <notebook>
        <page>
            <group col="Two">
            <div>
                <label></label>
                <field colspan="Five"> </field>
                </div>
            </group>
        </page>
    </notebook>
</form>
''')).getroot()

valid_form = etree.parse(StringIO('''\
<form string="">
    <notebook>
        <label for=""></label>
        <page>
            <field name=""></field>
            <label string=""></label>
            <field name=""></field>
        </page>
        <page>
            <group colspan="5" col="2">
                <label for=""></label>
                <label string="" colspan="5"></label>
            </group>
        </page>
    </notebook>
</form>
''')).getroot()

invalid_graph = etree.parse(StringIO('''\
<graph>
      <group>
        <div>
          <field></field>
          <field></field>
        </div>
      </group>
</graph>
''')).getroot()

valid_graph = etree.parse(StringIO('''\
<graph string="">
    <field name=""></field>
    <field name=""></field>
</graph>
''')).getroot()

invalid_tree = etree.parse(StringIO('''\
<tree>
  <group>
    <div>
      <field></field>
      <field></field>
    </div>
  </group>
</tree>
''')).getroot()

valid_tree= etree.parse(StringIO('''\
<tree string="">
    <button></button>
    <label string=""></label>
    <field name=""></field>
    <field name=""></field>
    <field name=""></field>
    <button></button>
</tree>
''')).getroot()


class test_view_validation(unittest2.TestCase):
    """ Test the view validation code (but not the views themselves). """

    def test_page_validation(self):
        assert not valid_page_in_book(invalid_form)
        assert valid_page_in_book(valid_form)

    def test_all_field_validation(self):
        assert not  valid_att_in_field(invalid_form)
        assert  valid_att_in_field(valid_form)

    def test_all_label_validation(self):
        assert not  valid_att_in_label(invalid_form)
        assert  valid_att_in_label(valid_form)

    def test_form_string_validation(self):
        assert not valid_att_in_form(invalid_form)
        assert valid_att_in_form(valid_form)

    def test_graph_field_validation(self):
        assert not valid_field_in_graph(invalid_graph)
        assert valid_field_in_graph(valid_graph)

    def test_graph_string_validation(self):
        assert not valid_field_in_graph(invalid_graph)
        assert valid_field_in_graph(valid_graph)

    def test_tree_field_validation(self):
        assert not valid_field_in_tree(invalid_tree)
        assert valid_field_in_tree(valid_tree)

    def test_tree_string_validation(self):
        assert not valid_field_in_tree(invalid_tree)
        assert valid_field_in_tree(valid_tree)

    def test_colspan_datatype_validation(self):
        assert not valid_type_in_colspan(invalid_form)
        assert valid_type_in_colspan(valid_form)

    def test_col_datatype_validation(self):
        assert not valid_type_in_col(invalid_form)
        assert valid_type_in_col(valid_form)

    def test_form_view(self):
        assert not valid_view(invalid_form)
        assert valid_view(valid_form)

    def test_tree_view(self):
        assert not valid_view(invalid_tree)
        assert valid_view(valid_tree)

    def test_graph_view(self):
        assert not valid_view(invalid_graph)
        assert valid_view(valid_graph)


if __name__ == '__main__':
    unittest2.main()
