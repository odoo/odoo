# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged

from odoo.addons.sale_management.tests.common import SaleManagementCommon


@tagged('-at_install', 'post_install')
class TestDynamicFieldsWizard(SaleManagementCommon):

    def test_wizard_from_quotation_template(self):
        action = self.empty_order_template.action_open_dynamic_fields_wizard()

        wizard_with_document_context = self.env[action['res_model']].with_context(
            active_model=self.empty_order_template._name,
            active_id=self.empty_order_template.id,
        )
        wizard_form = Form(wizard_with_document_context)
        wizard = wizard_form.save()

        wizard.save_configuration()

    def test_wizard_from_settings(self):
        wizard_with_settings_context = self.env['sale.pdf.quote.builder.dynamic.fields.wizard'].with_context(
            active_model='res.config.settings',
            active_id=None,
        )
        wizard_form = Form(wizard_with_settings_context)
        wizard = wizard_form.save()

        wizard.save_configuration()

    def test_wizard_from_product_document(self):
        demo_document = self.env['product.document'].search([], limit=1)
        if not demo_document:
            self.skipTest('No demo document found, skipping test')

        action = demo_document.action_open_dynamic_fields_wizard()

        wizard_with_document_context = self.env[action['res_model']].with_context(
            active_model=demo_document._name,
            active_id=demo_document.id,
        )
        wizard_form = Form(wizard_with_document_context)
        wizard = wizard_form.save()

        wizard.save_configuration()

    # TODO EDM assertRaises ValidationError when invalid values on lines
