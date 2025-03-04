# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import base64

from odoo import http, _, fields
from odoo.http import request
from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.osv import expression

from datetime import timedelta
from werkzeug.urls import url_join

class EventTrackLiveController(EventTrackController):

    @http.route('/event_track/get_track_suggestion', type='jsonrpc', auth='public', website=True)
    def get_next_track_suggestion(self, track_id):
        track = self._fetch_track(track_id)
        track_suggestion = track._get_track_suggestions(
            restrict_domain=expression.AND([
                self._get_event_tracks_domain(track.event_id),
                [('youtube_video_url', '!=', False)]
            ]), limit=1)
        if not track_suggestion:
            return False
        track_suggestion_sudo = track_suggestion.sudo()
        track_sudo = track.sudo()
        return self._prepare_track_suggestion_values(track_sudo, track_suggestion_sudo)

    def _prepare_track_suggestion_values(self, track, track_suggestion):
        return {
            'current_track': {
                'name': track.name,
                'website_image_url': track.website_image_url,
            },
            'suggestion': {
                'id': track_suggestion.id,
                'name': track_suggestion.name,
                'speaker_name': track_suggestion.partner_name,
                'website_url': track_suggestion.website_url
            }
        }

    @http.route('/event_track_youtube/callback', type='http', auth='user')
    def event_youtube_account_callback(self, code=None, **kw):
        """
        Handles the YouTube OAuth callback, exchanging the authorization code for access and refresh tokens.

        This endpoint is the target of the YouTube OAuth flow. It receives an authorization 'code'
        from YouTube, which is then used to request access and refresh tokens. These tokens are
        essential for authenticating requests to the YouTube Data API.

        Prerequisites:
        - The Odoo database must be configured with the YouTube OAuth Client ID and Client Secret
        - The user accessing this endpoint must have the 'event.group_event_manager' group.

        """

        if not request.env.user.has_group('event.group_event_manager'):
            return request.render('website_event_track_live.event_live_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator.')})

        if not code:
            return request.render(
                'website_event_track_live.event_live_http_error_view',
                {'error_message': _('YouTube did not provide a valid authorization code.')})

        youtube_oauth_client_id = request.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_id')
        youtube_oauth_client_secret = request.env['ir.config_parameter'].sudo().get_param('event.youtube_oauth_client_secret')

        if not (youtube_oauth_client_id and youtube_oauth_client_secret):
            return request.render('website_event_track_live.event_live_http_error_view',
                                {'error_message': _('YouTube Client ID or Secret not configured.')})

        base_url = request.env.user.get_base_url()
        redirect_uri = url_join(base_url, 'event_track_youtube/callback')

        try:
            token_exchange_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': youtube_oauth_client_id,
                    'client_secret': youtube_oauth_client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'access_type': 'offline',
                    'prompt': 'consent',
                    'redirect_uri': redirect_uri,
                },
                timeout=5,
            ).json()
        except requests.exceptions.RequestException as e:
            error_message = _('Error connecting to YouTube OAuth: %(error)s', error=str(e))
            return request.render('website_event_track_live.event_live_http_error_view',
                                {'error_message': error_message})

        error_description = token_exchange_response.get('error_description')
        if error_description:
            error_message = '\n'.join([
                error_description,
                _('Reason:'),
                token_exchange_response.get('error', ''),
            ])
            return request.render('website_event_track_live.event_live_http_error_view',
                                {'error_message': error_message})

        refresh_token = token_exchange_response.get('refresh_token')
        if not refresh_token:
            return request.render('website_event_track_live.event_live_http_error_view',
                                {'error_message': _('Auth endpoint did not provide a refresh token. Please try again.')})

        access_token = token_exchange_response['access_token']
        expires_in = token_exchange_response.get('expires_in', 0)

        self._event_youtube_create_accounts(access_token, refresh_token, expires_in)
        return request.redirect('/odoo/action-website_event_track_live.event_track_live_account_action')

    def _event_youtube_create_accounts(self, access_token, refresh_token, expires_in):
        youtube_channels_endpoint = "https://www.googleapis.com/youtube/v3/channels"
        youtube_channels = requests.get(youtube_channels_endpoint,
            params={
                'mine': 'true',
                'access_token': access_token,
                'part': 'snippet,contentDetails'
            },
            timeout=5
        ).json()

        if 'error' in youtube_channels:
            return request.render('website_event_track_live.event_live_http_error_view', {
                'error_message': _('YouTube did not provide a valid access token or it may have expired.')
            })

        if 'items' not in youtube_channels:
            message = _('There is no channel linked with this YouTube account.')
            documentation_link = 'https://support.google.com/youtube/answer/6388033'
            documentation_link_label = _('Read More about YouTube Channel')
            documentation_link_icon_class = 'fa fa-youtube'
            return request.render('website_event_track_live.event_live_http_error_view', {
                'error_message': message,
                'documentation_link': documentation_link,
                'documentation_link_label': documentation_link_label,
                'documentation_link_icon_class': documentation_link_icon_class
            })

        accounts_to_create = []
        existing_accounts = self._youtube_get_existing_track_live_accounts(youtube_channels)
        for channel in youtube_channels.get('items'):
            if channel.get('kind') != 'youtube#channel':
                continue
            account_id = channel['id']
            base_values = {
                'name': channel['snippet']['title'],
                'youtube_access_token': access_token,
                'youtube_refresh_token': refresh_token,
                'youtube_token_expiration_date': fields.Datetime.now() + timedelta(seconds=int(expires_in)),
                'is_connected': True,
                'youtube_upload_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads'],
                'image': base64.b64encode(requests.get(
                    channel['snippet']['thumbnails']['medium']['url'], timeout=10).content),
                'youtube_channel_id': account_id,
            }
            if existing_accounts.get(account_id):
                existing_accounts.get(account_id).write(base_values)
            else:
                accounts_to_create.append(base_values)

        if accounts_to_create:
            request.env['event.track.live.account'].create(accounts_to_create)

    def _youtube_get_existing_track_live_accounts(self, youtube_channels):
        youtube_accounts_ids = [account['id'] for account in youtube_channels.get('items', [])]
        if youtube_accounts_ids:
            existing_accounts = request.env['event.track.live.account'].sudo().with_context(active_test=False).search([
                ('youtube_channel_id', 'in', youtube_accounts_ids)
            ])

            return {
                existing_account.youtube_channel_id: existing_account
                for existing_account in existing_accounts
            }

        return {}
