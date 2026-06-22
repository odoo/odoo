from unittest.mock import MagicMock

from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Counter, Cycle, Eval


class TestCounterGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        product_model = self.env['test_populate.product']
        self.price_field = product_model._fields['price']
        self.stock_field = product_model._fields['stock_quantity']

    def test_counter_default_start_and_step(self):
        generator = Counter(field=self.stock_field, env=self.env)

        values = [generator.next({}) for _ in range(5)]
        self.assertEqual(values, [0, 1, 2, 3, 4])

    def test_counter_custom_start_and_step(self):
        generator = Counter(field=self.price_field, env=self.env, start=10, step=5)

        values = [generator.next({}) for _ in range(4)]
        self.assertEqual(values, [10, 15, 20, 25])

    def test_counter_negative_step(self):
        generator = Counter(field=self.stock_field, env=self.env, start=10, step=-3, end=0)

        values = [generator.next({}) for _ in range(4)]
        self.assertEqual(values, [10, 7, 4, 1])

    def test_counter_wraps_around_with_end(self):
        generator = Counter(field=self.stock_field, env=self.env, start=0, step=1, end=3)

        values = [generator.next({}) for _ in range(6)]
        self.assertEqual(values, [0, 1, 2, 0, 1, 2])

    def test_counter_zero_step_raises(self):
        with self.assertRaises(ValueError):
            Counter(field=self.stock_field, env=self.env, step=0)

    def test_counter_positive_step_end_before_start_raises(self):
        with self.assertRaises(ValueError):
            Counter(field=self.stock_field, env=self.env, start=5, step=1, end=3)

    def test_counter_negative_step_end_after_start_raises(self):
        with self.assertRaises(ValueError):
            Counter(field=self.stock_field, env=self.env, start=0, step=-1, end=5)

    def test_counter_null_ratio_is_zero(self):
        generator = Counter(field=self.stock_field, env=self.env)
        self.assertEqual(generator.null_ratio, 0)

    def test_unique_counter_subjobs_use_disjoint_strides(self):
        job_a = MagicMock()
        job_a.id = 1
        job_b = MagicMock()
        job_b.id = 2

        parent = MagicMock()
        parent.child_ids.ids = [job_a.id, job_b.id]
        session = MagicMock()
        session.is_parallel = True

        job_a.env = self.env
        job_a.session_id = session
        job_a.parent_id = parent
        job_b.env = self.env
        job_b.session_id = session
        job_b.parent_id = parent

        generator_a = Counter(field=self.stock_field, env=None, job=job_a, start=10.0, step=5.0, unique=True)
        generator_b = Counter(field=self.stock_field, env=None, job=job_b, start=10.0, step=5.0, unique=True)

        self.assertEqual([generator_a.next({}) for _ in range(4)], [10, 20, 30, 40])
        self.assertEqual([generator_b.next({}) for _ in range(4)], [15, 25, 35, 45])


class TestCycleGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        product_model = self.env['test_populate.product']
        self.name_field = product_model._fields['name']
        self.price_field = product_model._fields['price']

    def test_cycle_loops_through_values(self):
        generator = Cycle(field=self.name_field, env=self.env, values=['a', 'b', 'c'])

        values = [generator.next({}) for _ in range(6)]
        self.assertEqual(values, ['a', 'b', 'c', 'a', 'b', 'c'])

    def test_cycle_single_value(self):
        generator = Cycle(field=self.name_field, env=self.env, values=['only'])

        values = [generator.next({}) for _ in range(3)]
        self.assertTrue(all(v == 'only' for v in values))

    def test_cycle_numeric_values(self):
        generator = Cycle(field=self.price_field, env=self.env, values=[1.0, 2.5, 3.75])

        values = [generator.next({}) for _ in range(3)]
        self.assertEqual(values, [1.0, 2.5, 3.75])

    def test_cycle_empty_values_raises(self):
        with self.assertRaises(ValueError):
            Cycle(field=self.name_field, env=self.env, values=[])

    def test_cycle_weights_raises(self):
        with self.assertRaises(ValueError):
            Cycle(field=self.name_field, env=self.env, values={'a': 1, 'b': 2})

    def test_cycle_null_ratio_is_zero(self):
        generator = Cycle(field=self.name_field, env=self.env, values=['x'])
        self.assertEqual(generator.null_ratio, 0)


class TestEvalGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']
        self.price_field = test_product_model._fields['price']

    def test_eval_generator(self):
        generator = Eval(field=self.name_field, env=self.env, expr='"Test Product"')

        values = [generator.next({}) for _ in range(10)]

        self.assertTrue(all(val == "Test Product" for val in values))

    def test_eval_generator_numeric(self):
        generator = Eval(field=self.price_field, env=self.env, expr='99.99')

        value = generator.next({})
        self.assertEqual(value, 99.99)

    def test_eval_generator_simple_expression(self):
        generator = Eval(field=self.price_field, env=self.env, expr='42 + 69 if True else 420')

        value = generator.next({})
        self.assertEqual(value, 111)

    def test_eval_generator_dynamic_with_depends(self):
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr='price * 2',
            valid_fields=['price'],
        )

        value = generator.next({'price': 50.0})
        self.assertEqual(value, 100.0)

    def test_eval_generator_dynamic_with_multiple_names(self):
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr='price * stock',
            valid_fields=['price', 'stock'],
        )

        value = generator.next({'price': 10.0, 'stock': 5})
        self.assertEqual(value, 50.0)

    def test_eval_generator_dynamic_correct_name_mapping(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr="first.lower() + ' ' + second.upper()",
            valid_fields=['first', 'second'],
        )

        name = 'A Product'
        category = 'A Category'
        value = generator.next({'first': name, 'second': category})
        self.assertEqual(value, name.lower() + ' ' + category.upper())

    def test_eval_generator_rejects_unsafe_kwargs(self):
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr='price',
            valid_fields=['price'],
        )

        with self.assertRaises(TypeError):
            generator.evaluation(price=object())

    def test_eval_generator_dynamic_no_accept_lambda(self):
        with self.assertRaises(ValueError):
            Eval(field=self.name_field, env=self.env, expr='lambda x: 42')

    def test_static_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            Eval(field=self.name_field, env=self.env, expr='"Static Value"', unique=True)

        self.assertIn("Eval returns the same value", str(cm.exception))

    def test_eval_error_includes_expr_in_note(self):
        expr = 'price / 0'
        generator = Eval(
            field=self.price_field,
            env=self.env,
            expr=expr,
            valid_fields=['price'],
        )
        with self.assertRaises(ZeroDivisionError) as cm:
            generator.next({'price': 10.0})

        notes = cm.exception.__notes__
        self.assertTrue(
            any(f"Expression: '{expr}'" in note for note in notes),
            msg=f"Expected expression note not found in: {notes}",
        )


class TestEvalGeneratorContext(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product_model = self.env['test_populate.product']
        self.name_field = self.product_model._fields['name']
        self.price_field = self.product_model._fields['price']
        self.supplier_field = self.product_model._fields['supplier_id']
        self.tag_ids_field = self.product_model._fields['tag_ids']
        self.stock_field = self.product_model._fields['stock_quantity']

    def test_eval_context_env_available(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr='env["test_populate.product"]._name',
        )
        value = generator.next({})
        self.assertEqual(value, 'test_populate.product')

    def test_eval_context_model_available(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr='model._name',
        )
        value = generator.next({})
        self.assertEqual(value, 'test_populate.product')

    def test_eval_context_command_available(self):
        generator = Eval(
            field=self.tag_ids_field,
            env=self.env,
            expr='[Command.set([1, 2, 3])]',
        )
        value = generator.next({})
        self.assertEqual(value, [(6, 0, [1, 2, 3])])

    def test_eval_context_names_not_treated_as_depends(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr='model._name',
        )
        # `model` is provided by the eval context, not a field dependency
        self.assertFalse(generator.depends)

    def test_eval_context_env_not_a_dependency(self):
        generator = Eval(
            field=self.stock_field,
            env=self.env,
            expr='env["test_populate.product"].search_count([])',
        )
        self.assertFalse(generator.depends)

    def test_eval_context_command_not_a_dependency(self):
        generator = Eval(
            field=self.tag_ids_field,
            env=self.env,
            expr='[Command.clear()]',
        )
        self.assertFalse(generator.depends)

    def test_eval_context_mixed_with_field_depends(self):
        generator = Eval(
            field=self.name_field,
            env=self.env,
            expr='model._name + "_" + str(price)',
            valid_fields=['price'],
        )
        # `model` comes from eval context, `price` is a real field dependency
        self.assertEqual(generator.depends, ['price'])
        self.assertNotIn('model', generator.depends)

        value = generator.next({'price': 42.0})
        self.assertEqual(value, 'test_populate.product_42.0')
