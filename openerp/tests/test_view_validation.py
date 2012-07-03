# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_view_validation.py

from lxml import etree
from StringIO import StringIO
import unittest2

import openerp
from openerp.tools.view_validation import *

invalid_form = etree.parse(StringIO('''\
<form>     
    <label/>    
      <group>
        <div>
          <page/>
          <label/>
          <field>
          </field>
        </div>
      </group>
</form>
''')).getroot()

valid_form = etree.parse(StringIO('''\
<form string="">
    <notebook>
        <label for=""/>
        <page>
            <field name=""/>
            <label string=""/>
            <field name=""/>
        </page>
    </notebook>
</form>
''')).getroot()

invalid_graph = etree.parse(StringIO('''\
<graph>
      <group>
        <div>
          <field/>
          <field/>
        </div>
      </group>
</graph>
''')).getroot()

valid_graph = etree.parse(StringIO('''\
<graph string="">
    <field></field>
    <field/>
    <field/>
</graph>
''')).getroot()


valid_tree= etree.parse(StringIO('''\
<tree string="">
    <button/>
    <field/>
    <field/>
    <field/>
    <button/>
</tree>
''')).getroot()

invalid_tree = etree.parse(StringIO('''\
<tree>
  <group>
    <div>
      <field/>
      <field/>
    </div>
  </group>
</tree>
''')).getroot()

invalid_attribute = etree.parse(StringIO('''\
<group colspan="saf" col="dsd">
    <div>
      <label/>
      <field>
      </field>
    </div>
</group>
''')).getroot()

valid_attribute = etree.parse(StringIO('''\
<group colspan="1" col="2">
    <label for=""/>
    <label string=""/>
    <label for=""/>
</group>
''')).getroot()


class test_view_validation(unittest2.TestCase):
    """ Test the view validation code (but not the views themselves). """

    def test_page_validation(self):
        assert not valid_page_in_book(invalid_form)
        assert valid_page_in_book(valid_form)
        
        assert not valid_view(invalid_form)
        assert valid_view(valid_form)
        
    def test_all_field_validation(self):
        assert not  valid_att_in_field(invalid_form)
        assert  valid_att_in_field(valid_form)

        assert not valid_field_view(invalid_form)
        assert valid_field_view(valid_form)

    def test_all_label_validation(self):
        assert not  valid_att_in_label(invalid_form)
        assert  valid_att_in_label(valid_form)

        assert not valid_label_view(invalid_form)
        assert valid_label_view(valid_form)
        
    def test_form_string_validation(self):
        assert not valid_att_in_form(invalid_form)
        assert valid_att_in_form(valid_form)

        assert not valid_form_view(invalid_form)
        assert valid_form_view(valid_form)

    def test_graph_field_validation(self):
        assert not valid_field_in_graph(invalid_graph)
        assert valid_field_in_graph(valid_graph)
        
        assert not valid_view(invalid_graph)
        assert valid_view(valid_graph)        

    def test_graph_string_validation(self):
        assert not valid_att_in_graph(invalid_graph)
        assert valid_att_in_graph(valid_graph)

        assert not valid_graph_view(invalid_graph)
        assert valid_graph_view(valid_graph)
    
    def test_tree_field_validation(self):
        assert not valid_field_in_tree(invalid_tree)
        assert valid_field_in_tree(valid_tree)

        assert not valid_view(invalid_tree)
        assert valid_view(valid_tree)        

    def test_tree_string_validation(self):
        assert not valid_att_in_tree(invalid_tree)
        assert valid_att_in_tree(valid_tree)
    
        assert not valid_tree_view(invalid_tree)
        assert valid_tree_view(valid_tree)
        
    def test_colspan_datatype_validation(self):
        assert not valid_type_in_colspan(invalid_attribute)
        assert valid_type_in_colspan(valid_attribute)
        
        assert not valid_colspan_view(invalid_attribute)
        assert valid_colspan_view(valid_attribute)
    
    def test_col_datatype_validation(self):
        assert not valid_type_in_col(invalid_attribute)
        assert valid_type_in_col(valid_attribute)
        
        assert not valid_col_view(invalid_attribute)
        assert valid_col_view(valid_attribute)


if __name__ == '__main__':
    unittest2.main()
