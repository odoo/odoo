from odoo import fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    failure_type = fields.Selection(
        selection_add=[
            ('sms_twilio_authentication', 'Twilio Authentication Error')
        ],
        ondelete={'sms_twilio_authentication': 'cascade'},
    )
