# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import logging

from odoo import models, fields, _
from odoo.exceptions import RedirectWarning

from werkzeug.urls import url_encode, url_join
from datetime import timedelta

_logger = logging.getLogger(__name__)


class EventTrackLiveAccount(models.Model):
    _name = "event.track.live.account"
    _description = "Event Track Live Account for YouTube Integration"

    name = fields.Char('Name', required=True)
    image = fields.Image("Image", max_width=128, max_height=128, readonly=True)
    youtube_channel_id = fields.Char('YouTube Channel ID', readonly=True,
        help="YouTube Channel ID provided by the YouTube API, this should never be set manually.")
    youtube_access_token = fields.Char('Google Access Token', readonly=True,
        help="Access token provided by the YouTube API, this should never be set manually.")
    youtube_refresh_token = fields.Char('Google Refresh Token', readonly=True,
        help="Refresh token provided by the YouTube API, this should never be set manually.")
    youtube_token_expiration_date = fields.Datetime('Token Expiration Date', readonly=True,
        help="Expiration date of the access token provided by the YouTube API.")
    youtube_upload_playlist_id = fields.Char('YouTube Upload Playlist ID', readonly=True,
         help="Uploads playlist ID provided by the YouTube API.")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    is_connected = fields.Boolean('Connected to YouTube', readonly=True)

    def add_youtube_account(self):
        """Redirect to the Google OAuth URL to add a new YouTube account."""
        youtube_oauth_client_id = self.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_id')
        youtube_oauth_client_secret = self.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_secret')

        if youtube_oauth_client_id and youtube_oauth_client_secret:
            base_url = self.get_base_url()
            redirect_uri = url_join(base_url, "event_track_youtube/callback")
            params = {
                'client_id': youtube_oauth_client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': ' '.join([
                    'https://www.googleapis.com/auth/youtube.force-ssl',
                    'https://www.googleapis.com/auth/youtube.upload'
                ]),
                'access_type': 'offline',
                'prompt': 'consent',
            }
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + url_encode(params)

            _logger.info("Redirecting to YouTube OAuth URL: %s", auth_url)

            return {
                'type': 'ir.actions.act_url',
                'url': auth_url,
                'target': 'self',
            }

        else:
            msg = _("No YouTube configuration found. Configure your YouTube OAuth credentials in the settings.")
            redirect_action = self.env.ref('event.action_event_configuration')
            raise RedirectWarning(msg, redirect_action.id, _('Configure'))

    def _refresh_youtube_token(self):
        """
        YouTube uses access tokens for API authentication, which have a short lifespan.
        This method retrieves a new access token using the refresh token when the current
        access token expires.
        """

        config = self.env['ir.config_parameter'].sudo()
        youtube_oauth_client_id = config.get_param('event.youtube_oauth_client_id')
        youtube_oauth_client_secret = config.get_param('event.youtube_oauth_client_secret')

        for account in self:
            if not account.youtube_token_expiration_date or account.youtube_token_expiration_date > fields.Datetime.now():
                continue

            if youtube_oauth_client_id and youtube_oauth_client_secret:
                token_refresh_response = requests.post('https://oauth2.googleapis.com/token',
                    data={
                        'client_id': youtube_oauth_client_id,
                        'client_secret': youtube_oauth_client_secret,
                        'grant_type': 'refresh_token',
                        'refresh_token': account.youtube_refresh_token,
                    },
                    timeout=5,
                ).json()

                if token_refresh_response.get('error'):
                    _logger.warning("YouTube account is disconnected. Reason: %s",
                            token_refresh_response or "Not provided",
                            stack_info=True)
                    account.is_connected = False
                else:
                    account.sudo().write({
                        'youtube_access_token': token_refresh_response['access_token'],
                        'youtube_token_expiration_date': fields.Datetime.now() + timedelta(
                            seconds=token_refresh_response.get('expires_in', 0)),
                        'is_connected': True
                    })
