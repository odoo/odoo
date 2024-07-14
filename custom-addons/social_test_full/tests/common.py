# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.tests import common


class SocialTestFullCase(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(SocialTestFullCase, cls).setUpClass()
        media_refs = [
            'social_instagram.social_media_instagram',
            'social_facebook.social_media_facebook',
            'social_twitter.social_media_twitter',
            'social_linkedin.social_media_linkedin',
            'social_push_notifications.social_media_push_notifications',
            'social_youtube.social_media_youtube',
        ]

        with mock_void_external_calls():
            # create one account for every media type
            cls.accounts = cls.env['social.account'].create([{
                'media_id': cls.env.ref(media_ref).id,
                'name': 'Account'
            } for media_ref in media_refs])
