# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'cascade'})
    sms_id = fields.Many2one('sms.sms', string='SMS', index='btree_not_null', ondelete='set null')
    sms_number = fields.Char('SMS Number')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account')
    ])
