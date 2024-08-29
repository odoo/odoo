# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import onboarding

from odoo import api, models


class OnboardingOnboardingStep(models.Model, onboarding.OnboardingOnboardingStep):

    @api.model
    def action_validate_step_payment_provider(self):
        """ Override of `onboarding` to validate other steps as well. """
        return self.action_validate_step('payment.onboarding_onboarding_step_payment_provider')
