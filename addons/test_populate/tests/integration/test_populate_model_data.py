from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestModelDataCreation(PopulateTestCase):

    def test_populated_records_have_model_data_entries(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Model Data Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_model_data_count = self.env['populate.model.data'].search_count([])

        start_populate(session)

        final_model_data_count = self.env['populate.model.data'].search_count([])

        self.assertEqual(final_model_data_count - initial_model_data_count, 3)

        model_data_entries = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.product'),
            ('session_id', '=', session.id),
        ])
        self.assertEqual(len(model_data_entries), 3)

        for entry in model_data_entries:
            self.assertTrue(entry.res_id)
            self.assertEqual(entry.res_model, 'test_populate.product')
            self.assertEqual(entry.session_id, session)
            self.assertEqual(entry.blueprint_id, blueprint)

    def test_multiple_models_create_separate_model_data_entries(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multi-Model Data Entries Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                    },
                },
                {
                    'name': 'test_populate.customer',
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

        start_populate(session)

        product_entries = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.product'),
            ('session_id', '=', session.id),
        ])
        self.assertEqual(len(product_entries), 2)

        customer_entries = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.customer'),
            ('session_id', '=', session.id),
        ])
        self.assertEqual(len(customer_entries), 3)


class TestModelDataRefs(PopulateTestCase):

    def test_ref_field_properly_set_in_model_data(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Ref Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'special_products',
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

        start_populate(session)

        model_data_entries = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.product'),
            ('session_id', '=', session.id),
        ])
        self.assertEqual(len(model_data_entries), 2)

        for entry in model_data_entries:
            self.assertEqual(entry.ref, 'special_products')
