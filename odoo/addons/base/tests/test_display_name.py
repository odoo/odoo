import contextlib

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


IGNORE_MODEL_NAMES = {
    'ir.attachment',
    'test_new_api.attachment',
    'payment.link.wizard',
    'account.multicurrency.revaluation.wizard',
    'account_followup.manual_reminder',
}

IGNORE_COMPUTED_FIELDS = {
    'account.payment.register.payment_token_id',  # must be computed within a specific environment
}

@tagged('-at_install', 'post_install')
class TestEveryModel(TransactionCase):

    def test_display_name_new_record(self):
        for model_name in self.registry:
            model = self.env[model_name]
            if model._abstract or not model._auto or model_name in IGNORE_MODEL_NAMES:
                continue

            with self.subTest(
                msg="`_compute_display_name` doesn't work with new record (first onchange call).",
                model=model_name,
            ):
                # Check that the first onchange with display_name works on every models
                # OR it will fail anyway when people will use click on New
                fields_used = model._fields['display_name'].get_depends(model)[0]
                fields_used = [f.split('.', 1)[0] for f in fields_used]
                fields_spec = dict.fromkeys(fields_used + ['display_name'], {})
                with contextlib.suppress(UserError):
                    model.onchange({}, [], fields_spec)

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
