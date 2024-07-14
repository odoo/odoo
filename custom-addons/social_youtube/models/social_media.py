# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.parser
import requests

from odoo import _, api, models, fields
from odoo.exceptions import UserError
from werkzeug.urls import url_encode, url_join


class SocialMediaYoutube(models.Model):
    _inherit = 'social.media'

    _YOUTUBE_ENDPOINT = 'https://www.googleapis.com'

    media_type = fields.Selection(selection_add=[('youtube', 'YouTube')])

    def _action_add_account(self):
        self.ensure_one()

        if self.media_type != 'youtube':
            return super(SocialMediaYoutube, self)._action_add_account()

        youtube_oauth_client_id = self.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_id')
        youtube_oauth_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.youtube_oauth_client_secret')
        if youtube_oauth_client_id and youtube_oauth_client_secret:
            return self._add_youtube_accounts_from_configuration(youtube_oauth_client_id)
        else:
            return self._add_youtube_accounts_from_iap()

    def _add_youtube_accounts_from_configuration(self, youtube_oauth_client_id):
        """ Builds the URL to Youtube with the appropriate page rights request, then redirects the client.

        Redirect is done in 'self' since Youtube will then return back to the app with the 'redirect_uri' param.
        Redirect URI from Youtube will land on this module controller's 'youtube_account_callback' method.

        Youtube will display an error message if the callback URI is not correctly defined in the Youtube APP settings. """

        base_youtube_url = 'https://accounts.google.com/o/oauth2/v2/auth?%s'
        params = {
            'client_id': youtube_oauth_client_id,
            'redirect_uri': url_join(self.get_base_url(), "social_youtube/callback"),
            'response_type': 'code',
            'scope': ' '.join([
                'https://www.googleapis.com/auth/youtube.force-ssl',
                'https://www.googleapis.com/auth/youtube.upload'
            ]),
            'access_type': 'offline',
            'prompt': 'consent',
        }

        return {
            'type': 'ir.actions.act_url',
            'url': base_youtube_url % url_encode(params),
            'target': 'self'
        }

    def _add_youtube_accounts_from_iap(self):
        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )

        iap_add_accounts_url = requests.get(url_join(social_iap_endpoint, 'api/social/youtube/1/add_accounts'),
            params={
                'returning_url': url_join(self.get_base_url(), 'social_youtube/callback'),
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            },
            timeout=5
        ).text

        if iap_add_accounts_url == 'unauthorized':
            raise UserError(_("You don't have an active subscription. Please buy one here: %s", 'https://www.odoo.com/buy'))
        elif iap_add_accounts_url == 'youtube_missing_configuration':
            raise UserError(_("The url that this service requested returned an error. Please contact the author of the app."))

        return {
            'type': 'ir.actions.act_url',
            'url': iap_add_accounts_url,
            'target': 'self'
        }

    @api.model
    def _format_youtube_comment(self, youtube_comment):
        """ Formats a comment returned by the YouTube API to a dict that will be interpreted by our frontend. """
        comment_snippet = youtube_comment['snippet']
        return {
            'id': youtube_comment.get('id'),
            'message': comment_snippet.get('textDisplay'),
            'from': {
                'id': comment_snippet.get('authorChannelId', {}).get('value'),
                'name': comment_snippet.get('authorDisplayName'),
                'author_image_url': comment_snippet.get('authorProfileImageUrl'),
                'author_channel_url': comment_snippet.get('authorChannelUrl')
            },
            'created_time': comment_snippet.get('publishedAt'),
            'formatted_created_time': self.env['social.stream.post']._format_published_date(fields.Datetime.from_string(
                dateutil.parser.parse(comment_snippet.get('publishedAt')).strftime('%Y-%m-%d %H:%M:%S')
            )),
            'likes': {
                'summary': {
                    'total_count': comment_snippet.get('likeCount')
                }
            },
        }
