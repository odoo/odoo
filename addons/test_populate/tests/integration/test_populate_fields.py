from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestFieldGeneration(PopulateTestCase):

    def test_many2one_field_generation(self):
        suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Supplier A', 'country_code': 'US', 'is_active': True},
            {'name': 'Supplier B', 'country_code': 'CA', 'is_active': True},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Many2One Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0},
                        'supplier_id': {
                            'generator': 'relation.one',
                            'null_ratio': '0',
                        },
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
        self.assertEqual(final_count - initial_count, 5)

        created_products = self.env['test_populate.product'].search([
            ('id', 'in', self.env['populate.model.data'].search([
                ('session_id', '=', session.id),
                ('res_model', '=', 'test_populate.product'),
            ]).mapped('res_id')),
        ])

        products_with_suppliers = created_products.filtered('supplier_id')
        self.assertGreater(len(products_with_suppliers), 0)

        for product in products_with_suppliers:
            self.assertIn(product.supplier_id.id, suppliers.ids)


class TestMany2OnePopulation(PopulateTestCase):

    def test_many2one_with_domain_filtering(self):
        us_supplier, _ = self.env['test_populate.supplier'].create([{
            'name': 'US Supplier', 'country_code': 'US', 'is_active': True,
        }, {
            'name': 'CA Supplier', 'country_code': 'CA', 'is_active': True,
        }])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Domain Filter Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'count': 10,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'supplier_id': {
                            'generator': 'relation.one',
                            'domain': "[('country_code', '=', 'US')]",
                            'null_ratio': '0.1',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        created_products = self.env['test_populate.product'].search([
            ('id', 'in', self.env['populate.model.data'].search([
                ('session_id', '=', session.id),
                ('res_model', '=', 'test_populate.product'),
            ]).mapped('res_id')),
        ])

        for product in created_products.filtered('supplier_id'):
            self.assertEqual(product.supplier_id.country_code, 'US')
            self.assertEqual(product.supplier_id.id, us_supplier.id)

    def test_required_many2one_no_nulls(self):
        self.env['test_populate.customer'].create([
            {'name': 'Customer A', 'email': 'a@test.com'},
            {'name': 'Customer B', 'email': 'b@test.com'},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Required Many2One Test',
            'definition_json': [
                {
                    'name': 'test_populate.order',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'order_date': {'generator': 'temporal.date'},
                        'customer_id': {
                            'generator': 'relation.one',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        created_orders = self.env['test_populate.order'].search([
            ('id', 'in', self.env['populate.model.data'].search([
                ('session_id', '=', session.id),
                ('res_model', '=', 'test_populate.order'),
            ]).mapped('res_id')),
        ])

        self.assertEqual(len(created_orders), 3)
        for order in created_orders:
            self.assertTrue(order.customer_id)

    def test_reference_generator_with_ref_in_blueprint(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Reference with Ref Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'premium_suppliers',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'country_code': {'eval': '"US"'},
                        'is_active': {'eval': 'True'},
                    },
                },
                {
                    'name': 'test_populate.product',
                    'count': 5,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0},
                        'supplier_id': {
                            'generator': 'relation.one',
                            'ref': 'premium_suppliers',
                            'null_ratio': '0.0',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        supplier_model_data = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.supplier'),
            ('session_id', '=', session.id),
            ('ref', '=', 'premium_suppliers'),
        ])
        self.assertEqual(len(supplier_model_data), 3)

        created_supplier_ids = supplier_model_data.mapped('res_id')

        product_model_data = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.product'),
            ('session_id', '=', session.id),
        ])
        self.assertEqual(len(product_model_data), 5)

        created_product_ids = product_model_data.mapped('res_id')
        created_products = self.env['test_populate.product'].browse(created_product_ids)

        for product in created_products:
            self.assertIn(product.supplier_id.id, created_supplier_ids)

        referenced_supplier_ids = set(created_products.supplier_id.ids)
        self.assertLessEqual(referenced_supplier_ids, set(created_supplier_ids))


class TestOne2ManyPopulation(PopulateTestCase):

    def test_one2many_field_generation(self):
        products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
            {'name': 'Product C', 'price': 30.0},
            {'name': 'Product D', 'price': 40.0},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'One2Many Test Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'product_ids': {
                            'generator': 'relation.many',
                            'count': '2',
                            'null_ratio': '0.1',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        initial_count = self.env['test_populate.supplier'].search_count([])

        start_populate(session)

        final_count = self.env['test_populate.supplier'].search_count([])
        self.assertEqual(final_count - initial_count, 3)

        created_suppliers = self.env['test_populate.supplier'].search([
            ('id', 'in', self.env['populate.model.data'].search([
                ('session_id', '=', session.id),
                ('res_model', '=', 'test_populate.supplier'),
            ]).mapped('res_id')),
        ])

        suppliers_with_products = created_suppliers.filtered('product_ids')
        self.assertGreater(len(suppliers_with_products), 0)

        for supplier in suppliers_with_products:
            self.assertLessEqual(len(supplier.product_ids), 2)
            for product in supplier.product_ids:
                self.assertIn(product.id, products.ids)

    def test_one2many_with_domain_filtering(self):
        electronics_products = self.env['test_populate.product'].create([
            {'name': 'Electronics A', 'category': 'electronics', 'price': 10.0},
            {'name': 'Electronics B', 'category': 'electronics', 'price': 20.0},
        ])

        self.env['test_populate.product'].create([
            {'name': 'Book A', 'category': 'books', 'price': 15.0},
            {'name': 'Book B', 'category': 'books', 'price': 25.0},
        ])

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Domain Filter One2Many Test',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char'},
                        'product_ids': {
                            'generator': 'relation.many',
                            'count': '2',
                            'domain': "[('category', '=', 'electronics')]",
                            'null_ratio': '0.0',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        created_suppliers = self.env['test_populate.supplier'].search([
            ('id', 'in', self.env['populate.model.data'].search([
                ('session_id', '=', session.id),
                ('res_model', '=', 'test_populate.supplier'),
            ]).mapped('res_id')),
        ])

        for supplier in created_suppliers:
            for product in supplier.product_ids:
                self.assertEqual(product.category, 'electronics')
                self.assertIn(product.id, electronics_products.ids)

    def test_reference_many_with_ref_in_blueprint(self):
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Reference Many with Ref Test',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'special_products',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 15},
                        'price': {'generator': 'scalar.float', 'start': 10.0, 'end': 100.0},
                        'category': {'eval': '"electronics"'},
                    },
                },
                {
                    'name': 'test_populate.supplier',
                    'count': 2,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 20},
                        'product_ids': {
                            'generator': 'relation.many',
                            'ref': 'special_products',
                            'count': '2',
                            'null_ratio': '0.0',
                        },
                    },
                },
            ],
        })

        session = self.env['populate.session'].create({
            'blueprint_id': blueprint.id,
        })

        start_populate(session)

        product_model_data = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.product'),
            ('session_id', '=', session.id),
            ('ref', '=', 'special_products'),
        ])
        self.assertEqual(len(product_model_data), 4)

        created_product_ids = product_model_data.mapped('res_id')

        supplier_model_data = self.env['populate.model.data'].search([
            ('res_model', '=', 'test_populate.supplier'),
            ('session_id', '=', session.id),
        ])
        created_supplier_ids = supplier_model_data.mapped('res_id')
        created_suppliers = self.env['test_populate.supplier'].browse(created_supplier_ids)

        for supplier in created_suppliers:
            self.assertLessEqual(len(supplier.product_ids), 2)
            for product in supplier.product_ids:
                self.assertIn(product.id, created_product_ids)
