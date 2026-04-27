# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import requests
import werkzeug

from odoo import _, http
from odoo.addons.auth_oauth.controllers.main import fragment_to_query_string
from odoo.addons.social.controllers.main import SocialController
from odoo.addons.social.controllers.main import SocialValidationException
from odoo.http import request
from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_join


class SocialInstagramController(SocialController):

    @http.route('/social_instagram/callback', type='http', auth='user')
    @fragment_to_query_string
    def social_instagram_callback(self, access_token=None, extended_access_token=None, **kw):
        if not request.env.user.has_group('social.group_social_manager'):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator.')})

        request_csrf = kw.get('state')
        if not request_csrf or (not access_token and not extended_access_token):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Instagram did not provide a valid access token.')})

        media = request.env.ref('social_instagram.social_media_instagram')
        if media.csrf_token != request_csrf:
            return request.render('social.social_http_error_view',
                                  {'error_message': _('There was a authentication issue during your request.')})

        try:
            self._instagram_create_accounts(access_token, extended_access_token)
        except SocialValidationException as e:
            return request.render('social.social_http_error_view', {'error_message': e.get_message(), 'documentation_data': e.get_documentation_data()})

        return request.redirect('/odoo/action-social.action_social_stream_post')

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    @http.route('/social_instagram/comment', type='http', auth='user', methods=['POST'])
    def social_instagram_comment(self, stream_post_id=None, message=None, comment_id=None, **kwargs):
        """ Route used to add comments on an Instagram post or reply to a comment.
        If 'comment_id' is passed, then it's a reply, otherwise it's a standard comment on the post. """

        stream_post = self._get_social_stream_post(stream_post_id, 'instagram')
        if comment_id:
            result = stream_post._instagram_comment_add(message, comment_id, comment_type='reply')
        else:
            result = stream_post._instagram_comment_add(message, stream_post.instagram_post_id)

        return json.dumps(result)

    @http.route('/social_instagram/delete_comment', type='json', auth='user')
    def social_instagram_delete_comment(self, stream_post_id, comment_id):
        stream_post = self._get_social_stream_post(stream_post_id, 'instagram')
        return stream_post._instagram_comment_delete(comment_id)

    @http.route('/social_instagram/get_comments', type='json', auth='user')
    def social_instagram_get_comments(self, stream_post_id, next_records_token=False, comments_count=20):
        stream_post = self._get_social_stream_post(stream_post_id, 'instagram')
        return stream_post._instagram_comment_fetch(next_records_token, count=comments_count)

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    @http.route(['/social_instagram/<string:instagram_access_token>/get_image/<int:image_id>'], type='http', auth='public')
    def social_post_instagram_image(self, instagram_access_token, image_id):
        social_post = request.env['social.post'].sudo().search(
            [('instagram_access_token', '=', instagram_access_token)])

        if not social_post or not image_id in social_post.instagram_image_ids.ids:
            raise Forbidden()

        # called manually to throw a ValidationError if not valid instagram image
        social_post._check_post_access()

        return request.env['ir.binary']._get_image_stream_from(
            social_post.instagram_image_ids.filtered(lambda image: image.id == image_id),
            default_mimetype='image/jpeg',
        ).get_response()

    def _instagram_create_accounts(self, access_token, extended_access_token):
        """ 1. Retrieve all Facebook pages data from '/me/accounts'
            2. For each page, fetch detailed information
            3. If a 'instagram_business_account' is returned, create a matching social.account. """

        media = request.env.ref('social_instagram.social_media_instagram')
        accounts_url = url_join(request.env['social.media']._INSTAGRAM_ENDPOINT, "/me/accounts/")
        accounts = requests.get(accounts_url, params={
            'fields': 'access_token,name,id,instagram_business_account',
            'access_token': extended_access_token or self._instagram_get_extended_access_token(access_token, media)
        }).json()

        if 'data' not in accounts:
            raise SocialValidationException(_('Could not find any account to add.'))

        existing_accounts = {
            account_id.instagram_account_id: account_id
            for account_id in request.env['social.account'].search([
                ('media_id', '=', media.id)])
        }

        accounts_to_create = []
        has_existing_accounts = False
        for account in accounts['data']:
            instagram_access_token = account.get('access_token')
            facebook_account_id = account['id']
            instagram_account_id = account.get('instagram_business_account', {}).get('id')

            if not instagram_access_token or not instagram_account_id:
                continue

            instagram_accounts_endpoint = url_join(
                request.env['social.media']._INSTAGRAM_ENDPOINT,
                f'/v17.0/{instagram_account_id}')

            instagram_account = requests.get(instagram_accounts_endpoint,
                params={
                    'fields': 'username',
                    'access_token': instagram_access_token
                },
                timeout=5
            ).json()

            account_values = {
                'name': account['name'],
                'instagram_facebook_account_id': facebook_account_id,
                'instagram_account_id': instagram_account_id,
                'instagram_access_token': instagram_access_token,
                'social_account_handle': instagram_account['username'],
                'image': self._instagram_get_profile_image(facebook_account_id)
            }

            if account_values['instagram_account_id'] in existing_accounts:
                has_existing_accounts = True
                account_values.update({'is_media_disconnected': False})
                existing_accounts[account_values['instagram_account_id']].write(account_values)
            else:
                account_values.update({
                    'media_id': media.id,
                    'has_trends': True,
                })
                accounts_to_create.append(account_values)

        if accounts_to_create:
            request.env['social.account'].create(accounts_to_create)
        elif not has_existing_accounts:
            message = _('You need to link your Instagram page to your Facebook account to post with Odoo Social.\n Please create one and make sure it is linked to your account.')
            documentation_link = 'https://help.instagram.com/176235449218188'
            documentation_link_label = _('Read More about Instagram Accounts')
            documentation_link_icon_class = 'fa fa-instagram'
            raise SocialValidationException(message, documentation_link, documentation_link_label, documentation_link_icon_class)

    def _instagram_get_extended_access_token(self, access_token, media):
        """ Same mechanism as social_facebook/controllers/main.py#_get_extended_access_token """

        instagram_app_id = request.env['ir.config_parameter'].sudo().get_param('social.instagram_app_id')
        instagram_client_secret = request.env['ir.config_parameter'].sudo().get_param('social.instagram_client_secret')
        extended_token_url = url_join(request.env['social.media']._INSTAGRAM_ENDPOINT, "/oauth/access_token")
        extended_token_request = requests.post(extended_token_url,
            params={
                'client_id': instagram_app_id,
                'client_secret': instagram_client_secret,
                'fb_exchange_token': access_token,
                'grant_type': 'fb_exchange_token'
            },
            timeout=5
        )
        return extended_token_request.json().get('access_token')

    def _instagram_get_profile_image(self, account_id):
        profile_image_url = url_join(
            request.env['social.media']._INSTAGRAM_ENDPOINT,
            '/v17.0/%s/picture?height=300' % account_id)
        return base64.b64encode(requests.get(profile_image_url, timeout=10).content)
