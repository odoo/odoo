from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Char, Text


class TestCharGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.name_field = test_product_model._fields['name']

    def test_char_generator(self):
        generator = Char(field=self.name_field, env=self.env, length=10)

        values = [generator.next({}) for _ in range(10)]

        self.assertTrue(all(isinstance(val, str) and len(val) == 10 for val in values))

        unique_values = set(values)
        self.assertGreater(len(unique_values), 1)

    def test_char_generator_custom_charset(self):
        generator = Char(field=self.name_field, env=self.env, char_set='ABC', length=5)

        value = generator.next({})

        self.assertEqual(len(value), 5)
        self.assertTrue(all(char in 'ABC' for char in value))


class TestTextGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.description_field = test_product_model._fields['description']

    def test_text_generator(self):
        generator = Text(field=self.description_field, env=self.env, length=30)

        values = [generator.next({}) for _ in range(5)]

        self.assertTrue(all(isinstance(val, str) and len(val) == 30 for val in values))
