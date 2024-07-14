# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import requests

from datetime import timedelta
from odoo import _, fields, http
from odoo.addons.social.controllers.main import SocialController
from odoo.addons.social.controllers.main import SocialValidationException
from odoo.http import request
from werkzeug.urls import url_encode, url_join


class SocialYoutubeController(SocialController):
    @http.route('/social_youtube/callback', type='http', auth='user')
    def youtube_account_callback(self, code=None, iap_access_token=None, iap_refresh_token=None, iap_expires_in=0, **kw):
        """ Main entry point that receives YouTube information as part of the OAuth flow.
        There are 2 different ways of reaching this method:
        - Database is configured to use 'Own YouTube account'
          This method will receive a 'code' from the YouTube OAuth flow and use it to exchange for a
          pair of valid access_token/refresh_token
        - Using our IAP proxy (for databases with valid enterprise subscriptions)
          This method will directly receive the valid pair of access_token/refresh_token from the
          IAP proxy. """

        if not request.env.user.has_group('social.group_social_manager'):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator.')})

        if (not iap_access_token or not iap_access_token) and not code:
            return request.render(
                'social.social_http_error_view',
                {'error_message': _('YouTube did not provide a valid authorization code.')})

        youtube_media = request.env.ref('social_youtube.social_media_youtube')
        youtube_oauth_client_id = request.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_id')
        youtube_oauth_client_secret = request.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_secret')

        if iap_access_token and iap_refresh_token:
            access_token = iap_access_token
            refresh_token = iap_refresh_token
            expires_in = iap_expires_in
        else:
            base_url = youtube_media.get_base_url()
            token_exchange_response = requests.post('https://oauth2.googleapis.com/token',
                data={
                    'client_id': youtube_oauth_client_id,
                    'client_secret': youtube_oauth_client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'access_type': 'offline',
                    'prompt': 'consent',
                    # unclear why 'redirect_uri' is necessary, probably used as a validation by Google
                    'redirect_uri': url_join(base_url, 'social_youtube/callback'),
                },
                timeout=5
            ).json()

            if token_exchange_response.get('error_description'):
                return request.render('social.social_http_error_view', {
                    'error_message': '\n'.join([
                        token_exchange_response.get('error_description'),
                        _('Reason:'),
                        token_exchange_response.get('error')],
                    )
                })

            if not token_exchange_response.get('refresh_token'):
                return request.render('social.social_http_error_view', {
                    'error_message': _('Auth endpoint did not provide a refresh token. Please try again.')
                })

            access_token = token_exchange_response['access_token']
            refresh_token = token_exchange_response['refresh_token']
            expires_in = token_exchange_response.get('expires_in', 0)

        try:
            self._youtube_create_accounts(access_token, refresh_token, expires_in)
        except SocialValidationException as e:
            return request.render('social.social_http_error_view', {'error_message': e.get_message(), 'documentation_data': e.get_documentation_data()})

        url = '/web?#%s' % url_encode({
            'action': request.env.ref('social.action_social_stream_post').id,
            'view_type': 'kanban',
            'model': 'social.stream.post',
        })
        return request.redirect(url)

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    @http.route('/social_youtube/comment', type='http', auth='user', methods=['POST'])
    def social_youtube_comment(self, stream_post_id=None, comment_id=None, message=None, is_edit=False, **kwargs):
        stream_post = self._get_social_stream_post(stream_post_id, 'youtube')
        return json.dumps(stream_post._youtube_comment_add(comment_id, message, is_edit=is_edit))

    @http.route('/social_youtube/delete_comment', type='json', auth='user')
    def social_youtube_delete_comment(self, stream_post_id=None, comment_id=None):
        stream_post = self._get_social_stream_post(stream_post_id, 'youtube')
        return stream_post._youtube_comment_delete(comment_id)

    @http.route('/social_youtube/get_comments', type='json', auth='user')
    def social_youtube_get_comments(self, stream_post_id, next_page_token=False, comments_count=20):
        stream_post = self._get_social_stream_post(stream_post_id, 'youtube')
        return stream_post._youtube_comment_fetch(next_page_token, count=comments_count)

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _youtube_create_accounts(self, access_token, refresh_token, expires_in):
        youtube_channels_endpoint = url_join(request.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/channels")
        youtube_channels = requests.get(youtube_channels_endpoint,
            params={
                'mine': 'true',
                'access_token': access_token,
                'part': 'snippet,contentDetails'
            },
            timeout=5
        ).json()

        if 'error' in youtube_channels:
            raise SocialValidationException(_('YouTube did not provide a valid access token or it may have expired.'))

        if 'items' not in youtube_channels:
            message = _('There is no channel linked with this YouTube account.')
            documentation_link = 'https://support.google.com/youtube/answer/6388033'
            documentation_link_label = _('Read More about YouTube Channel')
            documentation_link_icon_class = 'fa fa-youtube'
            raise SocialValidationException(message, documentation_link, documentation_link_label, documentation_link_icon_class)

        accounts_to_create = []
        existing_accounts = self._youtube_get_existing_accounts(youtube_channels)
        youtube_media = request.env.ref('social_youtube.social_media_youtube')
        for channel in youtube_channels.get('items'):
            if channel.get('kind') != 'youtube#channel':
                continue

            account_id = channel['id']
            base_values = {
                'active': True,
                'name': channel['snippet']['title'],
                'social_account_handle': channel['snippet'].get('customUrl', '').lstrip('@'),
                'youtube_access_token': access_token,
                'youtube_refresh_token': refresh_token,
                'youtube_token_expiration_date': fields.Datetime.now() + timedelta(seconds=int(expires_in)),
                'youtube_upload_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads'],
                'is_media_disconnected': False,
                'image': base64.b64encode(requests.get(
                    channel['snippet']['thumbnails']['medium']['url'], timeout=10).content)
            }

            if existing_accounts.get(account_id):
                existing_accounts.get(account_id).write(base_values)
            else:
                base_values.update({
                    'youtube_channel_id': account_id,
                    'media_id': youtube_media.id,
                    'has_trends': False
                })
                accounts_to_create.append(base_values)

        if accounts_to_create:
            request.env['social.account'].create(accounts_to_create)

    def _youtube_get_existing_accounts(self, youtube_channels):
        youtube_accounts_ids = [account['id'] for account in youtube_channels.get('items', [])]
        if youtube_accounts_ids:
            existing_accounts = request.env['social.account'].sudo().with_context(active_test=False).search([
                ('media_id', '=', request.env.ref('social_youtube.social_media_youtube').id),
                ('youtube_channel_id', 'in', youtube_accounts_ids)
            ])

            error_message = existing_accounts._get_multi_company_error_message()
            if error_message:
                raise SocialValidationException(error_message)

            return {
                existing_account.youtube_channel_id: existing_account
                for existing_account in existing_accounts
            }

        return {}
