from odoo.tests import TransactionCase

from odoo.addons.populate.generators import (
    Boolean,
    Float,
    Integer,
    Monetary,
    UnmetDependencies,
)


class TestBooleanGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.active_field = test_product_model._fields['active']
        self.is_sellable_field = test_product_model._fields['is_sellable']

    def test_boolean_generator(self):
        for boolean_field, is_required in [
            (self.active_field, False),
            (self.is_sellable_field, True),
        ]:
            self.assertTrue(boolean_field.required == is_required)
            generator = Boolean(field=boolean_field, env=self.env)

            values = [generator.next({}) for _ in range(100)]

            valid_values = {True, False}
            if not is_required:
                valid_values |= {None}
            self.assertTrue(all(val in valid_values for val in values))

            unique_values = set(values)
            self.assertGreater(len(unique_values), 1)

    def test_boolean_generator_unique_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            Boolean(field=self.active_field, env=self.env, unique=True)

        self.assertIn("Unique cannot be used with the boolean generator", str(cm.exception))


class TestIntegerGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.stock_field = test_product_model._fields['stock_quantity']

    def test_integer_generator(self):
        generator = Integer(field=self.stock_field, env=self.env, start=1, end=1000)

        values = [generator.next({}) for _ in range(50)]

        self.assertTrue(all(isinstance(val, int) for val in values))
        self.assertTrue(all(1 <= val <= 1000 for val in values))


class TestFloatGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.price_field = test_product_model._fields['price']

    def test_float_generator(self):
        generator = Float(field=self.price_field, env=self.env, start=10.0, end=100.0)

        values = [generator.next({}) for _ in range(100)]

        self.assertTrue(all(isinstance(val, float) for val in values))
        self.assertTrue(all(10.0 <= val <= 100.0 for val in values))


class TestMonetaryGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.monetary_field = test_product_model._fields['monetary_price']
        self.currency_field = test_product_model._fields['currency_id']
        self.usd = self.env.ref('base.USD')
        self.eur = self.env.ref('base.EUR')

    def test_monetary_generator_basic(self):
        generator = Monetary(field=self.monetary_field, env=self.env, start=10.0, end=1000.0)

        values = [generator.next({'currency_id': self.usd.id}) for _ in range(50)]

        self.assertTrue(all(isinstance(val, float) for val in values))
        self.assertTrue(all(10.0 <= val <= 1000.0 for val in values))

    def test_monetary_generator_rounds_to_currency_decimal_places(self):
        generator = Monetary(field=self.monetary_field, env=self.env, start=1.0, end=9999.99)

        for currency in (self.usd, self.eur):
            values = [generator.next({'currency_id': currency.id}) for _ in range(50)]
            for value in values:
                # The value should be rounded to the currency's decimal places
                self.assertAlmostEqual(value, round(value, currency.decimal_places), places=10)

    def test_monetary_generator_different_decimal_places(self):
        # JPY typically has 0 decimal places (rounding = 1.0)
        jpy = self.env.ref('base.JPY')
        if jpy.decimal_places == 0:
            generator = Monetary(field=self.monetary_field, env=self.env, start=100.0, end=10000.0)
            values = [generator.next({'currency_id': jpy.id}) for _ in range(20)]
            for value in values:
                self.assertEqual(value, round(value, 0))

    def test_monetary_generator_depends_on_currency_field(self):
        generator = Monetary(field=self.monetary_field, env=self.env)

        currency_field_name = self.monetary_field.get_currency_field(self.env[self.monetary_field.model_name])
        self.assertIn(currency_field_name, generator.depends)

    def test_monetary_generator_raises_when_currency_missing(self):
        generator = Monetary(field=self.monetary_field, env=self.env)

        with self.assertRaises(UnmetDependencies):
            generator.next({})

    def test_monetary_generator_without_currency_in_known_vals(self):
        generator = Monetary(field=self.monetary_field, env=self.env, start=1.0, end=500.0)

        # When currency_id is present but falsy (0 / False), no rounding by currency is applied
        value = generator.next({'currency_id': False})
        self.assertIsInstance(value, float)
        self.assertTrue(1.0 <= value <= 500.0)

    def test_monetary_generator_null_ratio(self):
        generator = Monetary(field=self.monetary_field, env=self.env, null_ratio=1.0)

        values = [generator.next({'currency_id': self.usd.id}) for _ in range(20)]
        self.assertTrue(all(v is False for v in values))

    def test_monetary_generator_custom_range(self):
        generator = Monetary(field=self.monetary_field, env=self.env, start=50.0, end=100.0)

        values = [generator.next({'currency_id': self.usd.id}) for _ in range(50)]

        self.assertTrue(all(50.0 <= val <= 100.0 for val in values))

    def test_monetary_generator_values_vary(self):
        generator = Monetary(field=self.monetary_field, env=self.env, start=1.0, end=1000000.0)

        values = [generator.next({'currency_id': self.usd.id}) for _ in range(50)]

        self.assertGreater(len(set(values)), 1)

    def test_monetary_generator_wrong_field_type_raises(self):
        name_field = self.env['test_populate.product']._fields['name']
        with self.assertRaises(TypeError):
            Monetary(field=name_field, env=self.env)

    def test_monetary_convert_to_kwargs(self):
        attrs = {
            'generator': 'scalar.monetary',
            'start': '5.0',
            'end': '250.0',
            'null_ratio': '0.1',
        }
        kwargs = Monetary.convert_to_kwargs(attrs)

        self.assertAlmostEqual(kwargs['start'], 5.0)
        self.assertAlmostEqual(kwargs['end'], 250.0)
        self.assertAlmostEqual(kwargs['null_ratio'], 0.1)
        self.assertIsInstance(kwargs['start'], float)
        self.assertIsInstance(kwargs['end'], float)
