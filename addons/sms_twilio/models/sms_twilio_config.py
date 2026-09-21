from odoo import fields, models


class SmsTwilioConfig(models.Model):
    _name = "sms_twilio.config"
    _description = "A company's sms twilio configuration"
    _inherit = ["mixin.company.config"]

    sms_provider = fields.Selection(
        selection=[
            ("iap", "Send via Odoo"),
            ("twilio", "Send via Twilio"),
        ],
        string="SMS Provider",
        default="iap",
    )
    sms_twilio_account_sid = fields.Char(
        string="Account SID",
        groups="base.group_system",
    )
