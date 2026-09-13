from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sms_provider = fields.Selection(
        related="company_id.sms_provider",
        readonly=False,
        required=True,
    )

    def action_view_sms_twilio_account_manage(self):
        return self.company_id._action_view_sms_twilio_account_manage()
