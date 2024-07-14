# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
from werkzeug.urls import url_join

from odoo import _, api, fields, models, tools
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests
except ImportError:
    service_account = None


class SocialAccountPushNotifications(models.Model):
    _inherit = 'social.account'

    website_id = fields.Many2one('website', string="Website",
                                 help="This firebase configuration will only be used for the specified website", ondelete='cascade')
    firebase_use_own_account = fields.Boolean('Use your own Firebase account', related='website_id.firebase_use_own_account')
    firebase_project_id = fields.Char('Firebase Project ID', related='website_id.firebase_project_id')
    firebase_web_api_key = fields.Char('Firebase Web API Key', related='website_id.firebase_web_api_key')
    firebase_push_certificate_key = fields.Char('Firebase Push Certificate Key', related='website_id.firebase_push_certificate_key')
    firebase_sender_id = fields.Char('Firebase Sender ID', related='website_id.firebase_sender_id')
    firebase_admin_key_file = fields.Binary('Firebase Admin Key File', related='website_id.firebase_admin_key_file')

    notification_request_title = fields.Char('Notification Request Title', related='website_id.notification_request_title')
    notification_request_body = fields.Text('Notification Request Text', related='website_id.notification_request_body')
    notification_request_delay = fields.Integer('Notification Request Delay (seconds)', related='website_id.notification_request_delay')
    notification_request_icon = fields.Binary("Notification Request Icon", related='website_id.notification_request_icon')

    _sql_constraints = [('website_unique', 'unique(website_id)', 'There is already a configuration for this website.')]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_push_notification_account(self):
        if not self.env.user.has_group('base.group_system') and any(account.website_id for account in self):
            raise UserError(_("You can't delete a Push Notification account."))

    def _firebase_send_message(self, data, visitors):
        visitors = visitors.filtered(lambda visitor: visitor.push_subscription_ids)
        if self.firebase_use_own_account:
            self._firebase_send_message_from_configuration(data, visitors)
        else:
            self._firebase_send_message_from_iap(data, visitors)

    def _firebase_send_message_from_configuration(self, data, visitors):
        """ Sends messages one by one using the firebase REST API.
           It requires a bearer token for authentication that we obtain using the google_auth library.
           Returns he matched website.visitors (search_read records). """

        if not visitors:
            return [], []

        if not self.firebase_admin_key_file:
            raise UserError(_("Firebase Admin Key File is missing from the configuration."))

        tokens = visitors.mapped('push_subscription_ids.push_token')
        if service_account:
            firebase_data = json.loads(
                base64.b64decode(self.firebase_admin_key_file).decode())
            firebase_credentials = service_account.Credentials.from_service_account_info(
                firebase_data,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            firebase_credentials.refresh(google_requests.Request())
            auth_token = firebase_credentials.token

            for token in tokens:
                requests.post(
                    f'https://fcm.googleapis.com/v1/projects/{firebase_data["project_id"]}/messages:send',
                    json={
                        'message': {
                            'data': data,
                            'token': token
                        }
                    },
                    headers={'authorization': f'Bearer {auth_token}'},
                    timeout=5
                )
        else:
            raise UserError(_('You have to install "google_auth>=1.18.0" to be able to send push notifications.'))

        return tokens

    def _firebase_send_message_from_iap(self, data, visitors):
        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )
        batch_size = 100

        tokens = visitors.mapped('push_subscription_ids.push_token')
        data.update({'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')})
        for tokens_batch in tools.split_every(batch_size, tokens, piece_maker=list):
            batch_data = dict(data)
            batch_data['tokens'] = tokens_batch
            iap_tools.iap_jsonrpc(url_join(social_iap_endpoint, '/iap/social_push_notifications/firebase_send_message'), params=batch_data)

        return []
