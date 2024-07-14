# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class DemoSocialAccount(models.Model):
    _inherit = 'social.account'

    def _compute_statistics(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_facebook(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_twitter(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_youtube(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _refresh_youtube_token(self):
        """ Overridden to bypass third-party API calls. """
        return

    def _create_default_stream_instagram(self):
        """ Overridden to bypass third-party API calls. """
        return

    def twitter_get_user_by_username(self, query):
        """ Returns some fake suggestion """
        partner = self.env.ref('social_demo.res_partner_2', raise_if_not_found=False)
        return {
            'name': partner.name,
            'profile_image_url': f'/web/image/res.partner/{partner.id}/avatar_128',
            'username': partner.name.replace(' ', '').lower(),
            'description': "https://example.com",
        }
