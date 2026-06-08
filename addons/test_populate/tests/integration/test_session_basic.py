from psycopg2 import IntegrityError

from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestSessionCreation(TransactionCase):

    def test_simple_blueprint_creation(self):
        blueprint_data = {
            'name': 'Test Product Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 1000.0},
                        'active': {'generator': 'scalar.boolean'},
                        'category': {'generator': 'choice.selection'},
                        'description': {'generator': 'textual.text', 'length': 100},
                    },
                },
            ],
        }

        blueprint = self.env['populate.blueprint'].create(blueprint_data)
        self.assertEqual(blueprint.name, 'Test Product Blueprint')
        self.assertTrue(blueprint.definition_json)
        self.assertEqual(blueprint.definition, blueprint_data['definition_json'])

    def test_job_creation_and_constraints(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Job Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        self.assertTrue(session.job_ids)
        job = session.job_ids[0]
        self.assertEqual(job.model_name, 'test_populate.product')
        self.assertEqual(job.record_count, 2)
        self.assertEqual(job.session_id, session)

    @mute_logger('odoo.sql_db')
    def test_create_job_with_domain_fails(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Create Domain Blueprint',
            'definition_json': [{
                'name': 'test_populate.product',
                'count': 1,
                'domain': "[('category', '=', 'books')]",
                'fields': {
                    'name': {'generator': 'textual.char'},
                },
            }],
        })

        with self.assertRaises(IntegrityError):
            self.env['populate.session'].create({
                'blueprint_id': blueprint.id,
            })

    @mute_logger('odoo.sql_db')
    def test_blueprint_constraint_validation(self):
        with self.assertRaises(IntegrityError):
            self.env['populate.blueprint'].create({
                'name': 'Invalid Blueprint',
            })


class TestSessionExecution(PopulateTestCase):

    def test_session_creation_and_execution(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Customer Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'email': {'generator': 'textual.char', 'length': 20},
                        'age': {'generator': 'scalar.integer', 'start': 18, 'end': 80},
                        'is_vip': {'generator': 'scalar.boolean'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'worker_count': 1,
        })

        initial_customer_count = self.env['test_populate.customer'].search_count([])

        start_populate(session)

        final_customer_count = self.env['test_populate.customer'].search_count([])
        self.assertEqual(final_customer_count - initial_customer_count, 3)

    def test_multiple_models_blueprint(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multi-Model Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'email': {'generator': 'textual.char', 'length': 25},
                        'rating': {'generator': 'scalar.float', 'start': 1.0, 'end': 5.0},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 5.0, 'end': 500.0},
                        'category': {'generator': 'choice.selection'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_supplier_count = self.env['test_populate.supplier'].search_count([])
        initial_product_count = self.env['test_populate.product'].search_count([])

        start_populate(session)

        final_supplier_count = self.env['test_populate.supplier'].search_count([])
        final_product_count = self.env['test_populate.product'].search_count([])

        self.assertEqual(final_supplier_count - initial_supplier_count, 2)
        self.assertEqual(final_product_count - initial_product_count, 5)

    def test_session_state_transitions_sync(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'State Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 1,
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

        start_populate(session)

        self.assertTrue(session.is_done)

    def test_deleting_blueprint_cascades_to_leftover_session_data(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Cascade Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                    },
                },
            ],
        })
        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        jobs = self.env['populate.job'].search([('session_id', '=', session.id)])
        model_data = self.env['populate.model.data'].search([('job_id', 'in', jobs.ids)])
        products = self.env['test_populate.product'].browse(model_data.mapped('res_id'))
        self.assertTrue(jobs)
        self.assertTrue(model_data)
        self.assertTrue(products)

        blueprint.unlink()

        self.assertFalse(session.exists())
        self.assertFalse(jobs.exists())
        self.assertFalse(model_data.exists())
        self.assertTrue(products.exists())
