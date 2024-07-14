# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    firebase_enable_push_notifications = fields.Boolean('Enable Web Push Notifications')
    firebase_use_own_account = fields.Boolean('Use your own Firebase account')
    firebase_project_id = fields.Char('Firebase Project ID')
    firebase_web_api_key = fields.Char('Firebase Web API Key')
    firebase_push_certificate_key = fields.Char('Firebase Push Certificate Key')
    firebase_sender_id = fields.Char('Firebase Sender ID')
    firebase_admin_key_file = fields.Binary('Firebase Admin Key File', groups="social.group_social_manager")

    notification_request_title = fields.Char('Notification Request Title')
    notification_request_body = fields.Text('Notification Request Text')
    notification_request_delay = fields.Integer('Notification Request Delay (seconds)', default=3)
    notification_request_icon = fields.Binary("Notification Request Icon")

    @api.model_create_multi
    def create(self, vals_list):
        """ Overridden to automatically create push accounts for every created website """
        websites = super(Website, self).create(vals_list)
        websites._create_push_accounts()

        return websites

    def _create_push_accounts(self):
        social_media_push_notifications = self.env.ref('social_push_notifications.social_media_push_notifications').sudo()

        SocialAccount = self.env['social.account'].sudo()

        existing_accounts = SocialAccount.search([
            ('media_id', '=', social_media_push_notifications.id),
            ('website_id', 'in', self.ids)
        ])

        SocialAccount.create([{
            'name': website.name,
            'media_id': social_media_push_notifications.id,
            'website_id': website.id,
            'has_account_stats': False
        } for website in (self - existing_accounts.mapped('website_id'))])
