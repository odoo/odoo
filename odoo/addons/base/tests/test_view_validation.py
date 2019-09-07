# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import io

from odoo.tests.common import BaseCase
from odoo.tools.view_validation import (
    valid_page_in_book, valid_att_in_form, valid_type_in_colspan,
    valid_type_in_col, valid_att_in_field, valid_att_in_label,
    valid_field_in_graph, valid_field_in_tree, valid_alternative_image_text,
    valid_alternative_icon_text, valid_title_icon, valid_simili_button,
    valid_simili_progressbar, valid_dialog, valid_simili_dropdown,
    valid_focusable_button, valid_prohibited_none_role, valid_simili_tabpanel,
    valid_simili_tab, valid_simili_tablist, valid_alerts
)

invalid_form = etree.parse(io.BytesIO(b'''\
<form>
    <label></label>
    <ul class="dropdown-menu"><li/><li/></ul>
    <div role="presentation"/>
    <group>
        <div>
            <page></page>
            <label colspan="True" string=""></label>
            <field></field>
        </div>
    </group>
    <notebook>
        <page>
            <group col="Two">
                <div>
                    <div class="o_progressbar">100%</div>
                    <label string=""></label>
                    <img/>
                    <span class="fa fa-warning"/>
                    <field colspan="Five"> </field>
                </div>
            </group>
            <a class="btn"/>
            <div class="btn"/>
            <div class="tab-pane"/>
        </page>
    </notebook>
    <div class="modal"/>
    <a data-toggle="tab"/>
    <div class="nav-tabs"/>
    <div class="alert alert-success"/>
</form>
''')).getroot()

valid_form = etree.parse(io.BytesIO(b'''\
<form string="">
    <field name=""></field>
    <field name=""></field>
    <ul class="dropdown-menu" role="menu"></ul>
    <notebook>
        <page>
            <field name=""></field>
            <label for="" string=""></label>
            <field name=""></field>
        </page>
        <page>
            <group colspan="5" col="2">
                <div class="o_progressbar" role="progressbar" aria-valuenow="14" aria-valuemin="0" aria-valuemax="100">14%</div>
                <label for=""></label>
                <label for="" string="" colspan="5"></label>
                <img alt="Test image"/>
                <span class="fa fa-success" aria-label="Test span" title="Test span"/>
                <a class="fa fa-success"><span aria-label="test" title="test"/></a>
                <a class="btn" role="button"/>
                <i class="fa fa-check"/> Test icon
                <i class="fa fa-check"/>
            </group>
        </page>
    </notebook>
    <div role="dialog" class="modal">
        <header class="modal-header"/>
        <main class="modal-body"/>
        <i class="fa fa-check"/> <span>Test</span>
        <footer class="modal-footer"/>
    </div>
    <div class="tab-pane" role="tabpanel"/>
    <a data-toggle="tab" role="tab" aria-selected="true" aria-controls="test"/>
    <div class="nav-tabs" role="tablist"/>
    <div class="alert alert-success" role="alert"/>
    <div class="alert alert-success" role="alertdialog"/>
    <div class="alert alert-success" role="status"/>
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


class TestViewValidation(BaseCase):
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

    def test_a11y_validation(self):
        assert valid_alternative_image_text(invalid_form) == "Warning"
        assert valid_alternative_image_text(valid_form) is True
        assert valid_alternative_icon_text(invalid_form) == "Warning"
        assert valid_alternative_icon_text(valid_form) is True
        assert valid_title_icon(invalid_form) == "Warning"
        assert valid_title_icon(valid_form) is True
        assert valid_simili_button(invalid_form) == "Warning"
        assert valid_simili_button(valid_form) is True
        assert valid_dialog(invalid_form) == "Warning"
        assert valid_dialog(valid_form) is True
        assert valid_simili_dropdown(invalid_form) == "Warning"
        assert valid_simili_dropdown(valid_form) is True
        assert valid_simili_progressbar(invalid_form) == "Warning"
        assert valid_simili_progressbar(valid_form) is True
        assert valid_simili_tabpanel(invalid_form) == "Warning"
        assert valid_simili_tabpanel(valid_form) is True
        assert valid_simili_tablist(invalid_form) == "Warning"
        assert valid_simili_tablist(valid_form) is True
        assert valid_simili_tab(invalid_form) == "Warning"
        assert valid_simili_tab(valid_form) is True
        assert valid_focusable_button(invalid_form) == "Warning"
        assert valid_focusable_button(valid_form) is True
        assert valid_prohibited_none_role(invalid_form) == "Warning"
        assert valid_prohibited_none_role(valid_form) is True
        assert valid_alerts(invalid_form) == "Warning"
        assert valid_alerts(valid_form) is True
