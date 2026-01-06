from odoo.fields import Many2oneReference
from odoo.tests import TransactionCase

from odoo.addons.populate import start_populate
from odoo.addons.populate.generators import (
    ReferenceOne,
    ReferenceRaw,
    UnmetDependencies,
)
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestReferenceOne(TransactionCase):

    def setUp(self):
        super().setUp()
        test_reference_model = self.env['test_populate.reference']
        self.res_id_field = test_reference_model._fields['res_id']

    def test_reference_one_generator_basic(self):
        test_products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
            {'name': 'Product C', 'price': 30.0},
        ])

        generator = ReferenceOne(field=self.res_id_field, env=self.env)

        values = []
        for _ in range(10):
            value = generator.next({'res_model': 'test_populate.product'})
            values.append(value)

        for value in values:
            self.assertIn(value, test_products.ids)

    def test_reference_one_generator_dependency(self):
        generator = ReferenceOne(field=self.res_id_field, env=self.env)

        with self.assertRaises(UnmetDependencies):
            generator.next({})

        try:
            generator.next({'res_model': 'test_populate.product'})
        except UnmetDependencies:  # noqa:TRY203
            # Shouldn't be raised, as the dependency is provided.
            raise

    def test_reference_one_generator_empty_recordset(self):
        generator = ReferenceOne(field=self.res_id_field, env=self.env)

        values = [generator.next({'res_model': 'test_populate.customer'}) for _ in range(20)]

        self.assertTrue(all(value is False for value in values))

    def test_reference_one_generator_different_models(self):
        products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Supplier A', 'country_code': 'US'},
            {'name': 'Supplier B', 'country_code': 'CA'},
        ])

        generator = ReferenceOne(field=self.res_id_field, env=self.env)

        product_values = [generator.next({'res_model': 'test_populate.product'}) for _ in range(10)]
        for value in product_values:
            self.assertIn(value, products.ids)

        supplier_values = [generator.next({'res_model': 'test_populate.supplier'}) for _ in range(10)]
        for value in supplier_values:
            self.assertIn(value, suppliers.ids)

    def test_reference_one_generator_field_type_validation(self):
        self.assertIsInstance(self.res_id_field, Many2oneReference)
        generator = ReferenceOne(field=self.res_id_field, env=self.env)
        self.assertIsInstance(generator, ReferenceOne)

        name_field = self.env['test_populate.product']._fields['name']
        with self.assertRaises(TypeError):
            ReferenceOne(field=name_field, env=self.env)


class TestReferenceRaw(TransactionCase):

    def setUp(self):
        super().setUp()
        test_reference_model = self.env['test_populate.reference']
        self.reference_field = test_reference_model._fields['reference']

    def test_reference_raw_generator_basic(self):
        products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Supplier A', 'country_code': 'US'},
            {'name': 'Supplier B', 'country_code': 'CA'},
        ])

        generator = ReferenceRaw(field=self.reference_field, env=self.env)

        values = [generator.next({}) for _ in range(20)]

        valid_refs = set()
        for product in products:
            valid_refs.add(f"test_populate.product,{product.id}")
        for supplier in suppliers:
            valid_refs.add(f"test_populate.supplier,{supplier.id}")

        for value in values:
            self.assertIn(value, valid_refs)

    def test_reference_raw_generator_with_depends_model_and_id(self):
        products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            res_model='res_model',
            res_id='res_id_value',
            valid_fields=['reference', 'res_model', 'res_id_value'],
        )

        value = generator.next({
            'res_model': 'test_populate.product',
            'res_id_value': str(products[0].id),
        })

        self.assertEqual(value, f"test_populate.product,{products[0].id}")

    def test_reference_raw_generator_with_depends_model_only(self):
        products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            res_model='res_model',
        )

        values = [generator.next({'res_model': 'test_populate.product'}) for _ in range(10)]

        for value in values:
            self.assertTrue(value.startswith('test_populate.product,'))
            record_id = int(value.split(',')[1])
            self.assertIn(record_id, products.ids)

    def test_reference_raw_generator_null_ratio(self):
        self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
        ])

        generator = ReferenceRaw(field=self.reference_field, env=self.env, null_ratio=0.9)

        values = [generator.next({}) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

    def test_reference_raw_generator_invalid_model_in_depends(self):
        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            res_model='res_model',
        )

        with self.assertRaises(ValueError) as cm:
            generator.next({'res_model': 'invalid.model.name'})

        self.assertIn("not in the allowed models", str(cm.exception))

    def test_reference_raw_generator_convert_to_kwargs(self):
        attrs = {
            'generator': 'reference.raw',
            'ref': 'special_products',
            'null_ratio': '0.2',
        }

        kwargs = ReferenceRaw.convert_to_kwargs(attrs)

        self.assertIn('ref', kwargs)
        self.assertEqual(kwargs['ref'], 'special_products')
        self.assertIn('null_ratio', kwargs)
        self.assertEqual(kwargs['null_ratio'], 0.2)


class TestReferenceRawSessionBinding(PopulateTestCase):

    def setUp(self):
        super().setUp()
        self.reference_field = self.env['test_populate.reference']._fields['reference']

        self.blueprint = self.env['populate.blueprint'].create({
            'name': 'Product Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'special_products',
                    'count': 3,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'price': {'generator': 'scalar.float', 'start': 1.0, 'end': 50.0},
                    },
                },
            ],
        })

        self.session_a = self.env['populate.session'].create({'blueprint_id': self.blueprint.id})
        start_populate(self.session_a)

        self.session_b = self.env['populate.session'].create({'blueprint_id': self.blueprint.id})
        start_populate(self.session_b)

        self.session_a_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'special_products'),
            ('session_id', '=', self.session_a.id),
        ]).mapped('res_id'))

        self.session_b_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'special_products'),
            ('session_id', '=', self.session_b.id),
        ]).mapped('res_id'))

    def test_ref_without_session_picks_from_all(self):
        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            res_model='res_model',
            ref='special_products',
        )

        seen_ids = set()
        for _ in range(50):
            value = generator.next({'res_model': 'test_populate.product'})
            if value:
                _, record_id = value.split(',')
                seen_ids.add(int(record_id))

        all_ids = self.session_a_product_ids | self.session_b_product_ids
        self.assertEqual(seen_ids, all_ids)

    def test_ref_with_session_scopes_to_that_session(self):
        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            session=self.session_a,
            res_model='res_model',
            ref='special_products',
        )

        for _ in range(20):
            value = generator.next({'res_model': 'test_populate.product'})
            self.assertIsNot(value, False)
            _, record_id = value.split(',')
            self.assertIn(int(record_id), self.session_a_product_ids)
            self.assertNotIn(int(record_id), self.session_b_product_ids)

    def test_ref_with_empty_session_returns_false(self):
        session_c = self.env['populate.session'].create({'blueprint_id': self.blueprint.id})
        # session_c has not been started, so no model data entries exist

        generator = ReferenceRaw(
            field=self.reference_field,
            env=self.env,
            session=session_c,
            res_model='res_model',
            ref='special_products',
        )

        values = [generator.next({'res_model': 'test_populate.product'}) for _ in range(10)]
        self.assertTrue(all(v is False for v in values))
