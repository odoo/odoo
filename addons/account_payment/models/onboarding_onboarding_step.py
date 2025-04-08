# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_payment_provider(self):
        menu = self.env.ref('account_payment.payment_provider_menu', raise_if_not_found=False)
        menu_id = menu.id if menu else None
        return self.env.company._run_payment_onboarding_step(menu_id, 'stripe')

    @api.model
    def action_validate_step_payment_provider(self):
        validation_response = super().action_validate_step_payment_provider()
        self.action_validate_step("account_payment.onboarding_onboarding_step_payment_provider")
        return validation_response
