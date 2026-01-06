from unittest import skipIf

from odoo.tests import TransactionCase

try:
    from faker import Faker

except ImportError:
    Faker = None

if Faker:
    from odoo.addons.populate.generators import Generator, fake


@skipIf(not Faker, "Faker library not installed.")
class TestFakeGeneratorMethods(TransactionCase):

    def setUp(self):
        super().setUp()
        self.faker = Faker()

    def test_is_allowed_whitelisted_provider(self):
        # Known methods from the 'person' provider which is whitelisted
        self.assertTrue(fake.is_allowed(self.faker, 'name'))
        self.assertTrue(fake.is_allowed(self.faker, 'email'))
        self.assertTrue(fake.is_allowed(self.faker, 'company'))

    def test_is_allowed_private_methods_rejected(self):
        self.assertFalse(fake.is_allowed(self.faker, '_some_private_method'))

    def test_is_allowed_blacklisted_methods_rejected(self):
        for method_name in fake.METHODS_BLACKLIST:
            if hasattr(self.faker, method_name):
                self.assertFalse(fake.is_allowed(self.faker, method_name))

    def test_is_allowed_nonexistent_method(self):
        self.assertFalse(fake.is_allowed(self.faker, 'definitely_not_a_real_method_xyz'))

    def test_known_methods_populated(self):
        self.assertGreater(len(fake.KNOWN_METHODS), 0)

        some_expected_methods = ['name', 'email', 'address', 'company']
        for method in some_expected_methods:
            if hasattr(self.faker, method):
                self.assertIn(method, fake.KNOWN_METHODS)

    def test_create_generator_class(self):
        # `create` should've been called when the module loaded,
        # and defining the class should've registered it.
        FakeName = Generator.by_name('fake.name')

        self.assertIsNotNone(FakeName)
        self.assertTrue(issubclass(FakeName, Generator))
        self.assertEqual(FakeName.name, 'fake.name')


@skipIf(not Faker, "Faker library not installed.")
class TestFakeGenerators(TransactionCase):

    def setUp(self):
        self.name_field = self.env['test_populate.customer']._fields['name']
        self.email_field = self.env['test_populate.customer']._fields['email']
        self.notes_field = self.env['test_populate.customer']._fields['notes']

    def test_fake_generator_with_locale(self):
        FakeName = Generator.by_name('fake.name')
        generator = FakeName(field=self.name_field, env=self.env, locale='fr_FR')

        value = generator.next({})
        self.assertIsInstance(value, str)
        self.assertGreater(len(value), 0)

    def test_fake_generator_null_ratio(self):
        test_field = self.notes_field
        assert not test_field.required, "Cannot test null_ratio on a required field (raises ValueError)"
        FakeName = Generator.by_name('fake.words')
        generator = FakeName(field=test_field, env=self.env, null_ratio=0.9)

        values = [generator.next({}) for _ in range(100)]
        false_count = values.count(False)

        self.assertGreater(false_count, 70)

    def test_fake_generator_no_null_with_zero_frac(self):
        FakeName = Generator.by_name('fake.name')
        generator = FakeName(field=self.name_field, env=self.env, null_ratio=0)

        values = [generator.next({}) for _ in range(50)]

        self.assertNotIn(False, values)

    def test_fake_generator_unique(self):
        FakeEmail = Generator.by_name('fake.email')
        generator = FakeEmail(field=self.email_field, env=self.env, unique=True)

        values = [generator.next({}) for _ in range(50)]

        self.assertEqual(len(values), len(set(values)))

    def test_fake_generator_convert_to_kwargs_basic(self):
        FakeName = Generator.by_name('fake.name')
        attrs = {
            'generator': 'fake.name',
            'locale': 'de_DE',
            'null_ratio': '0.2',
        }

        kwargs = FakeName.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['locale'], 'de_DE')
        self.assertEqual(kwargs['null_ratio'], 0.2)

    def test_fake_generator_convert_to_kwargs_conversion_bool(self):
        FakeName = Generator.by_name('fake.name')

        for true_val in ['true', 'True', 'TRUE', '1']:
            attrs = {'some_param': true_val}
            kwargs = FakeName.convert_to_kwargs(attrs)
            self.assertIs(kwargs['some_param'], True)

        for false_val in ['false', 'False', 'FALSE', '0']:
            attrs = {'some_param': false_val}
            kwargs = FakeName.convert_to_kwargs(attrs)
            self.assertIs(kwargs['some_param'], False)

    def test_fake_generator_convert_to_kwargs_conversion_int(self):
        FakeName = Generator.by_name('fake.name')
        attrs = {'some_param': '42', 'negative': '-10'}

        kwargs = FakeName.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['some_param'], 42)
        self.assertEqual(kwargs['negative'], -10)

    def test_fake_generator_convert_to_kwargs_conversion_float(self):
        FakeName = Generator.by_name('fake.name')
        attrs = {
            'decimal': '3.14',
            'negative': '-2.5',
            'scientific': '1e-5',
        }

        kwargs = FakeName.convert_to_kwargs(attrs)

        self.assertAlmostEqual(kwargs['decimal'], 3.14)
        self.assertAlmostEqual(kwargs['negative'], -2.5)
        self.assertAlmostEqual(kwargs['scientific'], 1e-5)

    def test_fake_generator_convert_to_kwargs_conversion_list(self):
        FakeName = Generator.by_name('fake.name')
        attrs = {
            'elements': '[Mr, Mrs, Ms]',
            'numbers': '(1, 2, 3)',
        }

        kwargs = FakeName.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['elements'], ['Mr', 'Mrs', 'Ms'])
        self.assertEqual(kwargs['numbers'], [1, 2, 3])

    def test_fake_generator_convert_to_kwargs_conversion_none(self):
        FakeName = Generator.by_name('fake.name')

        for none_val in ['none', 'None', 'null', 'nil', '']:
            attrs = {'some_param': none_val}
            kwargs = FakeName.convert_to_kwargs(attrs)
            self.assertIsNone(kwargs['some_param'])

    def test_fake_generator_invalid_params_raises(self):
        FakeName = Generator.by_name('fake.name')

        with self.assertRaises(ValueError) as cm:
            FakeName(
                field=self.name_field,
                env=self.env,
                # `values` is a params for the generic generator,
                # but isn't allowed for 'fake' generators
                values='[1,2,3]',
            )

        self.assertIn('Invalid parameters', str(cm.exception))

    def test_fake_generator_with_method_args(self):
        # Some Faker methods accept arguments (e.g., numerify, bothify)
        # Test with a method that accepts kwargs
        method_name = 'numerify'
        try:
            FakeNumerify = Generator.by_name(f'fake.{method_name}')
            if FakeNumerify:
                generator = FakeNumerify(
                    field=self.name_field,
                    env=self.env,
                    text='ID-###',
                )
                value = generator.next({})
                self.assertRegex(value, r'ID-\d{3}')
        except (KeyError, AttributeError):
            # Method might not be available in all Faker versions (or anymore)
            self.fail(f"'{method_name}' doesn't exists. Test need to be updated.")
