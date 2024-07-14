# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import logging
import requests

from odoo import _, api, models, fields
from odoo.exceptions import UserError
from odoo.http import request
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)


class SocialStreamPostTwitter(models.Model):
    _inherit = 'social.stream.post'

    twitter_tweet_id = fields.Char('Twitter Tweet ID', index=True)
    twitter_conversation_id = fields.Char('Twitter Conversation ID')
    twitter_author_id = fields.Char('Twitter Author ID')
    twitter_screen_name = fields.Char('Twitter Screen Name')
    twitter_profile_image_url = fields.Char('Twitter Profile Image URL')
    twitter_likes_count = fields.Integer('Twitter Likes')
    twitter_user_likes = fields.Boolean('Twitter User Likes')
    twitter_comments_count = fields.Integer('Twitter Comments')
    twitter_retweet_count = fields.Integer('Re-tweets')

    twitter_retweeted_tweet_id_str = fields.Char('Twitter Retweet ID')
    twitter_can_retweet = fields.Boolean(compute='_compute_twitter_can_retweet')
    twitter_quoted_tweet_id_str = fields.Char('Twitter Quoted Tweet ID')
    twitter_quoted_tweet_message = fields.Text('Quoted tweet message')
    twitter_quoted_tweet_author_name = fields.Char('Quoted tweet author Name')
    twitter_quoted_tweet_author_link = fields.Char('Quoted tweet author Link')
    twitter_quoted_tweet_profile_image_url = fields.Char('Quoted tweet profile image URL')

    _sql_constraints = [
        ('tweet_uniq', 'UNIQUE (twitter_tweet_id, stream_id)', 'You can not store two times the same tweet on the same stream!')
    ]

    def _compute_author_link(self):
        twitter_posts = self._filter_by_media_types(['twitter'])
        super(SocialStreamPostTwitter, (self - twitter_posts))._compute_author_link()

        for post in twitter_posts:
            post.author_link = 'https://twitter.com/intent/user?user_id=%s' % post.twitter_author_id

    def _compute_post_link(self):
        twitter_posts = self._filter_by_media_types(['twitter'])
        super(SocialStreamPostTwitter, (self - twitter_posts))._compute_post_link()

        for post in twitter_posts:
            post.post_link = 'https://www.twitter.com/%s/statuses/%s' % (post.twitter_author_id, post.twitter_tweet_id)

    @api.depends('twitter_retweeted_tweet_id_str', 'twitter_tweet_id')
    def _compute_twitter_can_retweet(self):
        tweets = self.filtered(lambda post: post.twitter_tweet_id)
        (self - tweets).twitter_can_retweet = False
        if not tweets:
            return

        tweet_ids = set(tweets.mapped('twitter_tweet_id')) | set(tweets.mapped('twitter_retweeted_tweet_id_str'))
        twitter_author_ids = set(tweets.stream_id.account_id.mapped('twitter_user_id'))

        potential_retweets = self.search([
            ('twitter_author_id', 'in', list(twitter_author_ids)),
            '|',
                ('twitter_tweet_id', 'in', list(tweet_ids)),
                ('twitter_retweeted_tweet_id_str', 'in', list(tweet_ids)),
        ])

        for tweet in tweets:
            account = tweet.stream_id.account_id
            if tweet.twitter_retweeted_tweet_id_str and tweet.twitter_author_id == account.twitter_user_id:
                # If the tweet is a retweet and has been posted with the given account, the user will not
                # be allowed to retweet the tweet.
                tweet.twitter_can_retweet = False
                continue
            # Otherwise, the user will be allowed to retweet the tweet if there does not exist a retweet
            # of that tweet posted with the given account.
            original_tweet_id = tweet.twitter_retweeted_tweet_id_str or tweet.twitter_tweet_id
            tweet.twitter_can_retweet = not any(
                current.twitter_retweeted_tweet_id_str == original_tweet_id and \
                current.twitter_author_id == account.twitter_user_id for current in potential_retweets
            )

    def _compute_is_author(self):
        twitter_posts = self._filter_by_media_types(['twitter'])
        super(SocialStreamPostTwitter, (self - twitter_posts))._compute_is_author()

        for post in twitter_posts:
            post.is_author = post.twitter_author_id == post.account_id.twitter_user_id

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _twitter_comment_add(self, stream, comment_id, message, attachment):
        """Create a reply to a tweet."""
        self.ensure_one()
        tweet_id = comment_id or self.twitter_tweet_id
        tweet = self._twitter_post_tweet(stream, message, attachment, reply={'in_reply_to_tweet_id': tweet_id})
        tweet['in_reply_to_tweet_id'] = tweet_id
        return tweet

    def _twitter_comment_fetch(self, page=1):
        """Find the tweets in the same thread, but after the current one.

        All tweets have a `conversation_id` field, which correspond to the first tweet
        in the same thread. "comments" do not really exist in Twitter, so we take all
        the tweet in the same thread (same `conversation_id`), after the current one.

        https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
        """
        self.ensure_one()

        if not self.twitter_conversation_id:
            raise UserError(_('This tweet is outdated, please refresh the stream and try again.'))

        endpoint_url = url_join(self.env['social.media']._TWITTER_ENDPOINT, '/2/tweets/search/recent')
        query_params = {
            'query': f'conversation_id:{self.twitter_conversation_id}',
            'since_id': self.twitter_tweet_id,
            'max_results': 100,
            'tweet.fields': 'conversation_id,created_at,public_metrics,referenced_tweets',
            'expansions': 'author_id,attachments.media_keys',
            'user.fields': 'id,name,username,profile_image_url',
            'media.fields': 'type,url,preview_image_url',
        }

        headers = self.stream_id.account_id._get_twitter_oauth_header(
            endpoint_url,
            params=query_params,
            method='GET',
        )
        result = requests.get(
            endpoint_url,
            params=query_params,
            headers=headers,
            timeout=10,
        )
        if not result.ok:
            if result.json().get('errors', [{}])[0].get('parameters', {}).get('since_id'):
                raise UserError(_("Replies from Tweets older than 7 days must be accessed on Twitter.com"))
            raise UserError(_("Failed to fetch the tweets in the same thread: '%s' using the account %s.", result.text, self.stream_id.account_id.name))

        users = {
            user['id']: {
                **user,
                'profile_image_url': user.get('profile_image_url'),
            }
            for user in result.json().get('includes', {}).get('users', [])
        }

        medias = {
            media['media_key']: media
            for media in result.json().get('includes', {}).get('media', [])
        }

        return {
            'comments': [
                self.env['social.media']._format_tweet({
                    **tweet,
                    'author': users.get(tweet.get('author_id'), {}),
                    'medias': [
                        medias.get(media)
                        for media in tweet.get('attachments', {}).get('media_keys', [])
                    ],
                })
                for tweet in result.json().get('data', [])
            ],
            'is_reply_limited': ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param(
                'social_twitter.enable_reply_limit', 'False'))
        }

    def _twitter_tweet_delete(self, tweet_id):
        self.ensure_one()
        delete_endpoint = url_join(
            self.env['social.media']._TWITTER_ENDPOINT,
            '/2/tweets/%s' % tweet_id)
        headers = self.stream_id.account_id._get_twitter_oauth_header(
            delete_endpoint,
            method='DELETE',
        )
        response = requests.delete(
            delete_endpoint,
            headers=headers,
            timeout=5
        )
        if not response.ok:
            raise UserError(_('Failed to delete the Tweet\n%s.', response.text))

        return True

    def _twitter_tweet_like(self, stream, tweet_id, like):
        if like:
            endpoint = url_join(
                request.env['social.media']._TWITTER_ENDPOINT,
                '/2/users/%s/likes' % stream.account_id.twitter_user_id)
            headers = stream.account_id._get_twitter_oauth_header(endpoint)
            result = requests.post(
                endpoint,
                json={'tweet_id': tweet_id},
                headers=headers,
                timeout=5,
            )
        else:
            endpoint = url_join(
                request.env['social.media']._TWITTER_ENDPOINT,
                '/2/users/%s/likes/%s' % (stream.account_id.twitter_user_id, tweet_id))
            headers = stream.account_id._get_twitter_oauth_header(endpoint, method='DELETE')
            result = requests.delete(endpoint, headers=headers, timeout=10)

        if not result.ok:
            raise UserError(_('Can not like / unlike the tweet\n%s.', result.text))

        post = request.env['social.stream.post'].search([('twitter_tweet_id', '=', tweet_id)])
        if post:
            post.twitter_user_likes = like

        return True

    def _twitter_do_retweet(self):
        """ Creates a new retweet for the given stream post on Twitter. """
        if not self.twitter_can_retweet:
            raise UserError(_('A retweet already exists'))

        account = self.stream_id.account_id
        retweet_endpoint = url_join(self.env['social.media']._TWITTER_ENDPOINT, '/2/users/%s/retweets' % account.twitter_user_id)

        headers = account._get_twitter_oauth_header(retweet_endpoint)
        result = requests.post(retweet_endpoint, headers=headers, json={'tweet_id': self.twitter_tweet_id}, timeout=5)

        if result.ok: # 200-series HTTP code
            return True
        elif result.status_code == 401:
            account.write({'is_media_disconnected': True})
            raise UserError(_('You are not authenticated'))

        error = result.json().get('detail')
        if error:
            raise UserError(error)
        raise UserError(_('Unknown error'))

    def _twitter_undo_retweet(self):
        """ Deletes the retweet of the given stream post from Twitter """
        tweet_id = self.twitter_retweeted_tweet_id_str or self.twitter_tweet_id
        account = self.stream_id.account_id
        unretweet_endpoint = url_join(
            self.env['social.media']._TWITTER_ENDPOINT,
            '/2/users/%s/retweets/%s' % (account.twitter_user_id, tweet_id),
        )

        headers = account._get_twitter_oauth_header(unretweet_endpoint, method='DELETE')
        result = requests.delete(unretweet_endpoint, headers=headers, timeout=5)

        if result.status_code == 401:
            account.write({'is_media_disconnected': True})
            raise UserError(_('You are not authenticated'))

        if not result.ok or result.json().get('data', {}).get('retweeted') is not False:
            error = result.json().get('detail')
            if error:
                raise UserError(error)
            raise UserError(_('Unknown error'))

        retweets = self.search([
            ('twitter_author_id', '=', self.stream_id.account_id.twitter_user_id),
            ('twitter_retweeted_tweet_id_str', '=', tweet_id),
        ])
        retweets.unlink()
        return True

    def _twitter_tweet_quote(self, message, attachment):
        """
        :param werkzeug.datastructures.FileStorage attachment:
        Creates a new quotes for the current stream post on Twitter.
        If the stream post does not have any message, a retweet will be created instead of a quote.
        """
        self.ensure_one()
        if not message and not attachment:
            return self._twitter_do_retweet()
        self._twitter_post_tweet(self.stream_id, message, attachment, quote_tweet_id=self.twitter_tweet_id)
        return True

    # ========================================================
    # UTILITY / MISC
    # ========================================================

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'twitter' and self.twitter_tweet_id:
            return self.env['social.live.post'].search(
                [('twitter_tweet_id', '=', self.twitter_tweet_id)], limit=1
            ).post_id
        return super()._fetch_matching_post()

    def _twitter_post_tweet(self, stream, message, attachment, **additionnal_params):
        data = {
            'text': message,
            **additionnal_params,
        }

        images_attachments_ids = None
        if attachment:
            bytes_data = attachment.read()
            images_attachments_ids = stream.account_id._format_images_twitter([{
                'bytes': bytes_data,
                'file_size': len(bytes_data),
                'mimetype': attachment.content_type,
            }])
            if images_attachments_ids:
                data['media'] = {'media_ids': images_attachments_ids}

        post_endpoint_url = url_join(request.env['social.media']._TWITTER_ENDPOINT, '/2/tweets')
        headers = stream.account_id._get_twitter_oauth_header(post_endpoint_url)
        result = requests.post(
            post_endpoint_url,
            json=data,
            headers=headers,
            timeout=5
        )

        if not result.ok:
            stream.account_id.write({'is_media_disconnected': True})
            error = result.json().get('detail') or result.text
            raise UserError(_('Failed to post comment: %s with the account %s.', error, stream.account_id.name))

        tweet = result.json()['data']

        # we can not use fields expansion when creating a tweet,
        # so we fill manually the missing values to not recall the API
        tweet.update({
            'author_id': self.account_id.twitter_user_id,
            'author': {
                'id': self.account_id.twitter_user_id,
                'name': self.account_id.name,
                'username': self.account_id.social_account_handle,
                'profile_image_url': '/web/image/social.account/%s/image' % stream.account_id.id,
            },
            **additionnal_params,
        })
        if images_attachments_ids:
            # the image didn't create an attachment, and it will require an extra
            # API call to get the URL, so we just base 64 encode the image data
            b64_image = base64.b64encode(bytes_data).decode()
            link = "data:%s;base64,%s" % (attachment.content_type, b64_image)
            tweet['medias'] = [{'url': link, 'type': 'photo'}]

        return request.env['social.media']._format_tweet(tweet)
