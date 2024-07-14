# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from werkzeug.urls import url_encode, url_join

from odoo import _, fields, models
from odoo.exceptions import UserError


class SocialMediaInstagram(models.Model):
    """ The Instagram social media implementation is a bit special because it goes through
    the Facebook API to fetch information (as Facebook owns Instagram).

    That also means we can only add Instagram accounts through Facebook. """

    _inherit = 'social.media'

    _INSTAGRAM_ENDPOINT = 'https://graph.facebook.com/'

    media_type = fields.Selection(selection_add=[('instagram', 'Instagram')])

    def _action_add_account(self):
        self.ensure_one()

        if self.media_type != 'instagram':
            return super(SocialMediaInstagram, self)._action_add_account()

        instagram_app_id = self.env['ir.config_parameter'].sudo().get_param('social.instagram_app_id')
        instagram_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.instagram_client_secret')
        if instagram_app_id and instagram_client_secret:
            return self._add_instagram_accounts_from_configuration(instagram_app_id)
        else:
            return self._add_instagram_accounts_from_iap()

    def _add_instagram_accounts_from_configuration(self, instagram_app_id):
        base_url = self.get_base_url()
        base_instagram_url = 'https://www.facebook.com/v17.0/dialog/oauth?%s'

        params = {
            'client_id': instagram_app_id,
            'redirect_uri': url_join(base_url, "social_instagram/callback"),
            'response_type': 'token',
            'state': self.csrf_token,
            'scope': ','.join([
                'instagram_basic',
                'instagram_content_publish',
                'instagram_manage_comments',
                'instagram_manage_insights',
                'pages_show_list',
                'pages_manage_ads',
                'pages_manage_metadata',
                'pages_read_engagement',
                'pages_read_user_content',
                'pages_manage_engagement',
                'pages_manage_posts',
                'read_insights',
                'business_management',
            ])
        }

        return {
            'type': 'ir.actions.act_url',
            'url': base_instagram_url % url_encode(params),
            'target': 'self'
        }

    def _add_instagram_accounts_from_iap(self):
        base_url = self.get_base_url()
        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )

        iap_add_accounts_url = requests.get(url_join(social_iap_endpoint, 'api/social/instagram/1/add_accounts'),
            params={
                'returning_url': url_join(base_url, 'social_instagram/callback'),
                'csrf_token': self.csrf_token,
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            },
            timeout=5
        ).text

        if iap_add_accounts_url == 'unauthorized':
            raise UserError(_("You don't have an active subscription. Please buy one here: %s", 'https://www.odoo.com/buy'))

        return {
            'type': 'ir.actions.act_url',
            'url': iap_add_accounts_url,
            'target': 'self'
        }
