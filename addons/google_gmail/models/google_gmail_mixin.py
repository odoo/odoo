# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class GoogleGmailMixin(models.AbstractModel):
    _name = 'google.gmail.mixin'

    _description = 'Google Gmail Mixin'
    _email_field = None
    _server_type_field = None

    _SERVICE_SCOPE = 'https://mail.google.com/'
    _DEFAULT_GMAIL_IAP_ENDPOINT = 'https://gmail.api.odoo.com'

    google_gmail_token_id = fields.Many2one(
        'google.gmail.token',
        'Gmail Token',
        compute='_compute_google_gmail_token_id',
    )
    google_gmail_uri = fields.Char(
        compute='_compute_google_gmail_uri',
        string='URI',
        help='The URL to generate the authorization code from Google',
        groups='base.group_system',
    )

    def open_google_gmail_uri(self):
        """Open the URL to accept the Gmail permission.

        This is done with an action, so we can force the user the save the form.
        We need him to save the form so the current mail server record exist in DB, and
        we can include the record ID in the URL.
        """
        self.ensure_one()

        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only the administrator can link a Gmail mail server.'))

        email = tools.email_normalize(self[self._email_field])
        if not email:
            raise UserError(_('Please enter a valid email address.'))

        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        is_configured = google_gmail_client_id and google_gmail_client_secret
        if not is_configured:  # use IAP (see '/google_gmail/iap_confirm')
            gmail_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
                'mail.gmail_iap_endpoint',
                self._DEFAULT_GMAIL_IAP_ENDPOINT,
            )
            db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

            # final callback URL that will receive the token from IAP
            callback_url = url_join(self.get_base_url(), '/google_gmail/iap_confirm')
            callback_url += '?' + url_encode({
                'model': self._name,
                'rec_id': self.id,
                'csrf_token': self._get_gmail_csrf_token(),
                'email': email,
            })

            try:
                response = requests.get(
                    url_join(gmail_iap_endpoint, '/iap/mail_oauth/gmail'),
                    params={'db_uuid': db_uuid, 'email': email, 'callback_url': callback_url},
                    timeout=3)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                _logger.error('Can not contact IAP: %s.', e)
                raise UserError(_('Can not contact IAP.'))

            response = response.json()
            if 'error' in response:
                raise UserError(_('An error occurred: %s.', response['error']))

            # URL on IAP that will redirect to Gmail login page
            google_gmail_uri = response['url']

        else:
            google_gmail_uri = self.google_gmail_uri

        if not google_gmail_uri:
            raise UserError(_('Please configure your Gmail credentials.'))

        return {
            'type': 'ir.actions.act_url',
            'url': google_gmail_uri,
        }

    @api.depends(lambda self: (self._email_field, self._server_type_field))
    def _compute_google_gmail_uri(self):
        gmail_servers, normal_servers = self._split_gmail_servers()
        normal_servers.google_gmail_uri = False

        Config = self.env['ir.config_parameter'].sudo()
        google_gmail_client_id = Config.get_param('google_gmail_client_id')
        google_gmail_client_secret = Config.get_param('google_gmail_client_secret')
        is_configured = google_gmail_client_id and google_gmail_client_secret
        redirect_uri = url_join(self.get_base_url(), '/google_gmail/confirm')

        for record in gmail_servers:
            email = tools.email_normalize(record[self._email_field])
            if not email or not is_configured:
                record.google_gmail_uri = False
                continue

            record.google_gmail_uri = 'https://accounts.google.com/o/oauth2/v2/auth?%s' % url_encode({
                'client_id': google_gmail_client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': self._SERVICE_SCOPE,
                # access_type and prompt needed to get a refresh token
                'access_type': 'offline',
                'prompt': 'consent',
                'state': json.dumps(
                    {
                        'model': record._name,
                        'id': record.id or False,
                        'email': email,
                        'csrf_token': record._get_gmail_csrf_token(),
                    }
                ),
            })

    @api.depends(lambda self: (self._email_field, self._server_type_field))
    def _compute_google_gmail_token_id(self):
        gmail_servers, normal_servers = self._split_gmail_servers()
        normal_servers.google_gmail_token_id = False

        all_emails = list(map(tools.email_normalize, gmail_servers.mapped(self._email_field)))
        tokens = self.env['google.gmail.token'].search([('email', 'in', all_emails)])
        tokens_per_email = {token.email: token for token in tokens}
        for record, email in zip(gmail_servers, all_emails):
            record.google_gmail_token_id = tokens_per_email.get(email, False)

    def _get_gmail_csrf_token(self):
        """Generate a CSRF token that will be verified in `google_gmail_callback`.

        This will prevent a malicious person to make an admin user disconnect the mail servers.
        """
        self.ensure_one()
        _logger.info('Google Gmail: generate CSRF token for %s #%i', self._name, self.id)
        return tools.misc.hmac(
            env=self.env(su=True),
            scope='google_gmail_oauth',
            message=(self._name, self.id, tools.email_normalize(self[self._email_field])),
        )

    def _split_gmail_servers(self):
        gmail_servers = self.filtered(lambda server: server[self._server_type_field] == 'gmail')
        return gmail_servers, self - gmail_servers
