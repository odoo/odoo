# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.social_youtube.models.social_account import SocialAccountYoutube
from odoo.addons.social_youtube.models.social_stream import SocialStreamYoutube
from odoo.tests import common


class SocialYouTubeCase(common.TransactionCase):
    def test_youtube_data_cleaning(self):
        with patch.object(SocialAccountYoutube, '_create_default_stream_youtube', lambda *args, **kwargs: None), \
             patch.object(SocialStreamYoutube, '_fetch_stream_data', lambda x: None):

            SocialStreamPost = self.env['social.stream.post']
            youtube_media = self.env.ref('social_youtube.social_media_youtube')
            youtube_social_account = self.env['social.account'].create({
                'media_id': youtube_media.id,
                'name': 'Social Account'
            })
            youtube_stream_type = self.env.ref('social_youtube.stream_type_youtube_channel_videos')
            youtube_stream = self.env['social.stream'].create({
                'name': 'My Videos',
                'media_id': youtube_media.id,
                'account_id': youtube_social_account.id,
                'stream_type_id': youtube_stream_type.id,
            })

            [new_post, old_post] = SocialStreamPost.create([{
                'stream_id': youtube_stream.id
            }, {
                'stream_id': youtube_stream.id,
                'write_date': fields.Datetime.now() - relativedelta(days=31)
            }])
            new_post_id = new_post.id
            old_post_id = old_post.id
            SocialStreamPost._gc_youtube_data()

            # 'old_post' should be automatically deleted as of YouTube ToS
            # see 'social.stream.post#_gc_youtube_data()' for more information
            self.assertEqual(new_post, SocialStreamPost.search(
                [('id', 'in', [new_post_id, old_post_id])]
            ))
