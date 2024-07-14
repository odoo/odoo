# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import random

from odoo import api, models


class DemoSocialStream(models.Model):
    _inherit = 'social.stream'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(DemoSocialStream, self).create(vals_list)

        demo_streams = [
            self.env.ref('social_demo.social_stream_facebook_page', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_twitter_account', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_twitter_search', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_twitter_search_competitor', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_linkedin_page', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_youtube_account', raise_if_not_found=False),
            self.env.ref('social_demo.social_stream_instagram_account', raise_if_not_found=False),
        ]
        for stream in res:
            # Once all demo streams are created, we start creating default stream posts for new streams.
            if all(stream for stream in demo_streams):
                stream._add_default_stream_posts()
        return res

    def _add_default_stream_posts(self):
        """ When adding a stream, we create some fake stream.posts for demo purposes. """

        res_partner_10 = self.env.ref('social_demo.res_partner_10', raise_if_not_found=False)
        author_image = ('/web/image/res.partner/%s/avatar_128' % res_partner_10.id) if res_partner_10 else ''

        for stream in self:
            if stream.twitter_followed_account_id:
                author_name = stream.twitter_followed_account_id.name
            elif stream.media_id == self.env.ref('social_twitter.social_media_twitter', raise_if_not_found=False):
                author_name = 'Twitter Account'
            elif stream.media_id == self.env.ref('social_facebook.social_media_facebook', raise_if_not_found=False):
                author_name = 'My Page'
            else:
                author_name = 'My Company'

            message_suffix = stream.twitter_searched_keyword or ''

            self.env['social.stream.post'].create([{
                'stream_id': stream.id,
                'author_name': author_name,
                'twitter_profile_image_url': author_image,
                'facebook_comments_count': random.randint(100, 300),
                'published_date': datetime.datetime.now() - datetime.timedelta(minutes=45),
                'message': 'Oldest message %s' % message_suffix
            }, {
                'stream_id': stream.id,
                'author_name': author_name,
                'twitter_profile_image_url': author_image,
                'facebook_comments_count': random.randint(100, 300),
                'published_date': datetime.datetime.now() - datetime.timedelta(minutes=30),
                'message': 'Middle message %s' % message_suffix
            }, {
                'stream_id': stream.id,
                'author_name': author_name,
                'twitter_profile_image_url': author_image,
                'facebook_comments_count': random.randint(100, 300),
                'published_date': datetime.datetime.now() - datetime.timedelta(minutes=15),
                'message': 'Newest message %s' % message_suffix
            }])

    def _fetch_stream_data(self):
        """ Overridden to bypass third-party API calls. """
        return False
