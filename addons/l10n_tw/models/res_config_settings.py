# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_tw_edi_ecpay = fields.Boolean(string="Taiwan eGUI (ECPay)")

    def action_l10n_tw_activate_edi_ecpay(self):
        """ Install the ECPay e-invoicing module and reload the settings page to show its settings. """
        # _get() returns a sudo record: drop it so button_immediate_install checks the user is an admin
        module = self.env['ir.module.module']._get('l10n_tw_edi_ecpay').sudo(False)
        if module:
            self._install_modules(module)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
