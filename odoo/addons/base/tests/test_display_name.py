import contextlib
from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


IGNORE_MODEL_NAMES_DISPLAY_NAME = {
    'ir.attachment',
    'test_orm.attachment',
    'payment.link.wizard',
    'account.multicurrency.revaluation.wizard',
    'account_followup.manual_reminder',
    'product.fetch.image.wizard',
}

IGNORE_MODEL_NAMES_NEW_FORM = {
    'account.report.line',  # only used as wizard, and display_name isn't compute in a wizard but Form add display_name automatically
    'chatbot.script.step',  # only used as wizard
    'stock.warehouse',  # avoid warning "Creating a new warehouse will automatically activate the Storage Locations setting"
    'website.visitor',  # Visitors can only be created through the frontend.
    'marketing.activity',  # only used as wizard and always used form marketing.campaign
    'crm.stage',  # Avoid warning "Changing the value of 'Is Won Stage' may induce ..."
}

IGNORE_COMPUTED_FIELDS = {
    'account.payment.register.payment_token_id',  # must be computed within a specific environment
}


@tagged('-at_install', 'post_install')
class TestEveryModel(TransactionCase):

    def test_display_name_new_record(self):
        for model_name in self.registry:
            model = self.env[model_name]
            if model._abstract or not model._auto or model_name in IGNORE_MODEL_NAMES_DISPLAY_NAME:
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

    def test_form_new_record(self):
        allowed_models = set(self.env['ir.model.access']._get_allowed_models('create'))
        allowed_models -= IGNORE_MODEL_NAMES_NEW_FORM

        for model_name, model in self.env.items():
            if (
                model._abstract
                or model._transient
                or not model._auto
                or model_name not in allowed_models
            ):
                continue

            default_form_id = self.env['ir.ui.view'].default_view(model_name, 'form')
            if not default_form_id:
                continue

            default_form = self.env['ir.ui.view'].browse(default_form_id)
            if not default_form.arch:
                continue
            view_elem = etree.fromstring(default_form.arch)
            if view_elem.get('create') in ('0', 'false'):
                continue

            with self.subTest(
                msg="Create a new record from form view doesn't work (first onchange call).",
                model=model_name,
            ), contextlib.suppress(UserError):
                # Test to open the Form view to check first onchange
                Form(model)

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
