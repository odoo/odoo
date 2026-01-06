from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestVirtualFieldsJSON(PopulateTestCase):

    def test_virtual_fields_nodb_write_json_definition(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Virtual Fields Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15, 'null_ratio': 0.0},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0, 'null_ratio': 0.0},
                        'cost': {'virtual': True, 'eval': 'price * 0.7'},
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


class TestVirtualFieldsXML(PopulateTestCase):

    def test_virtual_fields_nodb_write_xml_definition(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Virtual Fields XML Test',
            'definition_xml': '''
                <data>
                    <model name="test_populate.product" count="5">
                        <field name="name" generator="textual.char" length="15" null_ratio="0"/>
                        <field name="price" generator="scalar.float" start="50.0" end="150.0" null_ratio="0"/>
                        <field name="cost" virtual="true" eval="price * 0.6"/>
                    </model>
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


class TestVirtualFieldDependencies(PopulateTestCase):

    def test_virtual_fields_for_computed_dependencies(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Virtual Fields Dependency Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 100.0, 'end': 200.0},
                        'cost': {
                            'virtual': True,
                            'eval': 'price * 0.65',
                        },
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

    def test_virtual_fields_multiple_levels(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Multiple Virtual Fields Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'price': {'generator': 'scalar.float', 'start': 100.0, 'end': 200.0},
                        'markup': {
                            'virtual': True,
                            'eval': '0.3',
                        },
                        'cost': {
                            'virtual': True,
                            'eval': 'price / (1 + markup)',
                        },
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

    def test_virtual_fields_not_in_model_noop(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Nonexistent Virtual Field Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'price': {'generator': 'scalar.float'},
                        'fake_field': {
                            'virtual': True,
                            'eval': '123',
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
        self.assertEqual(len(created_products), 2)
