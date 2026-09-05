from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_open_sms_iap_account(self):
        iap_account = self.env['iap.account'].get('sms')
        return iap_account.action_manage()
