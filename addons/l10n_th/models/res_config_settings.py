# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_th_edi_inet = fields.Boolean(string="Thailand e-Tax Invoice (INET)")

    def action_l10n_th_activate_edi_inet(self):
        module = self.env['ir.module.module']._get('l10n_th_edi_inet')
        if module:
            self._install_modules(module)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
