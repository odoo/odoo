from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

IGNORE_COMPUTED_FIELDS = {
    'account.payment.register.payment_token_id',  # must be computed within a specific environment
}


@tagged('-at_install', 'post_install')
class TestEveryModel(TransactionCase):
    def test_computed_fields_without_dependencies(self):
        for model in self.env.values():
            if model._abstract or not model._auto:
                continue

            for field in model._fields.values():
                if str(field) in IGNORE_COMPUTED_FIELDS:
                    continue
                if not field.compute or self.registry.field_depends[field]:
                    continue
                # ignore if the field does not appear in a form view
                domain = [
                    ('model', '=', model._name),
                    ('type', '=', 'form'),
                    ('arch_db', 'like', field.name),
                ]
                if not self.env['ir.ui.view'].search_count(domain, limit=1):
                    continue

                with self.subTest(msg=f"Compute method of {field} should work on new record."):
                    with self.env.cr.savepoint():
                        model.new()[field.name]

    def test_currency_field_has_sql(self):
        for model in self.env.values():
            if model._abstract or model.is_transient() or model._name.startswith('test_'):
                # skip abstract models, transient models (usually we don't group there) and test models
                continue
            currencies = {
                field.currency_field
                for field in model._fields.values()
                if field.type == 'monetary'
                and field.currency_field
                and (field.store or field.compute_sql)
            }
            if 'currency_id' in model._fields:
                currencies.add('currency_id')  # always add the default currency field
            for currency_name in currencies:
                currency_field = model._fields[currency_name]
                with self.subTest(msg=f"Currency {currency_field} must have a SQL representation."):
                    if not (currency_field.store or currency_field.compute_sql):
                        self.fail("Field with SQL representation uses currency without SQL representation")


class TestOverrides(TransactionCase):

    # Ensure all main ORM methods behavior works fine even on empty recordset
    # and that their returned value(s) follow the expected format.

    def test_creates(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.create([]), model_env.browse(),
                "Invalid create return value for model %s" % model_env._name)

    def test_writes(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            try:
                # with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.browse().write({}), True,
                    "Invalid write return value for model %s" % model_env._name)
            except UserError:
                # skip models that should never be modified
                continue

    def test_default_get(self):
        for model_env in self.env.values():
            if model_env._transient:
                continue
            try:
                # with self.assertQueryCount(1):  # allow one query for the call to get_model_defaults.
                self.assertEqual(
                    model_env.browse().default_get([]), {},
                    "Invalid default_get return value for model %s" % model_env._name)
            except UserError:
                # skip "You must be logged in a Belgian company to use this feature" errors
                continue

    def test_unlink(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.browse().unlink(), True,
                "Invalid unlink return value for model %s" % model_env._name)
