# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    firebase_enable_push_notifications = fields.Boolean('Enable Web Push Notifications', readonly=False, related='website_id.firebase_enable_push_notifications')
    firebase_use_own_account = fields.Boolean('Use your own Firebase account', readonly=False, related='website_id.firebase_use_own_account')
    firebase_project_id = fields.Char('Firebase Project ID', readonly=False, related='website_id.firebase_project_id')
    firebase_web_api_key = fields.Char('Firebase Web API Key', readonly=False, related='website_id.firebase_web_api_key')
    firebase_push_certificate_key = fields.Char('Firebase Push Certificate Key', readonly=False, related='website_id.firebase_push_certificate_key')
    firebase_sender_id = fields.Char('Firebase Sender ID', readonly=False, related='website_id.firebase_sender_id')
    firebase_admin_key_file = fields.Binary('Firebase Admin Key File', readonly=False, related='website_id.firebase_admin_key_file')

    notification_request_title = fields.Char('Notification Request Title', readonly=False, related='website_id.notification_request_title')
    notification_request_body = fields.Text('Notification Request Text', readonly=False, related='website_id.notification_request_body')
    notification_request_delay = fields.Integer('Notification Request Delay (seconds)', readonly=False, related='website_id.notification_request_delay')
    notification_request_icon = fields.Binary("Notification Request Icon", readonly=False, related='website_id.notification_request_icon')
