# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_onboarding_action_data(self):
        # EXTENDS 'account'
        self.ensure_one()
        if self.country_code != 'CN':
            return super()._get_onboarding_action_data()
        if self.company_id.l10n_cn_baiwang_subscription_status == 'authorized':
            title = self.env._("E-Fapiao Settings")
        else:
            title = self.env._("Activate E-Fapiao")
        return {
            'title': title,
            # Registration runs from the settings, where our block sits right
            # below "Initial Setup", so the settings page is the landing spot
            # for every state.
            'action': self.env.ref('account.action_account_config')._get_action_dict(),
        }
