from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestBlueprintDefinition(TransactionCase):

    def test_xml_definition_priority(self):
        json_def = [{'type': 'create', 'model': 'test_populate.product', 'count': 5, 'fields': {}}]
        xml_def = '<data><create model="test_populate.customer" count="3"></create></data>'

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Priority Test',
            'definition_json': json_def,
            'definition_xml': xml_def,
        })

        parsed_xml_def = [
            {
                'type': 'create',
                'model': 'test_populate.customer',
                'count': 3,
                'fields': {},
                'values': {},
            },
        ]
        self.assertEqual(blueprint.definition, parsed_xml_def)

    def test_definition_compute_json_only(self):
        json_def = [
            {
                'type': 'create',
                'model': 'test_populate.product',
                'count': 10,
                'fields': {
                    'name': {'generator': 'textual.char'},
                    'price': {'generator': 'scalar.float'},
                },
            },
        ]

        blueprint = self.env['populate.blueprint'].create({
            'name': 'JSON Only Test',
            'definition_json': json_def,
        })

        self.assertEqual(blueprint.definition, json_def)

    @mute_logger('odoo.sql_db')
    def test_blueprint_with_no_definition_fails(self):
        with self.assertRaises(IntegrityError):
            self.env['populate.blueprint'].create({
                'name': 'Invalid Blueprint',
            })

    @mute_logger('odoo.sql_db')
    def test_blueprint_name_required(self):
        with self.assertRaises(IntegrityError):
            self.env['populate.blueprint'].create({
                'definition_json': [{'type': 'create', 'model': 'test_populate.product', 'count': 1, 'fields': {}}],
            })

    def test_blueprint_instantiation_creates_jobs(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Instantiation Test',
            'definition_json': [
                {
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                    },
                },
                {
                    'type': 'create',
                    'model': 'test_populate.customer',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'email': {'generator': 'textual.char'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        assert session

        self.assertEqual(len(session.job_ids), 2)

        product_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.product')
        customer_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.customer')

        self.assertTrue(product_job)
        self.assertTrue(customer_job)

        self.assertEqual(product_job.record_count, 5)
        self.assertEqual(customer_job.record_count, 3)

        self.assertIn('name', product_job.instructions['fields'])
        self.assertIn('price', product_job.instructions['fields'])
        self.assertIn('name', customer_job.instructions['fields'])
        self.assertIn('email', customer_job.instructions['fields'])

    def test_invalid_model_in_definition_raises(self):
        with self.assertRaises(ExceptionGroup) as ctx:
            self.env['populate.blueprint'].create({
                'name': 'Invalid Model Test',
                'definition_json': [{'type': 'create', 'model': 'populate.does_not_exist', 'count': 1, 'fields': {}}],
            })

        errors = ctx.exception.exceptions
        self.assertTrue(all(isinstance(e, ValidationError) for e in errors))
        self.assertTrue(any("populate.does_not_exist" in str(e) for e in errors))

    def test_multiple_invalid_models_all_reported(self):
        with self.assertRaises(ExceptionGroup) as ctx:
            self.env['populate.blueprint'].create({
                'name': 'Multi Invalid Model Test',
                'definition_json': [
                    {'type': 'create', 'model': 'populate.ghost_one', 'count': 1, 'fields': {}},
                    {'type': 'create', 'model': 'populate.ghost_two', 'count': 1, 'fields': {}},
                ],
            })

        errors = ctx.exception.exceptions
        self.assertEqual(len(errors), 2)

    def test_invalid_field_in_definition_raises(self):
        with self.assertRaises(ExceptionGroup) as ctx:
            self.env['populate.blueprint'].create({
                'name': 'Invalid Field Test',
                'definition_json': [{
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 1,
                    'fields': {
                        'nonexistent_field': {'generator': 'textual.char'},
                    },
                }],
            })

        errors = ctx.exception.exceptions
        self.assertTrue(all(isinstance(e, ValidationError) for e in errors))
        self.assertTrue(any("nonexistent_field" in str(e) for e in errors))

    def test_value_skips_field_existence_check(self):
        """Values are not ORM fields, so they do not trigger a ValidationError."""
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Generated Value Test',
            'definition_json': [{
                'type': 'create',
                'model': 'test_populate.product',
                'count': 1,
                'values': {
                    'nonexistent_value': {'generator': 'textual.char'},
                },
                'fields': {
                    'name': {'generator': 'textual.char'},
                },
            }],
        })
        self.assertTrue(blueprint)

    def test_duplicate_field_value_name_raises(self):
        with self.assertRaises(ExceptionGroup) as ctx:
            self.env['populate.blueprint'].create({
                'name': 'Duplicate Field Value Test',
                'definition_json': [{
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 1,
                    'values': {
                        'name': {'generator': 'textual.char'},
                    },
                    'fields': {
                        'name': {'generator': 'textual.char'},
                    },
                }],
            })

        self.assertIn('name', str(ctx.exception.exceptions[0]))

    def test_multiple_invalid_orm_fields_all_reported(self):
        with self.assertRaises(ExceptionGroup) as ctx:
            self.env['populate.blueprint'].create({
                'name': 'Multi Invalid Fields Test',
                'definition_json': [{
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 1,
                    'fields': {
                        'ghost_field_a': {'generator': 'textual.char'},
                        'ghost_field_b': {'generator': 'scalar.float'},
                    },
                }],
            })

        errors = ctx.exception.exceptions
        # Both invalid fields should be reported in a single error for the model
        self.assertEqual(len(errors), 1)
        self.assertIn('ghost_field_a', str(errors[0]))
        self.assertIn('ghost_field_b', str(errors[0]))
