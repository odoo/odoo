# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests
import werkzeug

from odoo import http, _
from odoo.addons.social.controllers.main import SocialController
from odoo.addons.social.controllers.main import SocialValidationException
from odoo.http import request
from werkzeug.urls import url_encode


class SocialLinkedinController(SocialController):
    @http.route('/social_linkedin/callback', type='http', auth='user')
    def social_linkedin_callback(self, access_token=None, code=None, state=None, **kw):
        """
        We can receive
        - code directly from LinkedIn
        - access_token from IAP
        - state from LinkedIn/IAP, the state avoid the CSRF attack
        """
        if not request.env.user.has_group('social.group_social_manager'):
            return request.render('social.social_http_error_view',
                                  {'error_message': _('Unauthorized. Please contact your administrator.')})

        if kw.get('error') not in ('user_cancelled_authorize', 'user_cancelled_login'):
            if not access_token and not code:
                return request.render('social.social_http_error_view',
                                      {'error_message': _('LinkedIn did not provide a valid access token.')})

            media = request.env.ref('social_linkedin.social_media_linkedin')

            if media.csrf_token != state:
                return request.render('social.social_http_error_view',
                                      {'error_message': _('There was a authentication issue during your request.')})

            try:
                if not access_token:
                    access_token = self._linkedin_get_access_token(code, media)

                request.env['social.account']._create_linkedin_accounts(access_token, media)

            # Both _get_linkedin_access_token and _create_linkedin_accounts may raise a SocialValidationException
            except SocialValidationException as e:
                return request.render('social.social_http_error_view', {'error_message': e.get_message(), 'documentation_data': e.get_documentation_data()})


        return request.redirect('/web?#%s' % url_encode({
            'action': request.env.ref('social.action_social_stream_post').id,
            'view_type': 'kanban',
            'model': 'social.stream.post',
        }))

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    @http.route('/social_linkedin/comment', type='http', auth='user', methods=['POST'])
    def social_linkedin_add_comment(self, stream_post_id, message=None, comment_id=None, **kwargs):
        stream_post = self._get_social_stream_post(stream_post_id, 'linkedin')
        return json.dumps(stream_post._linkedin_comment_add(message, comment_id))

    @http.route('/social_linkedin/delete_comment', type='json', auth='user')
    def social_linkedin_delete_comment(self, stream_post_id, comment_id, **kwargs):
        stream_post = self._get_social_stream_post(stream_post_id, 'linkedin')
        return stream_post._linkedin_comment_delete(comment_id)

    @http.route('/social_linkedin/get_comments', type='json', auth='user')
    def social_linkedin_get_comments(self, stream_post_id, comment_urn=None, offset=0, comments_count=20):
        stream_post = self._get_social_stream_post(stream_post_id, 'linkedin')
        return stream_post._linkedin_comment_fetch(
            comment_urn=comment_urn,
            offset=offset,
            count=comments_count
        )

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _linkedin_get_access_token(self, linkedin_authorization_code, media):
        """
        Take the `authorization code` and exchange it for an `access token`
        We also need the `redirect uri`

        :return: the access token
        """
        linkedin_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        linkedin_app_id = request.env['ir.config_parameter'].sudo().get_param('social.linkedin_app_id')
        linkedin_client_secret = request.env['ir.config_parameter'].sudo().get_param('social.linkedin_client_secret')

        params = {
            'grant_type': 'authorization_code',
            'code': linkedin_authorization_code,
            'redirect_uri': media._get_linkedin_redirect_uri(),
            'client_id': linkedin_app_id,
            'client_secret': linkedin_client_secret
        }

        response = requests.post(linkedin_url, data=params, timeout=5).json()

        error_description = response.get('error_description')
        if error_description:
            raise SocialValidationException(error_description)

        return response.get('access_token')
