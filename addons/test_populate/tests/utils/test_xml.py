from lxml import etree

from odoo.tests import TransactionCase

from odoo.addons.populate.utils import xml


class TestXMLEnsureRoot(TransactionCase):

    def test_ensure_root_valid_data_unchanged(self):
        valid_xml = '<data><model name="test" count="1"/></data>'
        result = xml.ensure_root(valid_xml)
        self.assertEqual(result, valid_xml)

    def test_ensure_root_single_model_wrapped(self):
        single_model = '<model name="test" count="1"/>'
        result = xml.ensure_root(single_model)
        self.assertIn('<data>', result)
        self.assertIn('</data>', result)
        self.assertIn('<model name="test" count="1"/>', result)

    def test_ensure_root_empty_document(self):
        empty_xml = ''
        result = xml.ensure_root(empty_xml)
        self.assertEqual(result, '<data/>')

    def test_ensure_root_multiple_roots(self):
        multiple_roots = '<model name="test1" count="1"/><model name="test2" count="2"/>'
        result = xml.ensure_root(multiple_roots)
        expected = '<data><model name="test1" count="1"/><model name="test2" count="2"/></data>'
        self.assertEqual(result, expected)

    def test_ensure_root_invalid_xml_raises(self):
        invalid_xml = '<model name="test" count="1"'
        with self.assertRaises(etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)

    def test_ensure_root_malformed_closing_raises(self):
        invalid_xml = '<model name="test" count="1"></wrong>'
        with self.assertRaises(etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)


class TestXMLParse(TransactionCase):

    def test_parse_simple_model(self):
        xml_str = '''
        <data>
            <model name="test_populate.product" count="10">
                <field name="name" generator="textual.char" length="20"/>
                <field name="price" generator="scalar.float" start="10.0" end="100.0"/>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'test_populate.product')
        self.assertEqual(result[0]['count'], 10)
        self.assertIn('name', result[0]['fields'])
        self.assertIn('price', result[0]['fields'])

    def test_parse_model_with_ref(self):
        xml_str = '''
        <data>
            <model name="test_populate.product" count="5" id="special_products">
                <field name="name" generator="textual.char"/>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertEqual(result[0]['ref'], 'special_products')

    def test_parse_model_with_domain(self):
        xml_str = '''
        <data>
            <model name="test_populate.product" domain="[('category', '=', 'books')]">
                <field name="name" generator="textual.char"/>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertEqual(result[0]['domain'], "[('category', '=', 'books')]")

    def test_parse_model_missing_name_raises(self):
        xml_str = '''
        <data>
            <model count="10">
                <field name="name" generator="textual.char"/>
            </model>
        </data>
        '''
        with self.assertRaises(ValueError):
            xml.parse(xml_str)

    def test_parse_field_missing_name_raises(self):
        xml_str = '''
        <data>
            <model name="test_populate.product" count="10">
                <field generator="textual.char"/>
            </model>
        </data>
        '''
        with self.assertRaises(ValueError):
            xml.parse(xml_str)

    def test_parse_nested_fields(self):
        xml_str = '''
        <data>
            <model name="test_populate.supplier" count="2">
                <field name="product_ids" count="3">
                    <field name="name" generator="textual.char"/>
                    <field name="price" generator="scalar.float"/>
                </field>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertIn('product_ids', result[0]['fields'])
        self.assertIn('fields', result[0]['fields']['product_ids'])
        self.assertIn('name', result[0]['fields']['product_ids']['fields'])

    def test_parse_field_std_attribute_as_integer(self):
        xml_str = '''
        <data>
            <model name="test_populate.product.tagged" count="10">
                <field name="tag_ids" generator="relation.many" count="5" std="3" null_ratio="0.2"/>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        field_data = result[0]['fields']['tag_ids']

        self.assertEqual(field_data['count'], 5)
        self.assertEqual(field_data['std'], 3)
        self.assertIsInstance(field_data['std'], int)
        self.assertIsInstance(field_data['count'], int)

    def test_parse_field_std_with_nested_fields(self):
        xml_str = '''
        <data>
            <model name="test_populate.supplier" count="10">
                <field name="product_ids" count="4" std="2">
                    <field name="name" generator="textual.char"/>
                    <field name="price" generator="scalar.float"/>
                </field>
            </model>
        </data>
        '''
        result = xml.parse(xml_str)
        field_data = result[0]['fields']['product_ids']

        self.assertEqual(field_data['count'], 4)
        self.assertEqual(field_data['std'], 2)
        self.assertIn('fields', field_data)
        self.assertIn('name', field_data['fields'])
