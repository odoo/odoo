# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import _, models, fields, tools
from odoo.exceptions import UserError
from werkzeug.urls import url_encode, url_join


class SocialMediaFacebook(models.Model):
    _inherit = 'social.media'

    _FACEBOOK_ENDPOINT = 'https://graph.facebook.com'
    _FACEBOOK_ENDPOINT_VERSIONED = '%s/v17.0/' % _FACEBOOK_ENDPOINT

    media_type = fields.Selection(selection_add=[('facebook', 'Facebook')])

    def _action_add_account(self):
        """ Builds the URL to Facebook with the appropriate page rights request, then redirects the client.
        Redirect is done in 'self' since Facebook will then return back to the app with the 'redirect_uri' param.

        Redirect URI from Facebook will land on this module controller's 'facebook_account_callback' method.

        Facebook will display an error message if the callback URI is not correctly defined in the Facebook APP settings. """

        self.ensure_one()

        if self.media_type != 'facebook':
            return super(SocialMediaFacebook, self)._action_add_account()

        facebook_app_id = self.env['ir.config_parameter'].sudo().get_param('social.facebook_app_id')
        facebook_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.facebook_client_secret')
        if facebook_app_id and facebook_client_secret:
            return self._add_facebook_accounts_from_configuration(facebook_app_id)
        else:
            return self._add_facebook_accounts_from_iap()

    def _add_facebook_accounts_from_configuration(self, facebook_app_id):
        base_facebook_url = 'https://www.facebook.com/v17.0/dialog/oauth?%s'
        scopes = [
                'pages_manage_ads',
                'pages_manage_metadata',
                'pages_read_engagement',
                'pages_read_user_content',
                'pages_manage_engagement',
                'pages_manage_posts',
                'read_insights'
        ]
        if not self.env['ir.config_parameter'].sudo().get_param('social.facebook_no_business_management'):
            scopes.append("business_management")
        params = {
            'client_id': facebook_app_id,
            'redirect_uri': url_join(self.get_base_url(), "social_facebook/callback"),
            'response_type': 'token',
            'scope': ','.join(scopes),
        }

        return {
            'type': 'ir.actions.act_url',
            'url': base_facebook_url % url_encode(params),
            'target': 'self'
        }

    def _add_facebook_accounts_from_iap(self):
        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )

        iap_add_accounts_url = requests.get(url_join(social_iap_endpoint, 'api/social/facebook/1/add_accounts'),
            params={
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'returning_url': url_join(self.get_base_url(), 'social_facebook/callback'),
                'client_host_url': self.get_base_url(),
                'deletion_shared_secret': self._get_social_facebook_deletion_shared_secret(),
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

    def _get_social_facebook_deletion_shared_secret(self):
        """Shared secret between the database and IAP, derived from the database secret."""
        return tools.hmac(self.env(su=True), 'social_facebook-deletion_shared_secret', None)
