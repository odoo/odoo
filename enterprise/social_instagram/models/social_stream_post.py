# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.parser
import requests

from werkzeug.urls import url_join, url_quote

from odoo import fields, models, _


class SocialStreamPostInstagram(models.Model):
    _inherit = 'social.stream.post'

    instagram_facebook_author_id = fields.Char('Instagram Facebook Author ID',
        help="The Facebook ID of this Instagram post author, used to fetch the profile picture.")
    instagram_post_id = fields.Char('Instagram Post ID', index=True)
    instagram_comments_count = fields.Integer('Instagram Comments')
    instagram_likes_count = fields.Integer('Instagram Likes')
    instagram_post_link = fields.Char('Instagram Post URL')

    def _compute_post_link(self):
        """ The posts links for instagram cannot be inferred from the ID.
        We have to store the URL that we got when fetching the instagram posts. """
        instagram_posts = self._filter_by_media_types(['instagram'])

        super(SocialStreamPostInstagram, (self - instagram_posts))._compute_post_link()

        for post in instagram_posts:
            post.post_link = post.instagram_post_link or False

    def _compute_author_link(self):
        instagram_posts = self._filter_by_media_types(['instagram'])

        super(SocialStreamPostInstagram, (self - instagram_posts))._compute_author_link()

        for post in instagram_posts:
            post.author_link = 'https://www.instagram.com/%s' % url_quote(post.author_name)

    def _compute_is_author(self):
        instagram_posts = self._filter_by_media_types(['instagram'])
        super(SocialStreamPostInstagram, (self - instagram_posts))._compute_is_author()

        for post in instagram_posts:
            post.is_author = post.instagram_facebook_author_id == post.account_id.instagram_facebook_account_id

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _instagram_comment_add(self, message, object_id, comment_type="comment"):
        """ Publishes a comment on an Instagram stream post or on another comment.
        We specify a 'fields' parameter to retrieve information about the created comment
        and return the data to display a properly formatted comment in the frontend.  """

        self.ensure_one()

        comment_endpoint = url_join(
            self.env['social.media']._INSTAGRAM_ENDPOINT,
            '%s/%s' % (object_id, 'replies' if comment_type == 'reply' else 'comments'))
        response = requests.post(comment_endpoint,
            params={
                'access_token': self.account_id.instagram_access_token,
                'message': message,
                'fields': 'id,like_count,text,timestamp,username,user',
                'order': 'reverse'
            },
            timeout=5
        )
        response_json = response.json()
        if not response.ok or 'error' in response_json:
            return {
                'error': _('Please confirm that commenting is enabled for this post on the platform.')
            }
        return self._instagram_format_comment(response_json)

    def _instagram_comment_fetch(self, next_records_token=False, count=20):
        """ Returns users comments on an Instagram social.stream.post.
        This method supports pagination through the 'next_records_token' parameter. """
        self.ensure_one()

        comments_endpoint = url_join(
            self.env['social.media']._INSTAGRAM_ENDPOINT,
            '/v17.0/%s/comments' % self.instagram_post_id)

        params = {
            'access_token': self.account_id.instagram_access_token,
            'fields': 'id,like_count,text,timestamp,username,replies{like_count,text,timestamp,username},user',
            'summary': 1,
            'limit': count
        }
        if next_records_token:
            params['after'] = next_records_token

        response = requests.get(comments_endpoint, params=params, timeout=5).json()
        return {
            'comments': [self._instagram_format_comment(comment) for comment in response.get('data', [])],
            'nextRecordsToken': response.get('paging').get('cursors').get('after') if response.get('paging') else None
        }

    def _instagram_comment_delete(self, comment_id):
        self.ensure_one()
        comments_endpoint_url = url_join(self.env['social.media']._INSTAGRAM_ENDPOINT, "/v17.0/%s" % comment_id)
        requests.delete(comments_endpoint_url, data={
            'access_token': self.account_id.instagram_access_token,
        })

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'instagram' and self.instagram_post_id:
            return self.env['social.live.post'].search(
                [('instagram_post_id', '=', self.instagram_post_id)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostInstagram, self)._fetch_matching_post()

    def _instagram_format_comment(self, comment):
        return {
            'id': comment.get('id'),
            'from': {
                'name': comment.get('username'),
                'id': comment.get('user').get('id')
                if 'user' in comment else -1,
            },
            'message': comment.get('text'),
            'created_time': comment.get('timestamp'),
            'formatted_created_time': self.env['social.stream.post']._format_published_date(fields.Datetime.from_string(
                dateutil.parser.parse(comment.get('timestamp')).strftime('%Y-%m-%d %H:%M:%S')
            )),
            'likes': {
                'summary': {
                    'total_count': comment.get('like_count')
                }
            },
            'user_likes': comment.get('user_likes'),
            'comments': {
                # Small trick for the comment answers, we reverse the list to have it in the
                # desired order (chronological).
                'data': [self._instagram_format_comment(comment) for comment in comment['replies'].get('data', [])][::-1]
            } if comment.get('replies') else {'data': []}
        }
