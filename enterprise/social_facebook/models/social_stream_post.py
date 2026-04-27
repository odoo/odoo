# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.parser
import logging
import requests
import urllib.parse


from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.social_facebook.models.social_stream import SocialStreamFacebook
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)


class SocialStreamPostFacebook(models.Model):
    _inherit = 'social.stream.post'

    FACEBOOK_COMMENT_FIELDS = f'id,from.fields(id,name,picture),message,message_tags,created_time,attachment,comments.fields(id,from.fields(id,name,picture),message,created_time,attachment,user_likes,like_count,{SocialStreamFacebook.FACEBOOK_REACTIONS_FIELDS}),user_likes,like_count,{SocialStreamFacebook.FACEBOOK_REACTIONS_FIELDS}'

    facebook_post_id = fields.Char('Facebook Post ID', index=True)
    facebook_author_id = fields.Char('Facebook Author ID')
    facebook_likes_count = fields.Integer('Likes')
    facebook_reactions_count = fields.Char('Reactions Count')  # contains a JSON like {"LIKE": 1337, "CARE": 1234}
    facebook_user_likes = fields.Boolean('User Likes')
    facebook_comments_count = fields.Integer('Comments')
    facebook_shares_count = fields.Integer('Shares')
    facebook_reach = fields.Integer('Reach')

    facebook_is_event_post = fields.Boolean('Is event post')

    def _compute_author_link(self):
        facebook_posts = self._filter_by_media_types(['facebook'])
        super(SocialStreamPostFacebook, (self - facebook_posts))._compute_author_link()

        for post in facebook_posts:
            post.author_link = '/social_facebook/redirect_to_profile/%s/%s?name=%s' % (post.account_id.id, post.facebook_author_id, urllib.parse.quote(post.author_name))

    def _compute_post_link(self):
        facebook_posts = self._filter_by_media_types(['facebook'])
        super(SocialStreamPostFacebook, (self - facebook_posts))._compute_post_link()

        for post in facebook_posts:
            post.post_link = 'https://www.facebook.com/%s' % post.facebook_post_id

    def _compute_is_author(self):
        facebook_posts = self._filter_by_media_types(['facebook'])
        super(SocialStreamPostFacebook, (self - facebook_posts))._compute_is_author()

        for post in facebook_posts:
            post.is_author = post.facebook_author_id == post.account_id.facebook_account_id

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _facebook_comment_delete(self, comment_id):
        requests.delete(url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, comment_id),
            data={'access_token': self.stream_id.account_id.facebook_access_token},
            timeout=5
        )

        return True

    def _facebook_comment_fetch(self, next_records_token=False, count=20):
        self.ensure_one()

        comments_endpoint_url = url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/comments" % self.facebook_post_id)
        params = {
            'fields': self.FACEBOOK_COMMENT_FIELDS,
            'access_token': self.stream_id.account_id.facebook_access_token,
            'summary': 1,
            'limit': count,
            'order': 'reverse_chronological'
        }
        if next_records_token:
            params['after'] = next_records_token

        result = requests.get(comments_endpoint_url, params)
        result_json = result.json()

        if not result.ok:
            _logger.warning("An error occurred while fetching the comment: %s", result.text)

            error_message = _('An error occurred.')

            if result_json.get('error'):
                error_code = result_json['error'].get('code')
                error_subcode = result_json['error'].get('error_subcode')
                if error_code == 100 and error_subcode == 33:
                    error_message = _("Post not found. It could be because the post has been deleted on the Social Platform.")

            raise UserError(error_message)

        for comment in result_json.get('data'):
            comment.update(self._format_facebook_comment(comment))

            inner_comments = comment.get('comments', {}).get('data') or []

            if not inner_comments:
                comment['comments'] = {'data': []}
            for inner_comment in inner_comments:
                inner_comment.update(self._format_facebook_comment(inner_comment))

        return {
            'comments': result_json.get('data'),
            'summary': result_json.get('summary'),
            'nextRecordsToken': result_json.get('paging').get('cursors').get('after') if result_json.get('paging') else None
        }

    def _facebook_comment_post(self, endpoint_url, message, existing_attachment_id=None, attachment=None):
        params = {
            'message': message,
            'access_token': self.stream_id.account_id.facebook_access_token,
            # The response received from the post request to post the comment
            # does not return all the fields mentioned here.
            'fields': self.FACEBOOK_COMMENT_FIELDS
        }

        if existing_attachment_id:
            params.update({'attachment_id': existing_attachment_id})

        extracted_url = self.env['social.post']._extract_url_from_message(message)
        # can't combine with images
        if extracted_url and not attachment and not existing_attachment_id:
            params.update({'link': extracted_url})

        result = requests.post(
            endpoint_url,
            data=params,
            files={'source': ('source', attachment.read(), attachment.content_type)} if attachment else None,
            timeout=15  # can take some time if there are attached images to upload
        ).json()
        result['likes'] = {'summary': {'total_count': result.get('like_count', 0)}}

        inner_comments = result.get('comments', {}).get('data', [])
        for inner_comment in inner_comments:
            inner_comment['likes'] = {'summary': {'total_count': inner_comment.get('like_count', 0)}}

        result.setdefault('comments', {'data': []})
        return result

    def _facebook_like(self, object_id, like):
        params = {'access_token': self.stream_id.account_id.facebook_access_token}
        comments_like_endpoint_url = url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/likes" % (object_id))
        if like:
            requests.post(comments_like_endpoint_url, data=params, timeout=5)
        else:
            requests.delete(comments_like_endpoint_url, data=params)

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    @api.model
    def _format_facebook_published_date(self, comment):
        return self.env['social.stream.post']._format_published_date(
            dateutil.parser.parse(comment.get('created_time'), ignoretz=True)
        )

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'facebook' and self.facebook_post_id:
            return self.env['social.live.post'].search(
                [('facebook_post_id', '=', self.facebook_post_id)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostFacebook, self)._fetch_matching_post()

    def _format_facebook_comment(self, comment):
        """Modify `comment` for the web client."""
        comment = {
            **comment,
            # overwrite comment keys
            'formatted_created_time': self._format_facebook_published_date(comment),
            'message': self.stream_id._format_facebook_message(comment.get('message'), comment.get('message_tags')),
            'reactions': {
                reaction: comment.get(reaction, {}).get('summary', {}).get('total_count', 0)
                for reaction in self.env['social.stream'].FACEBOOK_REACTIONS
            }
        }
        if "from" not in comment:
            comment["from"] = {"name": _("Unknown")}
        if comment.get('attachment', {}).get('type') == 'sticker':
            # stickers are just image
            comment['attachment']['type'] = 'photo'
        return comment
