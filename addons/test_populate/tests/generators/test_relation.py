from odoo.fields import Domain
from odoo.tests import TransactionCase

from odoo.addons.populate import start_populate
from odoo.addons.populate.generators import RelationMany, RelationOne
from odoo.addons.populate.utils.orm import DynamicDomain, VirtualField
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestRelationOne(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.supplier_field = test_product_model._fields['supplier_id']

    def test_relation_generator_basic(self):
        test_suppliers = self.env['test_populate.supplier'].create([
            {'name': 'Test Supplier A', 'country_code': 'US', 'is_active': True},
            {'name': 'Test Supplier B', 'country_code': 'CA', 'is_active': True},
            {'name': 'Test Supplier C', 'country_code': 'US', 'is_active': False},
        ])

        generator = RelationOne(field=self.supplier_field, env=self.env)

        values = [generator.next({}) for _ in range(50)]

        valid_supplier_ids = test_suppliers.ids
        for value in values:
            self.assertTrue(value is False or value in valid_supplier_ids)

    def test_relation_generator_with_domain(self):
        test_suppliers = self.env['test_populate.supplier'].create([
            {'name': 'US Active Supplier', 'country_code': 'US', 'is_active': True},
            {'name': 'CA Active Supplier', 'country_code': 'CA', 'is_active': True},
            {'name': 'US Inactive Supplier', 'country_code': 'US', 'is_active': False},
        ])

        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=[('country_code', '=', 'US'), ('is_active', '=', True)],
        )

        values = [generator.next({}) for _ in range(30)]

        active_us_suppliers = test_suppliers.filtered(lambda s: s.country_code == 'US' and s.is_active)
        valid_ids = active_us_suppliers.ids

        for value in values:
            self.assertTrue(value is False or value in valid_ids)

    def test_relation_generator_null_ratio(self):
        self.env['test_populate.supplier'].create([
            {'name': 'Test Supplier', 'country_code': 'US', 'is_active': True},
        ])

        generator = RelationOne(field=self.supplier_field, env=self.env, null_ratio=0.9)

        values = [generator.next({}) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

        generator_low_null = RelationOne(field=self.supplier_field, env=self.env, null_ratio=0.1)

        values_low_null = [generator_low_null.next({}) for _ in range(100)]
        false_count_low = values_low_null.count(False)

        self.assertLess(false_count_low, 30)

    def test_relation_generator_empty_recordset(self):
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=[('country_code', '=', 'XYZ')],
        )

        values = [generator.next({}) for _ in range(20)]

        self.assertTrue(all(value is False for value in values))

    def test_relation_generator_field_type_validation(self):
        generator = RelationOne(field=self.supplier_field, env=self.env)
        self.assertIsInstance(generator, RelationOne)

        name_field = self.env['test_populate.product']._fields['name']
        with self.assertRaises(TypeError):
            RelationOne(field=name_field, env=self.env)

    def test_relation_one_virtual_requires_comodel_name(self):
        virtual_field = VirtualField('test_populate.product', 'v_supplier_id')
        with self.assertRaises(ValueError) as cm:
            RelationOne(
                field=virtual_field,
                env=self.env,
                valid_fields=['v_supplier_id'],
            )
        self.assertIn("comodel_name", str(cm.exception))

    def test_relation_one_virtual_with_comodel_name(self):
        supliers = self.env['test_populate.supplier'].create([
            {'name': 'Supplier A'},
            {'name': 'Supplier B'},
        ])
        virtual_field = VirtualField('test_populate.product', 'v_supplier_id')
        generator = RelationOne(
            field=virtual_field,
            env=self.env,
            comodel_name='test_populate.supplier',
            valid_fields=['v_supplier_id'],
        )
        values = [generator.next({}) for _ in range(20)]
        self.assertTrue(all(isinstance(v, int) and v in supliers.ids for v in values))

    def test_relation_one_virtual_invalid_comodel_name_raises(self):
        virtual_field = VirtualField('test_populate.product', 'v_supplier_id')
        with self.assertRaises(ValueError) as cm:
            RelationOne(
                field=virtual_field,
                env=self.env,
                comodel_name='not.a.real.model',
                valid_fields=['v_supplier_id'],
            )
        self.assertIn("isn't a valid model name", str(cm.exception))


class TestRelationOneSessionBinding(PopulateTestCase):
    """Test that RelationOne with `ref` + `session` scopes records to that session."""

    def setUp(self):
        super().setUp()
        self.supplier_field = self.env['test_populate.product']._fields['supplier_id']
        blueprint = self.env['populate.blueprint'].create({
            'name': 'Supplier Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.supplier',
                    'ref': 'my_suppliers',
                    'count': 3,
                    'fields': {'name': {'generator': 'textual.char', 'length': 10}},
                },
            ],
        })

        self.session_a = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(self.session_a)

        self.session_b = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(self.session_b)

    def test_ref_without_session_picks_from_all_sessions(self):
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            ref='my_suppliers',
        )

        all_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('res_model', '=', 'test_populate.supplier'),
        ]).mapped('res_id')

        self.assertEqual(len(all_supplier_ids), 6)
        self.assertEqual(set(generator.comodel_ids), set(all_supplier_ids))

    def test_ref_with_session_scopes_to_that_session(self):
        session_a_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('session_id', '=', self.session_a.id),
        ]).mapped('res_id')

        session_b_supplier_ids = self.env['populate.model.data'].search([
            ('ref', '=', 'my_suppliers'),
            ('session_id', '=', self.session_b.id),
        ]).mapped('res_id')

        # Scoped to session A
        gen_a = RelationOne(
            field=self.supplier_field,
            env=self.env,
            session=self.session_a,
            ref='my_suppliers',
        )
        self.assertEqual(set(gen_a.comodel_ids), set(session_a_supplier_ids))
        self.assertTrue(set(gen_a.comodel_ids).isdisjoint(set(session_b_supplier_ids)))

        # Scoped to session B
        gen_b = RelationOne(
            field=self.supplier_field,
            env=self.env,
            session=self.session_b,
            ref='my_suppliers',
        )
        self.assertEqual(set(gen_b.comodel_ids), set(session_b_supplier_ids))
        self.assertTrue(set(gen_b.comodel_ids).isdisjoint(set(session_a_supplier_ids)))


class TestRelationOneDynamicDomain(TransactionCase):

    def setUp(self):
        super().setUp()
        self.supplier_field = self.env['test_populate.product']._fields['supplier_id']
        self.env['test_populate.supplier'].create([
            {'name': 'US Supplier', 'country_code': 'US', 'is_active': True},
            {'name': 'CA Supplier', 'country_code': 'CA', 'is_active': True},
        ])

    def test_dynamic_domain_comodel_ids_is_none(self):
        dynamic_domain = DynamicDomain("[('country_code', '=', country_code)]")
        self.assertIsInstance(dynamic_domain, DynamicDomain)
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=dynamic_domain,
            valid_fields=['country_code'],
        )
        self.assertIsNone(generator.comodel_ids)

    def test_static_domain_comodel_ids_is_not_none(self):
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=[('country_code', '=', 'US')],
        )
        self.assertIsNotNone(generator.comodel_ids)

    def test_dynamic_domain_filters_per_call(self):
        dynamic_domain = DynamicDomain("[('country_code', '=', country_code)]")
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=dynamic_domain,
            valid_fields=['country_code'],
        )

        us_suppliers = self.env['test_populate.supplier'].search([('country_code', '=', 'US')])
        ca_suppliers = self.env['test_populate.supplier'].search([('country_code', '=', 'CA')])

        for _ in range(10):
            val_us = generator.next({'country_code': 'US'})
            self.assertIn(val_us, us_suppliers.ids)

            val_ca = generator.next({'country_code': 'CA'})
            self.assertIn(val_ca, ca_suppliers.ids)

    def test_dynamic_domain_depends_extended(self):
        dynamic_domain = DynamicDomain("[('country_code', '=', country_code)]")
        generator = RelationOne(
            field=self.supplier_field,
            env=self.env,
            domain=dynamic_domain,
            valid_fields=['country_code'],
        )
        self.assertIn('country_code', generator.depends)

    def test_convert_to_kwargs_static_domain(self):
        attrs = {'domain': "[('country_code', '=', 'US')]"}
        kwargs = RelationOne.convert_to_kwargs(attrs)
        self.assertIsInstance(kwargs['domain'], Domain)

    def test_convert_to_kwargs_dynamic_domain(self):
        attrs = {'domain': "[('country_code', '=', country_code)]"}
        kwargs = RelationOne.convert_to_kwargs(attrs)
        self.assertIsInstance(kwargs['domain'], DynamicDomain)


class TestRelationMany(TransactionCase):

    def setUp(self):
        super().setUp()
        supplier_model = self.env['test_populate.supplier']
        self.product_ids_field = supplier_model._fields['product_ids']

    def test_relation_many_generator_basic(self):
        test_products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
            {'name': 'Product C', 'price': 30.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=2)

        values = [generator.next({}) for _ in range(10)]

        for value in values:
            if value:
                selected_ids = value[0][2]
                self.assertEqual(len(selected_ids), 2)
                for product_id in selected_ids:
                    self.assertIn(product_id, test_products.ids)

    def test_relation_many_generator_with_domain(self):
        self.env['test_populate.product'].create([
            {'name': 'Electronics A', 'category': 'electronics', 'price': 10.0},
            {'name': 'Electronics B', 'category': 'electronics', 'price': 20.0},
            {'name': 'Book A', 'category': 'books', 'price': 15.0},
            {'name': 'Book B', 'category': 'books', 'price': 25.0},
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=2,
            domain=[('category', '=', 'electronics')],
        )

        values = [generator.next({}) for _ in range(10)]

        electronics_products = self.env['test_populate.product'].search([('category', '=', 'electronics')])
        books_products = self.env['test_populate.product'].search([('category', '=', 'books')])

        for value in values:
            if value:
                selected_ids = value[0][2]
                self.assertEqual(len(selected_ids), 2)
                for product_id in selected_ids:
                    self.assertIn(product_id, electronics_products.ids)
                    self.assertNotIn(product_id, books_products.ids)

    def test_relation_many_generator_null_ratio(self):
        self.env['test_populate.product'].create([
            {'name': 'Product 1', 'price': 10.0},
            {'name': 'Product 2', 'price': 20.0},
            {'name': 'Product 3', 'price': 30.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=2, null_ratio=0.9)

        values = [generator.next({}) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

    def test_relation_many_generator_count_exceeds_available(self):
        test_products = self.env['test_populate.product'].create([
            {'name': 'Product A', 'price': 10.0},
            {'name': 'Product B', 'price': 20.0},
        ])

        generator = RelationMany(field=self.product_ids_field, env=self.env, count=5)

        value = generator.next({})
        if value:
            selected_ids = value[0][2]
            self.assertEqual(len(selected_ids), 2)
            self.assertEqual(set(selected_ids), set(test_products.ids))

    def test_relation_many_generator_field_type_validation(self):
        generator = RelationMany(field=self.product_ids_field, env=self.env, count=1)
        self.assertIsInstance(generator, RelationMany)

        name_field = self.env['test_populate.supplier']._fields['name']
        with self.assertRaises(TypeError):
            RelationMany(field=name_field, env=self.env, count=1)

    def test_relation_many_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            RelationMany(field=self.product_ids_field, env=self.env, count=2, unique=True)

        self.assertIn("Unique cannot be used with the 'relation.many' generator", str(cm.exception))

    def test_relation_many_generator_with_std_variance(self):
        self.env['test_populate.product'].create([
            {'name': f'Product {i}', 'price': float(i * 10)}
            for i in range(20)
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=10,
            std=3,
        )

        counts = []
        for _ in range(200):
            value = generator.next({})
            self.assertIsNot(value, False)
            selected_ids = value[0][2]
            counts.append(len(selected_ids))

        # With std=3 and count=10, samples should vary around 10
        # but not all be exactly 10.
        unique_counts = set(counts)
        self.assertGreater(len(unique_counts), 1, "std > 0 should produce varying counts")

        self.assertTrue(all(c >= 1 for c in counts), 'All counts should be at least 1 ')

    def test_relation_many_generator_std_zero_means_fixed_count(self):
        self.env['test_populate.product'].create([
            {'name': f'Product {i}', 'price': float(i * 10)}
            for i in range(10)
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=5,
            std=0,
        )

        counts = set()
        for _ in range(50):
            value = generator.next({})
            self.assertIsNot(value, False)
            counts.add(len(value[0][2]))

        self.assertEqual(counts, {5}, "std=0 should always produce exactly `count` records")

    def test_relation_many_generator_std_capped_by_available(self):
        products = self.env['test_populate.product'].create([
            {'name': f'Product {i}', 'price': float(i)}
            for i in range(3)
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=10,
            std=5,
        )

        for _ in range(30):
            value = generator.next({})
            if value:
                selected_ids = value[0][2]
                self.assertLessEqual(len(selected_ids), len(products))

    def test_relation_many_generator_std_ensures_at_least_one(self):
        self.env['test_populate.product'].create([
            {'name': f'Product {i}', 'price': float(i)}
            for i in range(20)
        ])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=2,
            std=10,  # Very high std relative to count -> Gaussian could go negative
        )

        for _ in range(100):
            value = generator.next({})
            self.assertIsNot(value, False)
            selected_ids = value[0][2]
            self.assertGreaterEqual(len(selected_ids), 1)

    def test_relation_many_generator_negative_std_raises(self):
        with self.assertRaises(AssertionError):
            RelationMany(
                field=self.product_ids_field,
                env=self.env,
                count=5,
                std=-1,
            )

    def test_relation_many_virtual_requires_comodel_name(self):
        virtual_field = VirtualField('test_populate.product', 'v_tag_ids')
        with self.assertRaises(ValueError) as cm:
            RelationMany(
                field=virtual_field,
                env=self.env,
                count=2,
                valid_fields=['v_tag_ids'],
            )
        self.assertIn("comodel_name", str(cm.exception))

    def test_relation_many_virtual_with_comodel_name(self):
        tags = self.env['test_populate.tag'].create([
            {'name': 'Tag A'},
            {'name': 'Tag B'},
            {'name': 'Tag C'},
        ])
        virtual_field = VirtualField('test_populate.product', 'v_tag_ids')
        generator = RelationMany(
            field=virtual_field,
            env=self.env,
            comodel_name='test_populate.tag',
            count=2,
            valid_fields=['v_tag_ids'],
        )
        value = generator.next({})
        self.assertIsInstance(value, list)
        self.assertEqual(len(value[0][2]), 2)
        self.assertTrue(all(v in tags.ids for v in value[0][2]))

    def test_relation_many_virtual_invalid_comodel_name_raises(self):
        virtual_field = VirtualField('test_populate.product', 'v_tag_ids')
        with self.assertRaises(ValueError) as cm:
            RelationMany(
                field=virtual_field,
                env=self.env,
                comodel_name='not.a.real.model',
                count=2,
                valid_fields=['v_tag_ids'],
            )
        self.assertIn("isn't a valid model name", str(cm.exception))


class TestRelationManySessionBinding(PopulateTestCase):

    def test_ref_with_session_scopes_to_that_session(self):
        product_ids_field = self.env['test_populate.supplier']._fields['product_ids']

        blueprint = self.env['populate.blueprint'].create({
            'name': 'Product Blueprint',
            'definition_json': [
                {
                    'name': 'test_populate.product',
                    'ref': 'tagged_products',
                    'count': 4,
                    'fields': {
                        'name': {'generator': 'textual.char', 'length': 10},
                        'price': {'generator': 'scalar.float', 'start': 1.0, 'end': 50.0},
                    },
                },
            ],
        })

        session_a = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(session_a)

        session_b = self.env['populate.session'].create({'blueprint_id': blueprint.id})
        start_populate(session_b)

        session_a_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'tagged_products'),
            ('session_id', '=', session_a.id),
        ]).mapped('res_id'))

        session_b_product_ids = set(self.env['populate.model.data'].search([
            ('ref', '=', 'tagged_products'),
            ('session_id', '=', session_b.id),
        ]).mapped('res_id'))

        # Scoped to session A
        gen_a = RelationMany(
            field=product_ids_field,
            env=self.env,
            session=session_a,
            ref='tagged_products',
            count=2,
        )
        self.assertEqual(set(gen_a.comodel_ids), session_a_product_ids)

        for _ in range(10):
            value = gen_a.next({})
            if value:
                selected_ids = set(value[0][2])
                self.assertTrue(selected_ids.issubset(session_a_product_ids))
                self.assertTrue(selected_ids.isdisjoint(session_b_product_ids))


class TestRelationManyDynamicDomain(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product_ids_field = self.env['test_populate.supplier']._fields['product_ids']
        self.env['test_populate.product'].create([
            {'name': 'Electronics A', 'category': 'electronics', 'price': 10.0},
            {'name': 'Electronics B', 'category': 'electronics', 'price': 20.0},
            {'name': 'Book A', 'category': 'books', 'price': 5.0},
        ])

    def test_relation_many_dynamic_domain_filters_per_call(self):
        dynamic_domain = DynamicDomain("[('category', '=', category)]")
        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            domain=dynamic_domain,
            valid_fields=['category'],
            count=1,
        )

        electronics = self.env['test_populate.product'].search([('category', '=', 'electronics')])
        books = self.env['test_populate.product'].search([('category', '=', 'books')])

        for _ in range(10):
            val = generator.next({'category': 'electronics'})
            self.assertIsNot(val, False)
            self.assertTrue(all(pid in electronics.ids for pid in val[0][2]))

            val = generator.next({'category': 'books'})
            self.assertIsNot(val, False)
            self.assertTrue(all(pid in books.ids for pid in val[0][2]))


class TestRelationManyGroupby(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product_ids_field = self.env['test_populate.supplier']._fields['product_ids']
        self.env['test_populate.product'].create([
            {'name': 'Electronics A', 'category': 'electronics', 'price': 10.0},
            {'name': 'Electronics B', 'category': 'electronics', 'price': 20.0},
            {'name': 'Book A', 'category': 'books', 'price': 5.0},
            {'name': 'Book B', 'category': 'books', 'price': 15.0},
        ])

    def test_groupby_invalid_field_raises(self):
        with self.assertRaises(ValueError) as cm:
            RelationMany(
                field=self.product_ids_field,
                env=self.env,
                count=1,
                groupby='not_a_real_field',
            )
        self.assertIn('not_a_real_field', str(cm.exception))

    def test_groupby_samples_from_each_group(self):
        electronics = self.env['test_populate.product'].search([('category', '=', 'electronics')])
        books = self.env['test_populate.product'].search([('category', '=', 'books')])

        generator = RelationMany(
            field=self.product_ids_field,
            env=self.env,
            count=1,
            groupby='category',
        )

        value = generator.next({})
        sampled_ids = set(value[0][2])
        self.assertTrue(sampled_ids & set(electronics.ids), "Expected electronics IDs in samples")
        self.assertTrue(sampled_ids & set(books.ids), "Expected book IDs in samples")
