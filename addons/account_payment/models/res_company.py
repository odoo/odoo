# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def action_open_payment_onboarding(self):
        self.env.company.payment_onboarding_payment_method = 'stripe'
        menu = self.env.ref('account_payment.payment_provider_menu', raise_if_not_found=False)
        menu_id = menu and menu.id
        return self._run_payment_onboarding_step(menu_id)

    def get_account_invoice_onboarding_steps_states_names(self):
        """ Override of `account` to add the state of the payment onboarding step. """
        steps = super().get_account_invoice_onboarding_steps_states_names()
        return steps + ['payment_provider_onboarding_state']
