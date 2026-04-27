# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
import urllib.parse

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_join

from odoo import http, _
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.auth_oauth.controllers.main import fragment_to_query_string
from odoo.addons.social.controllers.main import SocialController
from odoo.addons.social.controllers.main import SocialValidationException

_logger = logging.getLogger(__name__)


class SocialFacebookController(SocialController):
    # ========================================================
    # ACCOUNTS MANAGEMENT
    # ========================================================

    @http.route(['/social_facebook/callback'], type='http', auth='user')
    @fragment_to_query_string
    def social_facebook_account_callback(self, access_token=None, is_extended_token=False, **kw):
        """ Facebook returns to the callback URL with all its own arguments as hash parameters.
        We use this very handy 'fragment_to_query_string' decorator to convert them to server readable parameters. """
        if not request.env.user.has_group('social.group_social_manager'):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator. ')})

        if kw.get('error') != 'access_denied':
            if not access_token:
                return request.render(
                    'social.social_http_error_view',
                    {'error_message': _('Facebook did not provide a valid access token.')})

            if access_token:
                media = request.env.ref('social_facebook.social_media_facebook')

                try:
                    self._facebook_create_accounts(access_token, media, is_extended_token)
                except SocialValidationException as e:
                    return request.render('social.social_http_error_view', {'error_message': e.get_message(), 'documentation_data': e.get_documentation_data()})

        return request.redirect('/odoo/action-social.action_social_stream_post')

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    @http.route('/social_facebook/comment', type='http', auth='user', methods=['POST'])
    def social_facebook_add_comment(self, stream_post_id=None, message=None, comment_id=None, existing_attachment_id=None, is_edit=False, **kwargs):
        stream_post = self._get_social_stream_post(stream_post_id, 'facebook')
        attachment = None
        files = request.httprequest.files.getlist('attachment')
        if files and files[0]:
            attachment = files[0]

        if comment_id and is_edit:
            result = stream_post._facebook_comment_post(
                url_join(request.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, comment_id),
                message,
                existing_attachment_id=existing_attachment_id,
                attachment=attachment
            )
        elif comment_id:
            result = stream_post._facebook_comment_post(
                url_join(request.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/comments" % (comment_id)),
                message,
                existing_attachment_id=existing_attachment_id,
                attachment=attachment
            )
        else:
            result = stream_post._facebook_comment_post(
                url_join(request.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/comments" % (stream_post.facebook_post_id)),
                message,
                existing_attachment_id=existing_attachment_id,
                attachment=attachment
            )

        result['formatted_created_time'] = request.env['social.stream.post']._format_facebook_published_date(result)
        return json.dumps(result)

    @http.route('/social_facebook/delete_comment', type='json', auth='user')
    def social_facebook_delete_comment(self, stream_post_id, comment_id):
        stream_post = self._get_social_stream_post(stream_post_id, 'facebook')
        stream_post._facebook_comment_delete(comment_id)

    @http.route('/social_facebook/get_comments', type='json', auth='user')
    def social_facebook_get_comments(self, stream_post_id, next_records_token=False, comments_count=20):
        stream_post = self._get_social_stream_post(stream_post_id, 'facebook')
        return stream_post._facebook_comment_fetch(next_records_token, count=comments_count)

    @http.route('/social_facebook/like_comment', type='json', auth='user')
    def social_facebook_like_comment(self, stream_post_id, comment_id, like):
        stream_post = self._get_social_stream_post(stream_post_id, 'facebook')
        stream_post._facebook_like(comment_id, like)

    @http.route('/social_facebook/like_post', type='json', auth='user')
    def social_facebook_like_post(self, stream_post_id, like):
        stream_post = self._get_social_stream_post(stream_post_id, 'facebook')
        stream_post._facebook_like(stream_post.facebook_post_id, like)

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    @http.route(['/social_facebook/deletion_callback'], type='http', auth='none', methods=['POST'], csrf=False)
    def social_facebook_deletion_callback(self, secret, facebook_page_identifiers):
        """Callback that IAP will hit, when a user asked to remove his data from Facebook.

        That request is initiated from the user's Facebook page settings.

        > https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback
        """
        if (
            not facebook_page_identifiers
            or not secret
            or not consteq(secret, request.env['social.media']._get_social_facebook_deletion_shared_secret())
        ):
            raise Forbidden()

        accounts = request.env['social.account'].sudo().with_context(active_test=False).search(
            [('facebook_account_id', 'in', json.loads(facebook_page_identifiers))])
        _logger.info(
            'The following Social Facebook Accounts were requested to be deleted by the end user: %r',
            ', '.join(accounts.mapped('name')),
        )
        request.env['social.post'].sudo().search([('account_ids', 'in', accounts.ids)]).unlink()
        request.env['social.post.template'].sudo().search([('account_ids', 'in', accounts.ids)]).unlink()
        accounts.unlink()
        return 'OK'

    @http.route(['/social_facebook/redirect_to_profile/<int:account_id>/<facebook_user_id>'], type='http', auth='user')
    def social_facebook_redirect_to_profile(self, account_id, facebook_user_id, name=''):
        """
        All profiles are not available through a direct link so we need to
        - Try to get a direct link to their profile
        - If we can't, we perform a search on Facebook with their name
        """
        account = request.env['social.account'].browse(account_id)

        json_response = requests.get(
            url_join(request.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, facebook_user_id),
            params={
                'fields': 'name,link',
                'access_token': account.facebook_access_token
            },
            timeout=5
        ).json()

        profile_url = json_response.get('link')
        if profile_url:
            redirect_url = profile_url
        else:
            redirect_url = 'https://www.facebook.com/search/?q=%s' % urllib.parse.quote(name)

        return request.redirect(redirect_url, local=False)

    def _facebook_create_accounts(self, access_token, media, is_extended_token):
        """ Steps to create the facebook social.accounts:
        1. Fetch an extended access token (see '_facebook_get_extended_access_token' for more info)
        2. Query the accounts api with that token
        3. Extract the 'pages' contained in the json result
        4. Create a social.account with its associated token (each page has its own access token)
        4a. If the social.account was already created before, we refresh its access_token """

        extended_access_token = access_token if is_extended_token else self._facebook_get_extended_access_token(access_token, media)
        accounts_url = url_join(request.env['social.media']._FACEBOOK_ENDPOINT, "/me/accounts/")
        json_response = requests.get(accounts_url,
            params={
                'fields': 'id,access_token,name,username',
                'access_token': extended_access_token
            },
            timeout=5
        ).json()

        if 'data' not in json_response:
            raise SocialValidationException(_('Facebook did not provide a valid access token or it may have expired.'))
        if not json_response['data']:
            message = _('You need to be the manager of a Facebook Page to post with Odoo Social.\n Please create one and make sure it is linked to your account.')
            documentation_link = 'https://facebook.com/business/pages/manage'
            documentation_link_label = _('Read More about Facebook Pages')
            documentation_link_icon_class = 'fa fa-facebook'
            raise SocialValidationException(message, documentation_link, documentation_link_label, documentation_link_icon_class)

        accounts_to_create = []
        existing_accounts = self._facebook_get_existing_accounts(media, json_response)
        for account in json_response.get('data'):
            account_id = account['id']
            access_token = account.get('access_token')
            social_account_handle = account.get('username')
            if existing_accounts.get(account_id):
                # update access token
                # TODO awa: maybe check for name/picture update?
                existing_accounts.get(account_id).write({
                    'active': True,
                    'facebook_access_token': access_token,
                    'social_account_handle': social_account_handle,
                    'is_media_disconnected': False
                })
            else:
                accounts_to_create.append({
                    'name': account.get('name'),
                    'media_id': media.id,
                    'has_trends': True,
                    'facebook_account_id': account_id,
                    'facebook_access_token': access_token,
                    'social_account_handle': social_account_handle,
                    'image': self._facebook_get_profile_image(account_id)
                })

        if accounts_to_create:
            request.env['social.account'].create(accounts_to_create)

    def _facebook_get_extended_access_token(self, access_token, media):
        """ The way that it works is Facebook sends you a token that is valid for 2 hours
        that you can automatically 'extend' to a 60 days token using the oauth/access_token endpoint.

        After those 60 days, there is absolutely no way to renew the token automatically, we have to ask
        the user's permissions again manually.
        However, using this extended token with the 'manage_pages' permission allows receiving 'Page Access Tokens'
        that are valid forever.

        More details on this mechanic: https://www.devils-heaven.com/facebook-access-tokens/ """

        facebook_app_id = request.env['ir.config_parameter'].sudo().get_param('social.facebook_app_id')
        facebook_client_secret = request.env['ir.config_parameter'].sudo().get_param('social.facebook_client_secret')
        extended_token_url = url_join(request.env['social.media']._FACEBOOK_ENDPOINT, "/oauth/access_token")
        extended_token_request = requests.post(extended_token_url,
            params={
                'client_id': facebook_app_id,
                'client_secret': facebook_client_secret,
                'grant_type': 'fb_exchange_token',
                'fb_exchange_token': access_token
            },
            timeout=5
        )
        return extended_token_request.json().get('access_token')

    def _facebook_get_profile_image(self, account_id):
        profile_image_url = url_join(request.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, '%s/picture?height=300' % account_id)
        return base64.b64encode(requests.get(profile_image_url, timeout=10).content)

    def _facebook_get_existing_accounts(self, media_id, json_response):
        """ Returns the social.accounts already created as:
        { facebook_account_id: social.account } """

        facebook_accounts_ids = [account['id'] for account in json_response.get('data', [])]
        if facebook_accounts_ids:
            existing_accounts = request.env['social.account'].sudo().with_context(active_test=False).search([
                ('media_id', '=', int(media_id)),
                ('facebook_account_id', 'in', facebook_accounts_ids)
            ])

            error_message = existing_accounts._get_multi_company_error_message()
            if error_message:
                raise SocialValidationException(error_message)

            return {
                existing_account.facebook_account_id: existing_account
                for existing_account in existing_accounts
            }

        return {}
