# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_setup_consolidation(self):
        return self.env['consolidation.chart'].setting_consolidation_action()

    @api.model
    def action_open_step_setup_ccoa(self):
        return self.env['consolidation.chart'].setting_consolidated_chart_of_accounts_action()

    @api.model
    def action_open_step_create_consolidation_period(self):
        return self.env['consolidation.chart'].setting_create_period_action()
