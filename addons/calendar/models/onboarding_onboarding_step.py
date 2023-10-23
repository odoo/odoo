# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_view_start_calendar_sync(self):
        self.env['onboarding.onboarding.step'].action_validate_step('calendar.onboarding_onboarding_step_setup_calendar_integration')
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_view_start_calendar_sync")
        return action
