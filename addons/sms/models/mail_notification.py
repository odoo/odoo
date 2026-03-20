# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'cascade'})
    sms_id_int = fields.Integer('SMS ID', index='btree_not_null')
    # Used to give links on form view without foreign key. In most cases, you'd want to use sms_id_int or sms_tracker_ids.sms_uuid.
    sms_id = fields.Many2one('sms.sms', string='SMS', store=False, compute='_compute_sms_id')
    sms_tracker_ids = fields.One2many('sms.tracker', 'mail_notification_id', string="SMS Trackers")
    sms_number = fields.Char('SMS Number', groups='base.group_user')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_country_not_supported', 'Country Not Supported'),
        ('sms_registration_needed', 'Country-specific Registration Required'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account'),
        # delivery report errors
        ('sms_expired', 'Expired'),
        ('sms_invalid_destination', 'Invalid Destination'),
        ('sms_not_allowed', 'Not Allowed'),
        ('sms_not_delivered', 'Not Delivered'),
        ('sms_rejected', 'Rejected'),
    ])

    @api.depends('sms_id_int', 'notification_type')
    def _compute_sms_id(self):
        self.sms_id = False
        sms_notifications = self.filtered(lambda n: n.notification_type == 'sms' and bool(n.sms_id_int))
        if not sms_notifications:
            return
        existing_sms_ids = self.env['sms.sms'].sudo().search([
            ('id', 'in', sms_notifications.mapped('sms_id_int')), ('to_delete', '!=', True)
        ]).ids
        for sms_notification in sms_notifications.filtered(lambda n: n.sms_id_int in set(existing_sms_ids)):
            sms_notification.sms_id = sms_notification.sms_id_int
