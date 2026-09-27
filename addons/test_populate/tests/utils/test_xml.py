from pathlib import Path

from lxml import etree

from odoo.modules import Manifest
from odoo.tests import TransactionCase
from odoo.tests.case import TestCase

from odoo.addons.populate.utils import xml


class TestXMLEnsureRoot(TransactionCase):

    def test_ensure_root_valid_data_unchanged(self):
        valid_xml = '<data><create model="test" count="1"/></data>'
        result = xml.ensure_root(valid_xml)
        self.assertEqual(result, valid_xml)

    def test_ensure_root_single_model_wrapped(self):
        single_model = '<create model="test" count="1"/>'
        result = xml.ensure_root(single_model)
        self.assertIn('<data>', result)
        self.assertIn('</data>', result)
        self.assertIn('<create model="test" count="1"/>', result)

    def test_ensure_root_empty_document(self):
        empty_xml = ''
        result = xml.ensure_root(empty_xml)
        self.assertEqual(result, '<data/>')

    def test_ensure_root_multiple_roots(self):
        multiple_roots = '<create model="test1" count="1"/><create model="test2" count="2"/>'
        result = xml.ensure_root(multiple_roots)
        expected = '<data><create model="test1" count="1"/><create model="test2" count="2"/></data>'
        self.assertEqual(result, expected)

    def test_ensure_root_invalid_xml_raises(self):
        invalid_xml = '<create model="test" count="1"'
        with self.assertRaises(etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)

    def test_ensure_root_malformed_closing_raises(self):
        invalid_xml = '<create model="test" count="1"></wrong>'
        with self.assertRaises(etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)


class TestXMLParse(TransactionCase):

    def test_parse_operation_attribute_raises(self):
        xml_str = '<data><create model="test_populate.product" operation="write"/></data>'

        with self.assertRaisesRegex(ValueError, "element name already defines the operation"):
            xml.parse(xml_str)

    def test_parse_simple_model(self):
        xml_str = '''
        <data>
            <create model="test_populate.product" count="10">
                <field name="name" generator="textual.char" length="20"/>
                <field name="price" generator="scalar.float" start="10.0" end="100.0"/>
            </create>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['model'], 'test_populate.product')
        self.assertEqual(result[0]['count'], 10)
        self.assertIn('name', result[0]['fields'])
        self.assertIn('price', result[0]['fields'])

    def test_parse_model_with_ref(self):
        xml_str = '''
        <data>
            <create model="test_populate.product" count="5" id="special_products">
                <field name="name" generator="textual.char"/>
            </create>
        </data>
        '''
        result = xml.parse(xml_str)
        self.assertEqual(result[0]['id'], 'special_products')

    def test_parse_model_with_domain(self):
        xml_str = '''
        <data>
            <create model="test_populate.product" domain="[('category', '=', 'books')]">
                <field name="name" generator="textual.char"/>
            </create>
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
            <create model="test_populate.product" count="10">
                <field generator="textual.char"/>
            </create>
        </data>
        '''
        with self.assertRaises(ValueError):
            xml.parse(xml_str)

    def test_parse_field_std_attribute_as_integer(self):
        xml_str = '''
        <data>
            <create model="test_populate.product.tagged" count="10">
                <field name="tag_ids" generator="relation.many" count="5" std="3" null_ratio="0.2"/>
            </create>
        </data>
        '''
        result = xml.parse(xml_str)
        field_data = result[0]['fields']['tag_ids']

        self.assertEqual(field_data['count'], 5)
        self.assertEqual(field_data['std'], 3)
        self.assertIsInstance(field_data['std'], int)
        self.assertIsInstance(field_data['count'], int)

    def test_parse_field_std_attribute_as_integer_without_generator(self):
        xml_str = '''
        <data>
            <create model="test_populate.supplier" count="10">
                <field name="product_ids" count="4" std="2"/>
            </create>
        </data>
        '''
        result = xml.parse(xml_str)
        field_data = result[0]['fields']['product_ids']

        self.assertEqual(field_data['count'], 4)
        self.assertEqual(field_data['std'], 2)

    def test_parse_function_with_args(self):
        xml_str = '''
        <data>
            <function model="test_populate.customer" name="populate_set_notes_from_args" ref="customers" batched="True">
                <value name="helper" eval="'suffix'"/>
                <arg eval="'first'"/>
                <arg eval="helper"/>
                <arg name="flag" eval="True"/>
            </function>
        </data>
        '''

        result = xml.parse(xml_str)

        self.assertEqual(result[0]['operation'], 'function')
        self.assertEqual(result[0]['model'], 'test_populate.customer')
        self.assertEqual(result[0]['name'], 'populate_set_notes_from_args')
        self.assertEqual(result[0]['ref'], 'customers')
        self.assertTrue(result[0]['batched'])
        self.assertEqual(result[0]['args']['0'], {'eval': "'first'"})
        self.assertEqual(result[0]['args']['1'], {'eval': 'helper'})
        self.assertEqual(result[0]['args']['flag'], {'eval': 'True'})
        self.assertEqual(result[0]['values']['helper'], {'eval': "'suffix'"})

    def test_parse_function_implicit_arg_collision_raises(self):
        xml_str = '''
        <data>
            <function model="test_populate.customer" name="populate_set_notes_from_args" ref="customers">
                <arg eval="'first'"/>
                <arg name="0" eval="'duplicate'"/>
            </function>
        </data>
        '''

        with self.assertRaises(ValueError):
            xml.parse(xml_str)


class TestXMLImportHelpers(TransactionCase):

    def test_expand_imports(self):
        fragments = {
            'test.source': etree.fromstring('''
                <data>
                    <create model="imported.first"/>
                    <create model="imported.second"/>
                </data>
            '''),
        }
        definition = etree.fromstring('''
            <data>
                <create model="local.first"/>
                <import ref="test.source"/>
                <create model="local.last"/>
            </data>
        ''')

        result = xml.expand_imports(
            definition,
            lambda element: fragments[element.get('ref')],
        )

        self.assertIs(result, definition)
        self.assertEqual(len(fragments['test.source']), 0)
        self.assertEqual(
            [element.get('model') for element in result],
            ['local.first', 'imported.first', 'imported.second', 'local.last'],
        )

    def test_namespace_references_only_rewrites_declared_ids(self):
        tree = etree.fromstring('''
            <data>
                <create model="test_populate.product" count="2" id="products">
                    <field name="name" eval="'products must remain text'"/>
                </create>
                <write model="test_populate.product" ref="products.product_variant_ids">
                    <field name="description" ref="caller_products" domain="[('name', '=', 'products')]"/>
                </write>
            </data>
        ''')

        xml.namespace_references(tree, 'catalog')

        self.assertEqual(tree[0].get('id'), 'catalog/products')
        self.assertEqual(tree[1].get('ref'), 'catalog/products.product_variant_ids')
        self.assertEqual(tree[1][0].get('ref'), 'caller_products')
        self.assertEqual(tree[1][0].get('domain'), "[('name', '=', 'products')]")
        self.assertEqual(tree[0][0].get('eval'), "'products must remain text'")

    def test_apply_inheritance_specs(self):
        source = etree.fromstring('''
            <data>
                <create model="test_populate.product" count="2" id="products"/>
            </data>
        ''')
        specs = etree.fromstring('''
            <import>
                <xpath expr="//create[@id='products']" position="attributes">
                    <attribute name="count">5</attribute>
                </xpath>
            </import>
        ''')

        result = xml.apply_inheritance_specs(source, specs)

        self.assertEqual(result[0].get('count'), '5')


class TestStaticPopulateXMLFiles(TestCase):

    @staticmethod
    def _field_xml(field):
        return ''.join(
            etree.tostring(child, encoding='unicode')
            for child in field
        ) or (field.text or '')

    def test_shipped_populate_blueprint_xml_definitions_parse(self):
        """Statically parse shipped standalone populate blueprint definitions."""
        failures = []
        checked = 0

        for manifest in Manifest.all_addon_manifests():
            populate_dir = Path(manifest.path) / 'populate'
            if not populate_dir.is_dir():
                continue

            for data_file in sorted(populate_dir.glob('*.xml')):
                tree = etree.parse(str(data_file))
                relative_path = data_file.relative_to(manifest.path)
                for record in tree.xpath(".//record[@model='populate.blueprint']"):
                    definition_field = record.find("./field[@name='definition_xml']")
                    if definition_field is None:
                        continue

                    if record.find("./field[@name='inherit_id']") is not None:
                        continue

                    record_id = record.get('id', '<unknown>')
                    label = f"{manifest.name}/{relative_path}:{record_id}"
                    try:
                        definition_xml = xml.ensure_root(self._field_xml(definition_field))
                        definition = etree.fromstring(definition_xml)
                        if definition.find('import') is not None:
                            continue
                        xml.parse(definition_xml)
                    except Exception as exc:  # noqa: BLE001
                        failures.append(f"{label}: {exc}")
                    checked += 1

        self.assertGreater(checked, 0, "No standalone populate blueprint XML definitions were found.")
        if failures:
            self.fail(
                "Invalid standalone populate blueprint XML definition(s):\n"
                + '\n'.join(f"- {failure}" for failure in failures)
            )
