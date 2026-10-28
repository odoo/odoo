# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_tw_edi_ecpay = fields.Boolean(string="Taiwan eGUI (ECPay)")

    def action_l10n_tw_activate_edi_ecpay(self):
        module = self.env['ir.module.module']._get('l10n_tw_edi_ecpay')
        if module:
            self._install_modules(module)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
