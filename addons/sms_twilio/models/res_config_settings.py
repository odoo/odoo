from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    sms_provider = fields.Selection(related='company_id.sms_provider', required=True, readonly=False)

    def action_sms_twilio_open_manage_connection_wizard(self, wizard=False):
        return self.company_id._action_sms_twilio_open_manage_connection_wizard(wizard)
