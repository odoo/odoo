from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _l10n_eg_is_pos_journal(self):
        self.ensure_one()
        if 'pos.config' not in self.env:
            return False
        PosConfig = self.env['pos.config']  # noqa: OLS03001
        return bool(
            PosConfig.sudo()
            .with_context(active_test=False)
            .search_count(
                [
                    '|',
                    ('journal_id', '=', self.id),
                    ('closing_journal_id', '=', self.id),
                ],
                limit=1,
            )
        )

    def _get_onboarding_action_data(self):
        onboarding_data = super()._get_onboarding_action_data()
        if self.country_code != 'EG' or not onboarding_data:
            return onboarding_data

        if self._l10n_eg_is_pos_journal():
            module_name = 'l10n_eg_edi_pos'
            activate_xmlid = 'l10n_eg.action_l10n_eg_edi_pos_activate'
            activate_title = self.env._("Activate E-Receipts")
            settings_xmlid = 'point_of_sale.action_pos_configuration'
            settings_title = self.env._("E-Receipts Settings")
        else:
            module_name = 'l10n_eg_edi_eta'
            activate_xmlid = 'l10n_eg.action_l10n_eg_edi_eta_activate'
            activate_title = self.env._("Activate E-Invoicing")
            settings_xmlid = 'account.action_account_config'
            settings_title = self.env._("E-Invoicing Settings")

        edi_module = self.env['ir.module.module']._get(module_name)
        if not edi_module:
            return onboarding_data
        if edi_module.state != 'installed':
            activate_action = self.env.ref(activate_xmlid, raise_if_not_found=False)
            if not activate_action:
                return onboarding_data
            return {
                'title': activate_title,
                'action': activate_action._get_action_dict(),
            }
        return {
            'title': settings_title,
            'action': self.env.ref(settings_xmlid)._get_action_dict(),
        }
