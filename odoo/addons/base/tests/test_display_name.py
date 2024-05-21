import contextlib
from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged, Form


IGNORE_MODEL_NAMES = {
    'account.report.line',  # only used as wizard, and display_name isn't compute in a wizard but Form add display_name automatically
    'chatbot.script.step',  # only used as wizard
    'stock.warehouse',  # avoid warning "Creating a new warehouse will automatically activate the Storage Locations setting"
    'website.visitor',  # Visitors can only be created through the frontend.
    'marketing.activity',  # only used as wizard and always used form marketing.campaign
}


@tagged('-at_install', 'post_install')
class TestEveryModel(TransactionCase):

    def test_form_new_record(self):
        for model_name in self.registry:
            model = self.env[model_name]
            if (
                model._abstract
                or model._transient
                or not model._auto
                or model_name in IGNORE_MODEL_NAMES
            ):
                continue

            default_form_id = self.env['ir.ui.view'].default_view(model_name, 'form')
            if not default_form_id:
                continue

            default_form = self.env['ir.ui.view'].browse(default_form_id)
            view_elem = etree.fromstring(default_form.arch)
            if view_elem.get('create') in ("0", "false"):
                continue

            with self.subTest(
                msg="Create a new record from form view doesn't work (first onchange call).",
                model=model_name,
            ), contextlib.suppress(UserError):
                # Test to open the Form view to check first onchange
                # (including display_name on new records)
                Form(model)
