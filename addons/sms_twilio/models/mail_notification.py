from odoo import fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    failure_type = fields.Selection(
        selection_add=[
            ('twilio_authentication', 'Authentication Error"'),
            ('twilio_callback', 'Incorrect callback URL'),
            ('twilio_from_missing', 'Missing From Number'),
            ('twilio_from_to', 'From / To identic'),
            ('twilio_wrong_credentials', 'Twilio Wrong Credentials'),
        ],
    )
