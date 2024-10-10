
from odoo import fields, models


class SMSPartner(models.Model):
    _description = 'SMS: Test model that allows testing SMS features'
    _name = 'sms.test.partner'
    _inherit = 'mail.thread'
    partner_id = fields.Many2one('res.partner')
