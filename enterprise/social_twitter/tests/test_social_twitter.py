# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.addons.social_twitter.models.social_account import SocialAccountTwitter
from odoo.addons.social_twitter.models.social_stream import SocialStreamTwitter
from odoo.addons.social.tests.common import SocialCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('social_post_twitter')
class SocialTwitterCase(SocialCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(SocialAccountTwitter, '_compute_statistics', lambda x: None), \
                patch.object(SocialAccountTwitter, '_create_default_stream_twitter', lambda *args, **kwargs: None), \
                patch.object(SocialStreamTwitter, '_fetch_stream_data', lambda *args, **kwargs: None):
            super(SocialTwitterCase, cls).setUpClass()

            cls.social_accounts.write({
                'twitter_oauth_token_secret': 'ABCD'
            })
            cls.social_accounts[0].write({
                'twitter_user_id': '1234'
            })
            cls.social_accounts[1].write({
                'twitter_user_id': '5678'
            })

            cls.env['ir.config_parameter'].sudo().set_param(
                'social.twitter_consumer_key', 'key')
            cls.env['ir.config_parameter'].sudo().set_param(
                'social.twitter_consumer_secret_key', 'secret_key')

            cls.social_stream_type_1 = cls.env.ref(
                'social_twitter.stream_type_twitter_follow')
            cls.social_stream_type_2 = cls.env.ref(
                'social_twitter.stream_type_twitter_user_mentions')

            cls.social_twitter_account_1 = cls.env['social.twitter.account'].create({
                'name': 'Social X Account 1',
                'twitter_id': '1234'
            })
            cls.social_twitter_account_2 = cls.env['social.twitter.account'].create({
                'name': 'Social X Account 2',
                'twitter_id': '5678'
            })

            cls.social_stream_1 = cls.env['social.stream'].create({
                'name': 'Social Stream 1',
                'media_id': cls._get_social_media().id,
                'account_id': cls.social_accounts[0].id,
                'stream_type_id': cls.social_stream_type_1.id,
                'twitter_followed_account_id': cls.social_twitter_account_1.id
            })
            cls.social_stream_2 = cls.env['social.stream'].create({
                'name': 'Social Stream 2',
                'media_id': cls._get_social_media().id,
                'account_id': cls.social_accounts[1].id,
                'stream_type_id': cls.social_stream_type_2.id,
                'twitter_followed_account_id': cls.social_twitter_account_2.id
            })

    def test_post_success(self):
        self._test_post()

    def test_post_failure(self):
        self._test_post(False)

    def _test_post(self, success=True):
        self.assertEqual(self.social_post.state, 'draft')

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            if success:
                response._content = json.dumps({'data': {'id': '42'}}).encode('utf-8')
                response.status_code = 200
            else:
                response.status_code = 404
            return response

        with patch.object(SocialAccountTwitter, '_format_images_twitter', lambda *args, **kwargs: ['media1', 'media2']), \
             patch.object(requests, 'post', _patched_post):
                self.social_post._action_post()

        self._checkPostedStatus(success)

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_twitter.social_media_twitter')

    def test_can_retweet(self):
        account = self.social_stream_1.account_id
        tweet_1 = self.env['social.stream.post'].create({
            'message': 'Hello world',
            'media_type': 'twitter',
            'stream_id': self.social_stream_1.id,
            'twitter_author_id': account.twitter_user_id,
            'twitter_tweet_id': '1'
        })
        self.assertTrue(tweet_1.twitter_can_retweet)

        # When we retweet the tweet with the same account:
        retweet = self.env['social.stream.post'].create({
            'message': 'RT Hello world',
            'media_type': 'twitter',
            'stream_id': self.social_stream_1.id,
            'twitter_author_id': account.twitter_user_id,
            'twitter_tweet_id': '2',
            'twitter_retweeted_tweet_id_str': tweet_1.twitter_tweet_id
        })

        # We should not be able to retweet the tweet or the retweet with the same account:
        tweet_1.invalidate_recordset()
        self.assertFalse(tweet_1.twitter_can_retweet)
        self.assertFalse(retweet.twitter_can_retweet)

        # But if the same tweet appears in another stream:
        tweet_2 = self.env['social.stream.post'].create({
            'message': tweet_1.message,
            'media_type': tweet_1.media_type,
            'stream_id': self.social_stream_2.id,
            'twitter_author_id': tweet_1.twitter_author_id,
            'twitter_tweet_id': '1'
        })

        # We should be able to retweet it with the other account:
        tweet_1.invalidate_recordset()
        retweet.invalidate_recordset()
        self.assertFalse(tweet_1.twitter_can_retweet)
        self.assertFalse(retweet.twitter_can_retweet)
        self.assertTrue(tweet_2.twitter_can_retweet)

    def test_no_duplicated_tweets_in_stream(self):
        # There should not be duplicated tweets within a stream:
        account = self.social_stream_1.account_id
        tweet = self.env['social.stream.post'].create({
            'message': 'Hi there',
            'media_type': 'twitter',
            'stream_id': self.social_stream_1.id,
            'twitter_author_id': account.twitter_user_id,
            'twitter_tweet_id': '4'
        })

        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['social.stream.post'].create({
                    'message': tweet.message,
                    'media_type': tweet.media_type,
                    'stream_id': tweet.stream_id.id,
                    'twitter_author_id': tweet.twitter_author_id,
                    'twitter_tweet_id': tweet.twitter_tweet_id
                })

        # But, we can store the same tweet in another stream
        self.env['social.stream.post'].create({
            'message': tweet.message,
            'media_type': tweet.media_type,
            'stream_id': self.social_stream_2.id,
            'twitter_author_id': tweet.twitter_author_id,
            'twitter_tweet_id': tweet.twitter_tweet_id
        })

        tweets = self.env['social.stream.post'].search([
            ('twitter_tweet_id', '=', tweet.twitter_tweet_id)
        ])
        self.assertEqual(len(tweets), 2)

    def test_remove_mentions(self):
        self.env['ir.config_parameter'].set_param('social_twitter.disable_mentions', True)

        # without `ignore_mention` parameter
        assert_results = [
            ["@mister hello", "@ mister hello"],
            ["111@mister hello", "111@mister hello"],
            ["hello @mister", "hello @ mister"],
            ["hello@gmail.com hello @mister", "hello@gmail.com hello @ mister"],
            ["#@mister hello", "#@mister hello"],
            ["@aa @bb @cc", "@ aa @ bb @ cc"],
            ["@@test", "@@ test"],
            ['"@test"', '"@ test"'],
        ]
        for message, expected in assert_results:
            self.assertEqual(self.env["social.live.post"]._remove_mentions(message), expected)

        # with `ignore_mention` parameter
        assert_results = [
            ["@mister hello", ["mister"], "@mister hello"],
            ["@mister hello", ["MISTER"], "@mister hello"],
            ["@mistER hello", ["@MistEr"], "@mistER hello"],
            ["@ mister this_is_an_email@mister7f.com @kiwi", ["kiwi"], "@ mister this_is_an_email@mister7f.com @kiwi"],
            ["this_is_an_email@mister7f.com @mister @kiwi", ["kiwi"], "this_is_an_email@mister7f.com @ mister @kiwi"],
            ["@Mister hello @miste ", ["mister"], "@Mister hello @ miste "],
            ["@Mister hello @miste @TEST", ["mister", "test"], "@Mister hello @ miste @TEST"],
            # will remove `mister_kiwi_12` but must keep `mister_kiwi_123`
            ["special mention @mister_kiwi_123 @mister_kiwi_12", ["mister_kiwi_123"], "special mention @mister_kiwi_123 @ mister_kiwi_12"],
            ["@mister_kiwi_123 @mister_kiwi_12", ["mister_kiwi_123"], "@mister_kiwi_123 @ mister_kiwi_12"],
            ["@mister_kiwi_12 @mister_kiwi_123", ["mister_kiwi_123"], "@ mister_kiwi_12 @mister_kiwi_123"],
        ]
        for message, ignore, expected in assert_results:
            self.assertEqual(self.env["social.live.post"]._remove_mentions(message, ignore), expected)

    def test_tweet_post_message_counter(self):
        message_to_post = '''
            Odoo is a suite of business management software tools including,
            for example, CRM, e-commerce🛍, billing, accounting, manufacturing,
            warehouse, project management, and inventory management. The Community
            version is a libre software, licensed under the GNU LGPLv3. The Enterprise
            version has proprietary extra features and services. The source code for
            the framework and core ERP modules is curated by the Belgium-based Odoo S.A.
            Odoo is available for both on-premise and ready to use SaaS environment.
        '''
        social_media = self._get_social_media()
        social_post = self.env['social.post'].create({
            'message': message_to_post,
            'account_ids': self.social_stream_1.account_id,
        })
        counter_message = f'{len(message_to_post)} / {social_media.max_post_length} characters to fit in a Post'

        # When posting a message exceeding the Twitter limit (280 characters), verify that the
        # preview properly shows that we exceed the limit (with highlighted exceeding text).
        self.assertEqual(social_post.twitter_post_limit_message, counter_message)
        self.assertTrue('o_social_twitter_message_exceeding' in social_post.twitter_preview)

        with self.assertRaises(ValidationError):
            social_post.action_post()  # Should raise ValidationError when trying to post tweet having content exceeding the limit

        social_media.max_post_length = 0
        social_post._compute_twitter_post_limit_message()
        social_post._compute_twitter_preview()
        counter_message = f'{len(message_to_post)} / {social_media.max_post_length} characters to fit in a Post'

        self.assertEqual(social_post.twitter_post_limit_message, counter_message)
        # Preview should not have Exceed Content when Max content length is satisfied
        self.assertTrue('o_social_twitter_message_exceeding' not in social_post.twitter_preview)

        social_post.action_post()  # Should not raise ValidationError when trying to post tweet having proper content length
