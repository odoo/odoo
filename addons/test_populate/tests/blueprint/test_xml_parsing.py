from odoo.tests import TransactionCase

from odoo.addons.populate.utils import xml


class TestXMLParsing(TransactionCase):

    def test_ensure_root_valid_xml_unchanged(self):
        valid_xml = '<data><create model="test" count="1"/></data>'
        result = xml.ensure_root(valid_xml)
        self.assertEqual(result, valid_xml)

    def test_ensure_root_empty_document_returns_blueprint(self):
        empty_xml = ''
        result = xml.ensure_root(empty_xml)
        self.assertEqual(result, '<data/>')

    def test_ensure_root_multiple_roots_wrapped(self):
        multiple_roots_xml = '<create model="test1" count="1"/><create model="test2" count="2"/>'
        result = xml.ensure_root(multiple_roots_xml)
        expected = '<data><create model="test1" count="1"/><create model="test2" count="2"/></data>'
        self.assertEqual(result, expected)

    def test_ensure_root_invalid_xml_raises_exception(self):
        invalid_xml = '<create model="test" count="1"'
        with self.assertRaises(xml.etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)

    def test_ensure_root_malformed_closing_tag_raises_exception(self):
        invalid_xml = '<create model="test" count="1"></wrong>'
        with self.assertRaises(xml.etree.XMLSyntaxError):
            xml.ensure_root(invalid_xml)


class TestXMLToJSONConversion(TransactionCase):

    def test_writing_blueprint_parsing_and_jobs(self):
        blueprint = self.env.ref('test_populate.sample_writing_blueprint', raise_if_not_found=False)
        if not blueprint:
            return

        definition = blueprint.definition
        self.assertIsInstance(definition, list)
        self.assertEqual(len(definition), 2)

        create_model = definition[0]
        self.assertEqual(create_model['type'], 'create')
        self.assertEqual(create_model['model'], 'test_populate.supplier')
        self.assertEqual(create_model['count'], 5)
        self.assertEqual(create_model.get('id'), 'some_supplies')

        write_model = definition[1]
        self.assertEqual(write_model['model'], 'test_populate.supplier')
        self.assertEqual(write_model['type'], 'write')
        self.assertEqual(write_model.get('ref'), 'some_supplies')
        self.assertNotIn('count', write_model)

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        self.assertEqual(len(session.job_ids), 2)

        create_job = session.job_ids.filtered(lambda j: j.type == 'create')
        write_job = session.job_ids.filtered(lambda j: j.type == 'write')

        self.assertEqual(len(create_job), 1)
        self.assertEqual(len(write_job), 1)

        self.assertEqual(create_job.model_name, 'test_populate.supplier')
        self.assertEqual(create_job.record_count, 5)
        self.assertEqual(create_job.ref, 'some_supplies')
        self.assertEqual(create_job.type, 'create')
        self.assertIn('name', create_job.instructions['fields'])
        self.assertIn('is_active', create_job.instructions['fields'])

        self.assertEqual(write_job.model_name, 'test_populate.supplier')
        self.assertEqual(write_job.ref, 'some_supplies')
        self.assertEqual(write_job.type, 'write')
        self.assertIn('is_active', write_job.instructions['fields'])

        self.assertLess(create_job.id, write_job.id)  # jobs are created in order of dependencies

    def test_value_parsing(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Value Parse Test',
            'definition_xml': '''
                <data>
                    <create model="test_populate.product" count="1">
                        <field name="name" generator="textual.char"/>
                        <value name="cost" eval="lambda: 50.0"/>
                    </create>
                </data>
            ''',
        })

        self.assertIn('cost', blueprint.definition[0]['values'])
        self.assertNotIn('cost', blueprint.definition[0]['fields'])
