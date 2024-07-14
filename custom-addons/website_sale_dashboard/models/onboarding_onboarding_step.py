# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_payment_provider_website_sale(self):
        self.env.company.payment_onboarding_payment_method = 'stripe'
        menu_id = self.env.ref('website.menu_website_dashboard').id
        return self.env.company._run_payment_onboarding_step(menu_id)

    @api.model
    def action_validate_step_payment_provider(self):
        validation_response = super().action_validate_step_payment_provider()
        self.action_validate_step("website_sale_dashboard.onboarding_onboarding_step_payment_provider")
        return validation_response
