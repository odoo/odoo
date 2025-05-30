from lxml import etree

from odoo.tests.common import TransactionCase
from odoo.tools.xml_utils import cleanup_xml_node


class TestXMLTools(TransactionCase):

    def setUp(self):
        super().setUp()
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

    def test_cleanup_xml_node_without_modification(self):
        # Qweb removes comments and any whitespace before first tag
        expected = """<h1>
            <h2/>
                <h2>text</h2>
        \t<h2><h3/></h2>
            <h2>            </h2>

</h1>"""
        qweb = self.env['ir.qweb']._render(self.qweb_poor.id)
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False, remove_blank_nodes=False, indent_level=-1)

    def test_cleanup_xml_node_indentation_and_spacing(self):
        # First tag is not indented because indent is actually previous tag's tail.
        expected = """<h1>
__<h2/>
__<h2>text</h2>
__<h2>
___<h3/>
__</h2>
__<h2>            </h2>
_</h1>
"""
        qweb = self.env['ir.qweb']._render(self.qweb_poor.id)
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False, remove_blank_nodes=False, indent_level=1, indent_space="_")

    def test_cleanup_xml_node_remove_blank_nodes_only(self):
        expected = """<h1>
  <h2>text</h2>
  <h2>            </h2>
</h1>
"""
        qweb = self.env['ir.qweb']._render(self.qweb_poor.id)
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_text=False)

    def test_cleanup_xml_node_remove_blank_text_only(self):
        expected = """<h1>
  <h2/>
  <h2>text</h2>
  <h2>
    <h3/>
  </h2>
  <h2></h2>
</h1>
"""
        qweb = self.env['ir.qweb']._render(self.qweb_poor.id)
        self.check_xml_cleanup_result_is_as_expected(qweb, expected, remove_blank_nodes=False)

    def test_cleanup_xml_node_indentation_with_t_call(self):
        template_child = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'arch_db': '''<h1>
    <content>This is content!</content>
</h1>
'''})
        template_parent = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': f'''<odoo>
    <data>
        <t t-call="{template_child.id}"/>
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
        qweb = self.env['ir.qweb']._render(template_parent.id)
        self.check_xml_cleanup_result_is_as_expected(qweb, expected)

    def test_cleanup_xml_node_conditional_rendering(self):
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
        qweb = self.env['ir.qweb']._render(template_main.id, {
            'items': [1, 2, "Three", False],
            'addressRecipient': {
                'number': '221B',
                'street': 'Baker street',
                'city': 'London',
            },
            'addressSender': {
                'street': ' ',
            },
        })

        # Empty nodes are removed after conditional rendering.
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
        self.check_xml_cleanup_result_is_as_expected(qweb, expected)

    def check_xml_cleanup_result_is_as_expected(self, original_string, expected_string, **kwargs):
        result_string = etree.tostring(cleanup_xml_node(original_string, **kwargs)).decode()
        self.assertEqual(expected_string, result_string)
        self.assertNotEqual(expected_string, original_string)
