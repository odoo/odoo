from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_onboarding_action_data(self):
        # EXTENDS 'account'
        self.ensure_one()
        edi_module = self.env['ir.module.module']._get('l10n_pk_edi')
        if self.country_code != 'PK' or not edi_module:
            return super()._get_onboarding_action_data()
        if edi_module.state != 'installed':
            # A server action, so the module is installed on click rather than on dashboard render.
            return {
                'title': self.env._("Activate E-Invoicing"),
                'action': self.env.ref('l10n_pk.action_l10n_pk_edi_activate')._get_action_dict(),
            }
        return {
            'title': self.env._("E-Invoicing Settings"),
            'action': self.env.ref('account.action_account_config')._get_action_dict(),
        }
