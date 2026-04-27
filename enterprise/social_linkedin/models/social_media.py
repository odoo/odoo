# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from werkzeug.urls import url_encode, url_join

from odoo import _, models, fields
from odoo.exceptions import UserError


class SocialMediaLinkedin(models.Model):
    _inherit = 'social.media'

    _LINKEDIN_ENDPOINT = 'https://api.linkedin.com/rest/'
    _LINKEDIN_SCOPE = 'r_basicprofile r_organization_followers w_member_social w_member_social_feed rw_organization_admin w_organization_social w_organization_social_feed r_organization_social r_organization_social_feed'

    media_type = fields.Selection(selection_add=[('linkedin', 'LinkedIn')])

    def _action_add_account(self):
        self.ensure_one()

        if self.media_type != 'linkedin':
            return super(SocialMediaLinkedin, self)._action_add_account()

        linkedin_use_own_account = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_use_own_account')
        linkedin_app_id = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_app_id')
        linkedin_client_secret = self.env['ir.config_parameter'].sudo().get_param('social.linkedin_client_secret')

        if linkedin_app_id and linkedin_client_secret and linkedin_use_own_account:
            return self._add_linkedin_accounts_from_configuration(linkedin_app_id)
        else:
            return self._add_linkedin_accounts_from_iap()

    def _add_linkedin_accounts_from_configuration(self, linkedin_app_id):
        params = {
            'response_type': 'code',
            'client_id': linkedin_app_id,
            'redirect_uri': self._get_linkedin_redirect_uri(),
            'state': self.csrf_token,
            'scope': self._LINKEDIN_SCOPE,
        }

        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(params),
            'target': 'self'
        }

    def _add_linkedin_accounts_from_iap(self):
        o_redirect_uri = url_join(self.get_base_url(), 'social_linkedin/callback')

        social_iap_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'social.social_iap_endpoint',
            self.env['social.media']._DEFAULT_SOCIAL_IAP_ENDPOINT
        )

        iap_add_accounts_url = requests.get(url_join(social_iap_endpoint, 'api/social/linkedin/1/add_accounts'), params={
            'state': self.csrf_token,
            'scope': self._LINKEDIN_SCOPE,
            'o_redirect_uri': o_redirect_uri,
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        }, timeout=5).text

        if iap_add_accounts_url == 'unauthorized':
            raise UserError(_("You don't have an active subscription. Please buy one here: %s", 'https://www.odoo.com/buy'))
        elif iap_add_accounts_url == 'linkedin_missing_configuration' or iap_add_accounts_url == 'missing_parameters':
            raise UserError(_("The url that this service requested returned an error. Please contact the author of the app."))

        return {
            'type': 'ir.actions.act_url',
            'url': iap_add_accounts_url,
            'target': 'self'
        }

    def _get_linkedin_redirect_uri(self):
        return url_join(self.get_base_url(), 'social_linkedin/callback')
