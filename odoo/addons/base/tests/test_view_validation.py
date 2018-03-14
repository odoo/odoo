# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import io
import unittest

from odoo.tests.common import tagged
from odoo.tools.view_validation import (
    valid_page_in_book, valid_att_in_form, valid_type_in_colspan,
    valid_type_in_col, valid_att_in_field, valid_att_in_label,
    valid_field_in_graph, valid_field_in_tree,
)

invalid_form = etree.parse(io.BytesIO(b'''\
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

valid_form = etree.parse(io.BytesIO(b'''\
<form string="">
    <field name=""></field>
    <field name=""></field>
    <notebook>
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

invalid_graph = etree.parse(io.BytesIO(b'''\
<graph>
    <label/>
    <group>
        <div>
            <field></field>
            <field></field>
        </div>
    </group>
</graph>
''')).getroot()

valid_graph = etree.parse(io.BytesIO(b'''\
<graph string="">
    <field name=""></field>
    <field name=""></field>
</graph>
''')).getroot()

invalid_tree = etree.parse(io.BytesIO(b'''\
<tree>
  <group>
    <div>
      <field></field>
      <field></field>
    </div>
  </group>
</tree>
''')).getroot()

valid_tree = etree.parse(io.BytesIO(b'''\
<tree string="">
    <field name=""></field>
    <field name=""></field>
    <button/>
    <field name=""></field>
</tree>
''')).getroot()


@tagged('standard', 'at_install')
class TestViewValidation(unittest.TestCase):
    """ Test the view validation code (but not the views themselves). """

    def test_page_validation(self):
        assert not valid_page_in_book(invalid_form)
        assert valid_page_in_book(valid_form)

    def test_all_field_validation(self):
        assert not valid_att_in_field(invalid_form)
        assert valid_att_in_field(valid_form)

    def test_all_label_validation(self):
        assert not valid_att_in_label(invalid_form)
        assert valid_att_in_label(valid_form)

    def test_form_string_validation(self):
        assert valid_att_in_form(valid_form)

    def test_graph_validation(self):
        assert not valid_field_in_graph(invalid_graph)
        assert valid_field_in_graph(valid_graph)

    def test_tree_validation(self):
        assert not valid_field_in_tree(invalid_tree)
        assert valid_field_in_tree(valid_tree)

    def test_colspan_datatype_validation(self):
        assert not valid_type_in_colspan(invalid_form)
        assert valid_type_in_colspan(valid_form)

    def test_col_datatype_validation(self):
        assert not valid_type_in_col(invalid_form)
        assert valid_type_in_col(valid_form)
