# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    # Invoice Onboarding
    @api.model
    def action_close_panel_account_invoice(self):
        self.action_close_panel('account.onboarding_onboarding_account_invoice')

    def _prepare_rendering_values(self):
        """Compute existence of invoices for company."""
        self.ensure_one()
        if self == self.env.ref('account.onboarding_onboarding_account_invoice', raise_if_not_found=False):
            step = self.env.ref('account.onboarding_onboarding_step_create_invoice', raise_if_not_found=False)
            if step and step.current_step_state == 'not_done':
                if self.env['account.move'].search_count(
                    [('company_id', '=', self.env.company.id), ('move_type', '=', 'out_invoice')], limit=1
                ):
                    step.action_set_just_done()
        return super()._prepare_rendering_values()

    # Dashboard Onboarding
    @api.model
    def action_close_panel_account_dashboard(self):
        self.action_close_panel('account.onboarding_onboarding_account_dashboard')
