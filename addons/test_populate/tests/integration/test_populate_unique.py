from odoo.addons.populate import start_populate
from odoo.addons.populate.generators import UniqueValueNotFound
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestUniqueConstraints(PopulateTestCase):

    def test_char_generator_unique_integration_with_blueprint(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unique Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.customer',
                    'count': 10,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15, 'unique': 'True', 'null_ratio': '0'},
                        'email': {'generator': 'textual.char', 'length': 20, 'unique': 'True', 'null_ratio': '0'},
                        'age': {'generator': 'scalar.integer', 'start': '18', 'end': '80'},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        customer_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.customer'),
        ]).mapped('res_id')

        created_customers = self.env['test_populate.customer'].browse(customer_ids)

        names = created_customers.mapped('name')
        self.assertEqual(len(names), len(set(names)))

        emails = created_customers.mapped('email')
        self.assertEqual(len(emails), len(set(emails)))

    def test_unique_field_with_dependency_reroll(self):
        """
        Test that when a unique field can't find a novel value,
        its dependencies are re-rolled to produce new upstream values,
        allowing the unique field to eventually succeed.
        """
        # The eval 'f"product-{category}"' depends on 'category' (4 possible values).
        # With unique=True and count=4, the generator *must* produce all 4 categories
        # to satisfy uniqueness. Since category is random, collisions are near-certain,
        # which raises a NoUniqueValueFoundError -> dependency re-roll path.
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unique Dependency Reroll Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15, 'null_ratio': '0'},
                        'category': {'generator': 'choice.selection', 'null_ratio': '0'},
                        'description': {
                            'eval': 'f"product-{category}"',
                            'unique': 'True',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
            'seed': 42,  # known seed to pass the test & that triggers a re-roll of deps.
        })

        start_populate(session)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(products), 4)

        descriptions = products.mapped('description')
        self.assertEqual(len(descriptions), len(set(descriptions)),
                         "All descriptions should be unique — "
                         "the re-roll mechanism must have varied 'category' to achieve this")

    def test_unique_exhaustion_raises_runtime_error(self):
        """
        When a unique field truly cannot produce a novel value
        (no dependencies to re-roll and all values exhausted),
        a RuntimeError should still be raised.
        """
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Unique Exhaustion Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    # Request more records than possible unique values in range [1, 2]
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'null_ratio': '0'},
                        'stock_quantity': {
                            'generator': 'scalar.integer',
                            'start': '1',
                            'end': '2',
                            'unique': 'True',
                            'null_ratio': '0',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        with self.assertRaises(UniqueValueNotFound) as cm:
            start_populate(session)

        self.assertIn("unique value", str(cm.exception).lower())
