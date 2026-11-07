# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_calendar_onboarding(self):
        self.action_close_panel('calendar.onboarding_onboarding_calendar')

    def _prepare_rendering_values(self):
        """Compute existence of invoices for company."""
        self.ensure_one()
        if self == self.env.ref('calendar.onboarding_onboarding_calendar', raise_if_not_found=False):
            step = self.env.ref('calendar.onboarding_onboarding_step_setup_calendar_integration', raise_if_not_found=False)
            if step and step.current_step_state == 'not_done':
                credentials = self.env['res.users'].check_calendar_credentials()
                if any(credentials[service] for service in credentials):
                    step.action_set_just_done()
        return super()._prepare_rendering_values()
