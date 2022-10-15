# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from lxml import etree
from odoo.tests import common
from odoo.tools.xml_utils import cleanup_xml_node


class TestXMLTools(common.TransactionCase):

    def setUp(self):
        super(TestXMLTools, self).setUp()
        self.qweb_poor = self.env()['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': """
    <h1>
            <h2/>
                <h2>text</h2>
        \t<h2><h3/></h2>
            <h2>            </h2>
<!-- comment removed by qweb -->
</h1>"""})

    def test_cleanup_xml_node_no_modif(self):
        # Qweb removes comments and any whitespace before first tag, no other content affected
        expected = """<h1>
            <h2/>
                <h2>text</h2>
        \t<h2><h3/></h2>
            <h2>            </h2>
</h1>"""
        qweb = self.qweb_poor._render()
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False, remove_blank_nodes=False, indent_level=-1)

    def test_cleanup_xml_node_indent_level(self):
        # Indentation level and spacing works as expected, nothing else affected
        # (quirk: first tag not indented because indent is actually previous tag's tail)
        expected = """<h1>
__<h2/>
__<h2>text</h2>
__<h2>
___<h3/>
__</h2>
__<h2>            </h2>
_</h1>
"""
        qweb = self.qweb_poor._render()
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False, remove_blank_nodes=False, indent_level=1, indent_space="_")

    def test_cleanup_xml_node_keep_blank_text(self):
        # Blank nodes are removed but not nodes containing blank text
        expected = """<h1>
  <h2>text</h2>
  <h2>            </h2>
</h1>
"""
        qweb = self.qweb_poor._render()
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False)

    def test_cleanup_xml_node_keep_blank_nodes(self):
        # Blank text is removed but blank (empty) nodes remain
        expected = """<h1>
  <h2/>
  <h2>text</h2>
  <h2>
    <h3/>
  </h2>
  <h2></h2>
</h1>
"""
        qweb = self.qweb_poor._render()
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_nodes=False)

    def test_cleanup_xml_t_call_indent(self):
        # Indentation is fixed after t-call (which keeps indentation of called template)
        template_1 = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': '''<h1>
    <content>This is content!</content>
</h1>
'''})
        template_2 = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': f'''<odoo>
    <data>
        <t t-call="{template_1.id}"/>
    </data>
</odoo>
'''})
        expected = """<odoo>
  <data>
    <h1>
      <content>This is content!</content>
    </h1>
  </data>
</odoo>
"""
        qweb = template_2._render()
        self.check_xml_cleanup_result_is_as_expected(qweb, expected)

    def test_qweb_render_values_empty_nodes(self):
        # Indentation is fixed and empty nodes are removed after conditional rendering
        template_addresses = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': '''<t>
    <street t-esc="address.get('street')"/>
    <number t-esc="address.get('number')"/>
    <city t-esc="address.get('city')"/>
</t>
'''})
        template_main = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': f'''<data>
    <item t-foreach="items" t-as="item" t-esc="item"/>
    <addressSender t-call='{template_addresses.id}'>
        <t t-set="address" t-value="addressSender"/>
    </addressSender>
    <addressRecipient t-call='{template_addresses.id}'>
        <t t-set="address" t-value="addressRecipient"/>
    </addressRecipient>
</data>
'''})
        expected = """<data>
  <item>1</item>
  <item>2</item>
  <item>Three</item>
  <addressRecipient>
    <street>Baker street</street>
    <number>221B</number>
    <city>London</city>
  </addressRecipient>
</data>
"""
        qweb = template_main._render({
            'items': [1, 2, "Three", False],
            'addressRecipient': {
                'number': '221B',
                'street': 'Baker street',
                'city': 'London',
            },
            'addressSender': {
                'street': ' '
            }
        })
        self.check_xml_cleanup_result_is_as_expected(qweb, expected)

    def check_xml_cleanup_result_is_as_expected(self, original_string, expected_string, **kwargs):
        result_string = etree.tostring(cleanup_xml_node(original_string, **kwargs)).decode()
        self.assertEqual(expected_string, result_string)
        self.assertNotEqual(expected_string, original_string)
