from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Sample, Selection


class TestSelectionGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.category_field = test_product_model._fields['category']

    def test_selection_generator(self):
        generator = Selection(field=self.category_field, env=self.env)

        values = [generator.next({}) for _ in range(50)]

        valid_values = dict(self.category_field.selection).keys()
        valid_values = list(valid_values) + [False]

        self.assertTrue(all(val in valid_values for val in values))

    def test_selection_generator_custom_values(self):
        custom_values = ['electronics', 'books']
        generator = Selection(
            field=self.category_field,
            env=self.env,
            values=custom_values,
        )

        values = [generator.next({}) for _ in range(20)]

        self.assertTrue(all(val in custom_values for val in values))

    def test_selection_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            Selection(field=self.category_field, env=self.env, unique=True)

        self.assertIn("Unique cannot be used with the selection generator", str(cm.exception))


class TestSampleGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']

    def test_sample_generator_basic(self):
        values = ['a', 'b', 'c']
        generator = Sample(field=self.name_field, env=self.env, values=values)

        values_generated = [generator.next({}) for _ in range(20)]

        self.assertTrue(all(val in values for val in values_generated))
        self.assertGreater(len(set(values_generated)), 1)

    def test_sample_generator_weights(self):
        values = {'common': 100, 'rare': 1}
        generator = Sample(field=self.name_field, env=self.env, values=values)

        values_generated = [generator.next({}) for _ in range(50)]

        self.assertTrue(all(val in values for val in values_generated))
        self.assertIn('common', values_generated)
        self.assertGreater(values_generated.count('common'), values_generated.count('rare'))

    def test_sample_generator_empty_values(self):
        with self.assertRaises(ValueError):
            Sample(field=self.name_field, env=self.env, values=[])
