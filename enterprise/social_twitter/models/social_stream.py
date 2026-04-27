# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.parser
import logging
import requests
from html import unescape

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)


class SocialStreamTwitter(models.Model):
    _inherit = 'social.stream'

    twitter_searched_keyword = fields.Char('Search Keyword')
    twitter_followed_account_search = fields.Char('Search User')
    # TODO awa: clean unused 'social.twitter.account' in a cron job
    twitter_followed_account_id = fields.Many2one('social.twitter.account')

    @api.constrains('stream_type_id', 'twitter_followed_account_id')
    def _check_twitter_followed_account_id(self):
        if any(
            stream.stream_type_id.stream_type in ('twitter_follow', 'twitter_likes')
            and not stream.twitter_followed_account_id
            for stream in self
        ):
            raise UserError(_("Please select a X account for this stream type."))

    def _apply_default_name(self):
        twitter_streams = self.filtered(lambda s: s.media_id.media_type == 'twitter')
        super(SocialStreamTwitter, (self - twitter_streams))._apply_default_name()

        for stream in twitter_streams:
            name = False
            if stream.stream_type_id.stream_type in ['twitter_follow', 'twitter_likes'] and stream.twitter_followed_account_id:
                name = '%s: %s' % (stream.stream_type_id.name, stream.twitter_followed_account_id.name)
            elif stream.stream_type_id.stream_type == 'twitter_user_mentions' and stream.account_id:
                name = '%s: %s' % (stream.stream_type_id.name, stream.account_id.name)
            elif stream.stream_type_id.stream_type == 'twitter_keyword' and stream.twitter_searched_keyword:
                name = '%s: %s' % (stream.stream_type_id.name, stream.twitter_searched_keyword)

            if name:
                stream.write({'name': name})

    def _fetch_stream_data(self):
        if self.media_id.media_type != 'twitter':
            return super()._fetch_stream_data()

        if self.stream_type_id.stream_type == 'twitter_user_mentions':
            return self._fetch_tweets('/2/users/%s/mentions' % self.account_id.twitter_user_id)
        if self.stream_type_id.stream_type == 'twitter_follow':
            return self._fetch_tweets('/2/users/%s/tweets' % self.twitter_followed_account_id.twitter_id)
        if self.stream_type_id.stream_type == 'twitter_likes':
            return self._fetch_tweets('/2/users/%s/liked_tweets' % self.twitter_followed_account_id.twitter_id)
        if self.stream_type_id.stream_type == 'twitter_keyword':
            keyword = self.twitter_searched_keyword
            if not keyword.startswith("#"):
                keyword = "#%s" % keyword
            return self._fetch_tweets('/2/tweets/search/recent', {'query': keyword + ' -is:retweet'})

    def _fetch_tweets(self, endpoint_name, extra_params={}):
        self.ensure_one()
        query_params = {
            'max_results': 100,
            'tweet.fields': 'created_at,public_metrics,referenced_tweets,conversation_id',
            'expansions': 'author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id',
            'user.fields': 'id,name,username,profile_image_url',
            'media.fields': 'type,url,preview_image_url',
        }
        query_params.update(extra_params)
        tweets_endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, endpoint_name)
        # TODO awa: check the "TE" header (Transfer-Encoding) to get a (smaller) gzip response
        headers = self.account_id._get_twitter_oauth_header(
            tweets_endpoint_url,
            params=query_params,
            method='GET',
        )
        response = requests.get(
            tweets_endpoint_url,
            query_params,
            headers=headers,
            timeout=5
        )
        result = response.json()

        if not response.ok:
            _logger.warning('Failed to fetch social stream posts: %r for account %i.', response.text, self.account_id.id)
            # an error occurred
            if 'Not authorized' in result.get('title', ''):
                # no error code is returned by the Twitter API in that case
                # it's probably because the Twitter account we tried to add
                # is private
                error_message = _(
                    "You cannot create a Stream from this X account.\n"
                    "It may be because it's protected. To solve this, please make sure you follow it before trying again."
                )
            elif response.status_code == 400 and result.get('errors', [{}])[0].get('parameters', {}).get('query'):
                # invalid query
                error_message = _("The keyword you've typed in does not look valid. Please try again with other words.")
            else:
                error_code = result.get('status')
                error_message = result.get('title')
                ERROR_MESSAGES = {
                    429: _("Looks like you've made too many requests. Please wait a few minutes before giving it another try."),
                }
                error_message = ERROR_MESSAGES.get(error_code, error_message)

            if error_message:
                raise UserError(error_message)

        if isinstance(result, dict) and not result.get('data') and result.get('errors') or result is None:
            self.account_id._action_disconnect_accounts(result)
            return False

        tweets_by_tweet_id = {
            tweet['id']: tweet
            for tweet in result.get('data', [])
        }

        existing_tweets = self.env['social.stream.post'].sudo().search([
            ('stream_id', '=', self.id),
            ('twitter_tweet_id', 'in', list(tweets_by_tweet_id)),
        ])
        existing_tweets_by_tweet_id = {
            tweet.twitter_tweet_id: tweet for tweet in existing_tweets
        }

        # TODO awa: handle deleted tweets ?
        tweets_to_create = []

        users_per_id = {
            user['id']: user
            for user in result.get('includes', {}).get('users', [])
        }
        medias_per_id = {
            media['media_key']: media
            for media in result.get('includes', {}).get('media', [])
        }

        quote_and_retweet_per_ids = {
            tweet.get('id'): tweet
            for tweet in result.get('includes', {}).get('tweets', [])
        }

        for twitter_tweet_id, tweet in tweets_by_tweet_id.items():
            public_metrics = tweet.get('public_metrics', {})
            user_info = users_per_id.get(tweet.get('author_id'), {})
            created_date = tweet.get('created_at')
            if created_date:
                created_date = fields.Datetime.from_string(dateutil.parser.parse(created_date).strftime('%Y-%m-%d %H:%M:%S'))
            values = {
                'stream_id': self.id,
                'message': unescape(tweet.get('text', '')),
                'author_name': user_info.get('name'),
                'published_date': created_date,
                'twitter_likes_count': public_metrics.get('like_count'),
                'twitter_retweet_count': public_metrics.get('retweet_count'),
                'twitter_tweet_id': twitter_tweet_id,
                'twitter_conversation_id': tweet.get('conversation_id'),
                'twitter_author_id': tweet.get('author_id'),
                'twitter_screen_name': user_info.get('username'),
                'twitter_profile_image_url': user_info.get('profile_image_url'),
            }

            # Handle quote and retweet
            referenced_tweets = tweet.get('referenced_tweets', [])
            if referenced_tweets and referenced_tweets[0]['type'] == 'retweeted':
                values['twitter_retweeted_tweet_id_str'] = referenced_tweets[0]['id']
            elif referenced_tweets and referenced_tweets[0]['type'] == 'quoted':
                quote = quote_and_retweet_per_ids.get(referenced_tweets[0]['id'], {})
                quote_author = users_per_id.get(quote.get('author_id'), {})

                values.update({
                    'twitter_quoted_tweet_id_str': quote.get('id'),
                    'twitter_quoted_tweet_message': quote.get('text', ''),
                    'twitter_quoted_tweet_author_name': quote_author.get('name', ''),
                    'twitter_quoted_tweet_profile_image_url': quote_author.get('profile_image_url', ''),
                })
                if quote_author.get('username'):
                    values['twitter_quoted_tweet_author_link'] = 'https://twitter.com/%s' % quote_author['username']

            retweets = list(filter(lambda ref: ref.get('type') == 'retweeted', referenced_tweets))
            if retweets:
                origin_tweet_msg = quote_and_retweet_per_ids.get(retweets[0].get('id'), {}).get('text')
                if origin_tweet_msg:
                    username = users_per_id[quote_and_retweet_per_ids.get(retweets[0].get('id'), {}).get('author_id')].get('username', _('Unknown'))
                    values['message'] = unescape(
                        f"RT @{username}: "
                        f"{origin_tweet_msg}"
                    )

            existing_tweet = existing_tweets_by_tweet_id.get(tweet.get('id'))
            if existing_tweet:
                existing_tweet.sudo().write(values)
            else:
                # attachments are only extracted for new posts
                values.update(self._extract_twitter_attachments(tweet, medias_per_id))
                tweets_to_create.append(values)

        stream_posts = self.env['social.stream.post'].sudo().create(tweets_to_create)
        return any(stream_post.stream_id.create_uid.id == self.env.uid for stream_post in stream_posts)

    @api.model
    def _extract_twitter_attachments(self, tweet, medias_per_id=None):
        if not medias_per_id:
            return {}
        medias = [
            medias_per_id[media]
            for media in tweet.get('attachments', {}).get('media_keys', [])
        ]
        images = [
            {'image_url': media['url']}
            for media in medias
            if media['type'] == 'photo'
        ]
        return {'stream_post_image_ids': [(0, 0, attachment) for attachment in images]} if images else {}
