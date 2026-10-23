from odoo import api, models

L10N_EG_EDI_MODULES = {
    'eta': ('l10n_eg_edi_eta', 'account.action_account_config'),
    'pos': ('l10n_eg_edi_pos', 'point_of_sale.action_pos_configuration'),
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _l10n_eg_action_activate_edi(self, edi_type):
        """Install the EDI module of `edi_type` ('eta' or 'pos'), then open its settings."""
        module_name, settings_xmlid = L10N_EG_EDI_MODULES[edi_type]
        module = self.env['ir.module.module']._get(module_name)
        if module and module.state not in {'uninstallable', 'installed'}:
            module.button_immediate_install()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': self.env.ref(settings_xmlid).id},
        }
