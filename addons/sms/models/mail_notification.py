# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class Notification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])
    sms_id = fields.Many2one('sms.sms', string='SMS', index=True, ondelete='set null')
    sms_number = fields.Char('SMS Number')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error')]
    )
