# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
import re
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)


class SocialLivePostTwitter(models.Model):
    _inherit = 'social.live.post'

    twitter_tweet_id = fields.Char('X post id')

    def _compute_live_post_link(self):
        twitter_live_posts = self._filter_by_media_types(['twitter']).filtered(
            lambda post: post.state == 'posted' and post.account_id.twitter_user_id
        )
        super(SocialLivePostTwitter, (self - twitter_live_posts))._compute_live_post_link()

        for post in twitter_live_posts:
            post.live_post_link = 'https://www.twitter.com/%s/statuses/%s' % (
                post.account_id.twitter_user_id, post.twitter_tweet_id
            )

    def _refresh_statistics(self):
        super()._refresh_statistics()
        accounts = self.env['social.account'].search([('media_type', '=', 'twitter')])
        for account in accounts:
            existing_live_posts = self.env['social.live.post'].sudo().search(
                [('account_id', '=', account.id), ('twitter_tweet_id', '!=', False)],
                order='create_date DESC', limit=100)

            if not existing_live_posts:
                continue

            tweets_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, '/2/tweets')
            query_params = {
                'ids': ','.join(existing_live_posts.mapped('twitter_tweet_id')),
                'tweet.fields': 'public_metrics',
            }
            headers = account._get_twitter_oauth_header(
                tweets_endpoint_url,
                params=query_params,
                method='GET'
            )
            result = requests.get(
                tweets_endpoint_url,
                params=query_params,
                headers=headers,
                timeout=5
            )
            if not result.ok:
                _logger.warning('Failed to fetch the account (%i) metrics: %r.', account.id, result.text)

            result_tweets = result.json().get('data', [])
            if isinstance(result_tweets, dict) and result_tweets.get('errors'):
                account._action_disconnect_accounts(result_tweets)
                return

            existing_live_posts_by_tweet_id = {
                live_post.twitter_tweet_id: live_post for live_post in existing_live_posts
            }

            for tweet in result_tweets:
                existing_live_post = existing_live_posts_by_tweet_id.get(tweet.get('id'))
                if existing_live_post:
                    public_metrics = tweet.get('public_metrics', {})
                    likes_count = public_metrics.get('like_count', 0)
                    retweets_count = public_metrics.get('retweet_count', 0)
                    existing_live_post.engagement = likes_count + retweets_count

    def _post(self):
        twitter_live_posts = self._filter_by_media_types(['twitter'])
        super(SocialLivePostTwitter, (self - twitter_live_posts))._post()

        twitter_live_posts._post_twitter()

    def _post_twitter(self):
        post_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, '/2/tweets')

        for live_post in self:
            account = live_post.account_id

            params = {
                'text': live_post.message,
            }

            try:
                images_attachments_ids = account._format_attachments_to_images_twitter(live_post.image_ids)
            except UserError as e:
                live_post.write({
                    'state': 'failed',
                    'failure_reason': str(e)
                })
                continue
            if images_attachments_ids:
                params['media'] = {'media_ids': images_attachments_ids}

            headers = account._get_twitter_oauth_header(post_endpoint_url)
            result = requests.post(
                post_endpoint_url,
                json=params,
                headers=headers,
                timeout=5
            )

            if result.ok:
                live_post.twitter_tweet_id = result.json()['data']['id']
                values = {
                    'state': 'posted',
                    'failure_reason': False
                }
            else:
                values = {
                    'state': 'failed',
                    'failure_reason': result.text
                }

            live_post.write(values)

    @api.model
    def _remove_mentions(self, message, ignore_mentions=None):
        """Remove mentions in the Tweet message.

        :param message: text message in which we will look for mention
        :param ignore_mentions: do not remove those mentions if found
        """
        if not ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param(
           'social_twitter.disable_mentions', 'False')):
            return message

        if ignore_mentions:
            # keep only safe (mention consistent) chars in `ignore_mention`
            ignore_mentions = [
                re.sub(r'[^\w]', '', mention).lower()
                for mention in ignore_mentions
            ]

        mention_regex = r'(^|[^\w#])@(%s)\b'

        remove_mentions = [
            match[2] for match in re.finditer(mention_regex % r'\w+', message)
            if not ignore_mentions or match[2].lower() not in ignore_mentions
        ]

        for mention in remove_mentions:
            message = re.sub(mention_regex % mention, r'\1@ \2', message)
        return message
