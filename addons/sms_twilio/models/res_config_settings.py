from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sms_provider = fields.Selection(related='company_id.sms_provider', required=True, readonly=False)

    def action_open_sms_twilio_account_manage(self):
        return self.company_id._action_open_sms_twilio_account_manage()
