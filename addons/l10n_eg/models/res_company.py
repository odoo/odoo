from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _l10n_eg_action_activate_edi(self, module_name, settings_action_xmlid):
        """Install the given Egyptian EDI module, then land the user on its settings."""
        module = self.env['ir.module.module']._get(module_name)
        if module.state != 'installed':
            module.button_immediate_install()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': self.env.ref(settings_action_xmlid).id},
        }
