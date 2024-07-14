# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from odoo import _, fields, models, tools
from werkzeug.urls import url_join


class SocialLivePostYoutube(models.Model):
    _inherit = 'social.live.post'

    youtube_video_id = fields.Char(related='post_id.youtube_video_id')

    def _refresh_statistics(self):
        super(SocialLivePostYoutube, self)._refresh_statistics()
        youtube_accounts = self.env['social.account'].search([('media_type', '=', 'youtube')])

        # 1. build various data structures we are going to need
        all_existing_posts = self.env['social.live.post'].sudo().search([
            ('account_id', 'in', youtube_accounts.ids),
            ('youtube_video_id', '!=', False)
        ])
        posts_per_account = dict.fromkeys(youtube_accounts.ids, self.env['social.live.post'])
        for existing_post in all_existing_posts:
            posts_per_account[existing_post.account_id.id] |= existing_post

        existing_live_posts_by_youtube_video_id = {
            live_post.youtube_video_id: live_post for live_post in all_existing_posts
        }

        # 2. make one batch of requests per account to fetch youtube videos
        youtube_videos = []
        for account in youtube_accounts:
            account._refresh_youtube_token()
            video_endpoint_url = url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/videos")

            youtube_video_ids = posts_per_account[account.id].mapped('youtube_video_id')

            YOUTUBE_BATCH_SIZE = 50  # can only fetch videos 50 by 50 maximum, limited by YouTube API
            for video_ids_batch in tools.split_every(YOUTUBE_BATCH_SIZE, youtube_video_ids):
                result = requests.get(video_endpoint_url,
                    params={
                        'id': ','.join(video_ids_batch),
                        'access_token': account.youtube_access_token,
                        'part': 'statistics',
                        'maxResults': YOUTUBE_BATCH_SIZE,
                    },
                    timeout=5
                )

                if not result.ok:
                    account._action_disconnect_accounts(result.json())
                    break

                youtube_videos += result.json().get('items')

        # 3. update live post based on video statistics
        for video in youtube_videos:
            video_stats = video['statistics']
            existing_live_posts_by_youtube_video_id.get(video['id']).write({
                'engagement': sum(int(video_stats.get(key, 0)) for key in [
                    'likeCount',
                    'viewCount',
                    'commentCount',
                    'dislikeCount',
                    'favoriteCount'
                ]),
            })

    def _post(self):
        youtube_live_posts = self._filter_by_media_types(['youtube'])
        super(SocialLivePostYoutube, (self - youtube_live_posts))._post()

        for live_post in youtube_live_posts:
            live_post._post_youtube()

    def _post_youtube(self):
        """ Will simply mark the already uploaded video as 'publicly available'. """
        self.ensure_one()
        self.account_id._refresh_youtube_token()

        youtube_description = self.post_id.youtube_description
        if youtube_description:
            # shorten and UTMize links in YouTube description
            # we only do that for the content we put on YouTube, the "message" field remains
            # untouched to avoid confusing the end user
            youtube_description = self.env['mail.render.mixin'].sudo()._shorten_links_text(
                    youtube_description,
                    self._get_utm_values())

        video_endpoint_url = url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/videos")
        result = requests.put(video_endpoint_url,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'snippet,status',
            },
            json={
                'id': self.youtube_video_id,
                'snippet': {
                    'title': self.post_id.youtube_title,
                    'description': youtube_description,
                    # for some reason the category ID is required, even if we never change it
                    'categoryId': self.post_id.youtube_video_category_id,
                },
                'status': {
                    'privacyStatus': self.post_id.youtube_video_privacy,
                    'embeddable': True
                }
            },
            timeout=5
        )

        if (result.ok):
            values = {
                'state': 'posted',
                'failure_reason': False
            }
        else:
            result_json = result.json()
            error_message = _('An error occurred.')
            youtube_error = result_json.get('error')
            if youtube_error:
                error_reason = youtube_error.get('errors', [{}])[0].get('reason')
                if youtube_error.get('code') == 404 and error_reason == 'videoNotFound':
                    error_message = _('The video you are trying to publish has been deleted from YouTube.')
                elif youtube_error.get('status') == 'INVALID_ARGUMENT':
                    error_message = _('Your video is missing a correct title or description.')
                else:
                    error_message = youtube_error.get('errors', [{}])[0].get('message') or error_reason

            values = {
                'state': 'failed',
                'failure_reason': error_message
            }

        self.write(values)
