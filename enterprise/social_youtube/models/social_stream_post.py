# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join


class SocialStreamPostYoutube(models.Model):
    _inherit = 'social.stream.post'

    youtube_video_id = fields.Char('YouTube Video ID', index=True)
    youtube_likes_count = fields.Integer('YouTube Likes')
    youtube_dislikes_count = fields.Integer('YouTube Dislikes')
    youtube_comments_count = fields.Integer('YouTube Comments Count')
    youtube_views_count = fields.Integer('YouTube Views')
    youtube_thumbnail_url = fields.Char('YouTube Thumbnail Url', compute="_compute_youtube_thumbnail_url")

    def _compute_author_link(self):
        youtube_posts = self._filter_by_media_types(['youtube'])
        super(SocialStreamPostYoutube, (self - youtube_posts))._compute_author_link()

        for post in youtube_posts:
            post.author_link = 'http://www.youtube.com/channel/%s' % (post.stream_id.account_id.youtube_channel_id)

    def _compute_post_link(self):
        youtube_posts = self._filter_by_media_types(['youtube'])
        super(SocialStreamPostYoutube, (self - youtube_posts))._compute_post_link()

        for post in youtube_posts:
            post.post_link = 'https://www.youtube.com/watch?v=%s' % post.youtube_video_id

    @api.depends('youtube_video_id')
    def _compute_youtube_thumbnail_url(self):
        for post in self:
            post.youtube_thumbnail_url = "http://i3.ytimg.com/vi/%s/hqdefault.jpg" % post.youtube_video_id

    def _compute_is_author(self):
        youtube_posts = self._filter_by_media_types(['youtube'])
        super(SocialStreamPostYoutube, (self - youtube_posts))._compute_is_author()
        youtube_posts.is_author = True

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _youtube_comment_add(self, comment_id, message, is_edit=False):
        self.ensure_one()
        self.account_id._refresh_youtube_token()

        common_params = {
            'access_token': self.account_id.youtube_access_token,
            'part': 'snippet',
        }

        if comment_id:
            if is_edit:
                # editing own comment
                result_comment = requests.put(
                    url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/comments"),
                    params=common_params,
                    json={
                        'id': comment_id,
                        'snippet': {
                            'textOriginal': message,
                        }
                    }
                ).json()
            else:
                # reply to comment, uses different endpoint that commenting a video
                result_comment = requests.post(
                    url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/comments"),
                    params=common_params,
                    json={
                        'snippet': {
                            'textOriginal': message,
                            'parentId': comment_id
                        }
                    },
                    timeout=5
                ).json()
        else:
            # brand new comment on the video
            result_comment = requests.post(
                url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/commentThreads"),
                params=common_params,
                json={
                    'snippet': {
                        'topLevelComment': {'snippet': {'textOriginal': message}},
                        'channelId': self.account_id.youtube_channel_id,
                        'videoId': self.youtube_video_id
                    },
                },
                timeout=5
            ).json().get('snippet', {}).get('topLevelComment')

        youtube_comment = self.env['social.media']._format_youtube_comment(result_comment)
        youtube_comment.setdefault('comments', {'data': []})
        return youtube_comment

    def _youtube_comment_delete(self, comment_id):
        self.ensure_one()
        self.account_id._refresh_youtube_token()

        response = requests.delete(
            url=url_join(self.env['social.media']._YOUTUBE_ENDPOINT, 'youtube/v3/comments'),
            params={
                'id': comment_id,
                'access_token': self.account_id.youtube_access_token,
            }
        )

        if not response.ok:
            self.account_id._action_disconnect_accounts(response.json())

    def _youtube_comment_fetch(self, next_page_token=False, count=20):
        self.ensure_one()
        self.stream_id.account_id._refresh_youtube_token()

        comments_endpoint_url = url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/commentThreads")
        params = {
            'part': 'snippet,replies',
            'textFormat': 'plainText',
            'access_token': self.stream_id.account_id.youtube_access_token,
            'videoId': self.youtube_video_id,
            'maxResults': count
        }

        if next_page_token:
            params['pageToken'] = next_page_token

        result = requests.get(comments_endpoint_url, params=params, timeout=5)
        result_json = result.json()

        if not result.ok:
            error_message = _('An error occurred.')

            if result_json.get('error'):
                error_code = result_json['error'].get('code')
                error_reason = result_json['error'].get('errors', [{}])[0].get('reason')
                if error_code == 404 and error_reason == 'videoNotFound':
                    error_message = _("Video not found. It could have been removed from Youtube.")
                elif error_code == 403 and error_reason == 'commentsDisabled':
                    error_message = _("Comments are marked as 'disabled' for this video. It could have been set as 'private'.")

            raise UserError(error_message)

        comments = []
        for comment in result_json.get('items', []):
            youtube_comment = self.env['social.media']._format_youtube_comment(
                comment.get('snippet').get('topLevelComment'))

            youtube_comment_replies = [
                self.env['social.media']._format_youtube_comment(reply)
                for reply in list(reversed(comment.get('replies', {}).get('comments', [])))]

            youtube_comment['comments'] = {
                'data': youtube_comment_replies if youtube_comment_replies else []
            }

            comments.append(youtube_comment)

        return {
            'comments': comments,
            'nextPageToken': result_json.get('nextPageToken')
        }

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'youtube' and self.youtube_video_id:
            return self.env['social.live.post'].search(
                [('youtube_video_id', '=', self.youtube_video_id)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostYoutube, self)._fetch_matching_post()

    @api.autovacuum
    def _gc_youtube_data(self):
        """ According to Youtube API terms of service, users Youtube data have to be removed
        if they have not been updated for more than 30 days.
        Ref: https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content
        (Section 4. "Refreshing, Storing, and Displaying API Data") """

        youtube_stream = self.env.ref('social_youtube.stream_type_youtube_channel_videos')
        self.env['social.stream.post'].sudo().search([
            ('stream_id.stream_type_id', '=', youtube_stream.id),
            ('write_date', '<', fields.Datetime.now() - relativedelta(days=30))
        ]).unlink()
