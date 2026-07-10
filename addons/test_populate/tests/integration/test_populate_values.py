from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestValuesJSON(PopulateTestCase):

    def test_values_nodb_write_json_definition(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Generated Values Test',
            'definition_json': [
                {
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 3,
                    'values': {
                        'cost': {'eval': 'price * 0.7'},
                    },
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15, 'null_ratio': 0.0},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0, 'null_ratio': 0.0},
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_count = self.env['test_populate.product'].search_count([])

        start_populate(session)

        final_count = self.env['test_populate.product'].search_count([])
        self.assertEqual(final_count - initial_count, 3)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)

        for product in created_products:
            self.assertTrue(product.name)
            self.assertTrue(product.price)
            self.assertEqual(product.cost, 0.0)


class TestValuesXML(PopulateTestCase):

    def test_values_nodb_write_xml_definition(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Generated Values XML Test',
            'definition_xml': '''
                <data>
                    <create model="test_populate.product" count="5">
                        <field name="name" generator="textual.char" length="15" null_ratio="0"/>
                        <field name="price" generator="scalar.float" start="50.0" end="150.0" null_ratio="0"/>
                        <value name="cost" eval="price * 0.6"/>
                    </create>
                </data>
            ''',
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(created_products), 5)

        for product in created_products:
            self.assertTrue(product.name)
            self.assertTrue(product.price)
            self.assertEqual(product.cost, 0.0)


class TestValueDependencies(PopulateTestCase):

    def test_values_for_computed_dependencies(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Generated Values Dependency Test',
            'definition_json': [
                {
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 4,
                    'values': {
                        'cost': {
                            'eval': 'price * 0.65',
                        },
                    },
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 100.0, 'end': 200.0},
                        'description': {
                            'eval': 'f"{name}: Price ${price:.2f}, Cost ${cost:.2f}"',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(created_products), 4)

        for product in created_products:
            expected_cost = product.price * 0.65
            expected_description = f"{product.name}: Price ${product.price:.2f}, Cost ${expected_cost:.2f}"
            self.assertEqual(product.description, expected_description)
            self.assertEqual(product.cost, 0.0)

    def test_values_multiple_levels(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multiple Generated Values Test',
            'definition_json': [
                {
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 3,
                    'values': {
                        'markup': {
                            'eval': '0.3',
                        },
                        'cost': {
                            'eval': 'price / (1 + markup)',
                        },
                    },
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'price': {'generator': 'scalar.float', 'start': 100.0, 'end': 200.0},
                        'stock_quantity': {
                            'eval': 'int(cost * 2)',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(created_products), 3)

        for product in created_products:
            markup = 0.3
            expected_cost = product.price / (1 + markup)
            expected_stock = int(expected_cost * 2)
            self.assertEqual(product.stock_quantity, expected_stock)
            self.assertEqual(product.cost, 0.0)

    def test_values_not_in_model_noop(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Nonexistent Generated Value Test',
            'definition_json': [
                {
                    'type': 'create',
                    'model': 'test_populate.product',
                    'count': 2,
                    'values': {
                        'fake_field': {
                            'eval': '123',
                        },
                    },
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

        product_ids = self.env['populate.model.data'].search([
            ('session_id', '=', session.id),
            ('res_model', '=', 'test_populate.product'),
        ]).mapped('res_id')

        created_products = self.env['test_populate.product'].browse(product_ids)
        self.assertEqual(len(created_products), 2)
