# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.social_test_full.tests.common import SocialTestFullCase
from odoo.addons.social.tests.tools import mock_void_external_calls


class SocialYoutube(SocialTestFullCase):
    @mock_void_external_calls()
    def test_youtube_link(self):
        social_post = self.env['social.post'].create({
            'account_ids': self.accounts.ids,
            'message': 'Check out my great video!',
            'youtube_video_id': 'ABC123'
        })

        social_post.action_post()
        # check that the video link is correctly added in posts content
        for live_post in social_post.live_post_ids.filtered(
            lambda live_post: live_post.account_id.media_type != 'youtube'
        ):
            self.assertTrue('https://youtube.com/watch?v=ABC123' in live_post.message)

        # check that the push notification has detected the YouTube link
        # and added it as its target URL
        self.assertEqual('https://youtube.com/watch?v=ABC123', social_post.push_notification_target_url)
