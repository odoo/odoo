from odoo.fields import Domain
from odoo.tests import TransactionCase, case

from odoo.addons.populate.utils.orm import (
    DynamicDomain,
    ValueTarget,
    drop_pending_update,
)


class TestValueTarget(case.TestCase):

    def test_generated_value_creation(self):
        value = ValueTarget('test_populate.product', 'test_value')
        self.assertEqual(value.model_name, 'test_populate.product')
        self.assertEqual(value.name, 'test_value')
        self.assertEqual(value.type, 'value')
        self.assertFalse(value.required)

    def test_generated_value_str(self):
        value = ValueTarget('test_populate.product', 'test_value')
        self.assertEqual(str(value), 'test_populate.product.test_value')

    def test_generated_value_repr(self):
        value = ValueTarget('test_populate.product', 'test_value')
        self.assertEqual(repr(value), "ValueTarget('test_populate.product', 'test_value')")


class TestDropPendingUpdate(TransactionCase):

    def test_drop_pending_update_with_dirty_fields(self):
        product = self.env['test_populate.product'].create({
            'name': 'Test Product',
            'price': 100.0,
        })

        product.name = 'Modified Product'

        name_field = self.env['test_populate.product']._fields['name']

        self.assertTrue(self.env.transaction.field_dirty[name_field])

        drop_pending_update(self.env, ['name'])

        self.assertFalse(self.env.transaction.field_dirty[name_field])

    def test_drop_pending_update_only_specified_fields(self):
        product = self.env['test_populate.product'].create({
            'name': 'Test Product',
            'price': 100.0,
        })

        product.name = 'Modified Product'
        product.price = 420

        name_field = self.env['test_populate.product']._fields['name']
        price_field = self.env['test_populate.product']._fields['price']

        self.assertTrue(self.env.transaction.field_dirty[name_field])
        self.assertTrue(self.env.transaction.field_dirty[price_field])

        drop_pending_update(self.env, ['name'])

        self.assertFalse(self.env.transaction.field_dirty[name_field])
        self.assertTrue(self.env.transaction.field_dirty[price_field])


class TestDynamicDomain(case.TestCase):

    def test_static_domain_returns_domain_instance(self):
        result = DynamicDomain("[('country_code', '=', 'US')]")
        self.assertIsInstance(result, Domain)

    def test_dynamic_domain_returns_dynamic_domain_instance(self):
        result = DynamicDomain("[('company_id', '=', company_id)]")
        self.assertIsInstance(result, DynamicDomain)

    def test_dynamic_fields_detected(self):
        result = DynamicDomain("[('company_id', '=', company_id)]")
        self.assertListEqual(result.dynamic_fields, ['company_id'])

    def test_multiple_dynamic_fields_detected(self):
        result = DynamicDomain("[('company_id', '=', company_id), ('country_code', '=', country_code)]")
        self.assertSetEqual(set(result.dynamic_fields), {'company_id', 'country_code'})

    def test_call_resolves_domain(self):
        d = DynamicDomain("[('company_id', '=', company_id)]")
        resolved = d(company_id=42)
        self.assertEqual(resolved, Domain('company_id', '=', 42))

    def test_call_resolves_multiple_fields(self):
        d = DynamicDomain("[('company_id', '=', company_id), ('country_code', '=', country_code)]")
        resolved = d(company_id=7, country_code='FR')
        self.assertEqual(resolved, Domain([('company_id', '=', 7), ('country_code', '=', 'FR')]))

    def test_resolver_rejects_unsafe_kwargs(self):
        d = DynamicDomain("[('company_id', '=', company_id)]")
        with self.assertRaises(TypeError):
            d(company_id=object())

    def test_empty_domain_string_returns_domain(self):
        result = DynamicDomain("[]")
        self.assertIsInstance(result, Domain)
