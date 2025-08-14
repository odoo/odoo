# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCheckoutSteps(WebsiteSaleCommon):

    def test_get_existing_specific_extra_step(self):
        specific_extra_step = self.website._get_checkout_step('/shop/extra_info')
        generic_extra_step = self.env.ref('website_sale.checkout_step_extra')
        self.assertNotEqual(specific_extra_step, generic_extra_step)
        self.assertEqual(specific_extra_step.website_id, self.website)

    def test_translate_checkout_steps(self):
        """Verify that loading languages correctly translates website-specific steps."""
        CheckoutStep = self.env['website.checkout.step']
        IrModuleModule = self.env['ir.module.module']

        if self.env['website'].search_count([]) == 1:
            self.env['website'].create({'name': "My Website 2"})

        default_payment_step = self.env.ref('website_sale.checkout_step_payment')
        default_payment_step_FR = default_payment_step.with_context(lang='fr_FR')
        website_1_step_FR, website_2_step_FR = CheckoutStep.with_context(lang='fr_FR').search([
            ('website_id', '!=', False),
            ('step_href', '=', default_payment_step.step_href),
        ], limit=2)

        # Activate French
        if not (lang_fr := self.env.ref('base.lang_fr')).active:
            lang_fr.active = True
        for fname, field in CheckoutStep._fields.items():
            if field.translate and default_payment_step[fname]:
                default_payment_step_FR[fname] = f"{default_payment_step[fname]} (FR)"

        # Have a different translation for a specific website
        website_1_step_FR.name = "Pay in French"

        # Load translations without overwrite
        IrModuleModule._load_module_terms(['website_sale'], ['fr_FR'])
        CheckoutStep.invalidate_model(['name'])
        self.assertEqual(
            website_1_step_FR.name, "Pay in French",
            "Loading translations without overwrite should keep existing translation",
        )
        self.assertIn(
            website_2_step_FR.name,
            ("Payment (FR)", "Paiement"),  # "Paiement" in case translation was already loaded
            "Loading translations should add missing term from default step",
        )

        # Load translations with overwrite
        IrModuleModule._load_module_terms(['website_sale'], ['fr_FR'], overwrite=True)
        CheckoutStep.invalidate_model(['name'])
        self.assertEqual(
            website_1_step_FR.name, "Payment (FR)",
            "Loading translations with overwrite should update existing term from template",
        )

        # Ensure all translatable fields were updated
        for fname, field in CheckoutStep._fields.items():
            if field.translate:
                self.assertEqual(website_1_step_FR[fname], default_payment_step_FR[fname])
                self.assertEqual(website_2_step_FR[fname], default_payment_step_FR[fname])
