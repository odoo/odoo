from odoo import models, fields


class SmsTracker(models.Model):
    _inherit = 'sms.tracker'

    sms_twilio_sid = fields.Char(string='Twilio SMS SID', readonly=True)
