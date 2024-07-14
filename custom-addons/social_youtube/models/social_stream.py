# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dateutil.parser
import re
import requests
from werkzeug.urls import url_join

from odoo import fields, models


class SocialStreamYoutube(models.Model):
    _inherit = 'social.stream'

    def _apply_default_name(self):
        for stream in self:
            if stream.media_id.media_type == 'youtube' and stream.account_id:
                stream.write({'name': '%s: %s' % (stream.stream_type_id.name, stream.account_id.name)})
            else:
                super(SocialStreamYoutube, stream)._apply_default_name()

    def _fetch_stream_data(self):
        if self.media_id.media_type != 'youtube':
            return super(SocialStreamYoutube, self)._fetch_stream_data()

        self.account_id._refresh_youtube_token()
        if self.stream_type_id.stream_type == 'youtube_channel_videos':
            return self._fetch_channel_videos()

    def _fetch_channel_videos(self):
        """ The method to retrieve the channel videos is a bit tricky.
        The best way to do it would be to use the API '/search' endpoint, specifying
        we only want to search for record of types 'video' and for our own channel.
        BUT, this endpoint 'costs' 100 quota points.

        Instead, we use a query to retrieve the "playlistItems" of our "uploads" playlist
        (the 'youtube_upload_playlist_id' field of the social.account).
        This call only costs a single quota point.

        Then we use the retrieved videos IDs to query the '/videos' endpoint to fetch
        all the necessary data (title, description, thumbnail, statistics, ...).
        This also costs one quota point, for a total of 2 points VS 100 points for the search. """

        # 1. get the playlist items from the "all uploads" playlist
        # results are returned by published desc by default
        playlist_items_endpoint = url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/playlistItems")
        playlist_items_response = requests.get(playlist_items_endpoint,
            params={
                'access_token': self.account_id.youtube_access_token,
                'playlistId': self.account_id.youtube_upload_playlist_id,
                'part': 'snippet,status',
                'maxResults': 50,
            },
            timeout=5
        ).json()

        if playlist_items_response.get('error'):
            self.account_id._action_disconnect_accounts(playlist_items_response)
            return False

        youtube_video_ids = [
            item['snippet']['resourceId']['videoId']
            for item in playlist_items_response['items']
            if item['status']['privacyStatus'] == 'public'
        ]
        if not youtube_video_ids:
            return False

        # 2. get the videos information from the playlist items retrieved at step 1.
        video_endpoint = url_join(self.env['social.media']._YOUTUBE_ENDPOINT, "youtube/v3/videos")
        video_items_response = requests.get(video_endpoint,
            params={
                'access_token': self.account_id.youtube_access_token,
                'part': 'id,snippet,statistics,contentDetails',
                'id': ','.join(youtube_video_ids),
            },
            timeout=5
        ).json()

        if video_items_response.get('error'):
            self.account_id._action_disconnect_accounts(video_items_response)
            return False
        elif not video_items_response.get('items'):
            return False

        # 3. create or update social.stream.post based on fetched videos
        existing_posts = self.env['social.stream.post'].search([
            ('stream_id', '=', self.id),
            ('youtube_video_id', 'in', youtube_video_ids)
        ])
        existing_posts_by_youtube_video_id = {
            post.youtube_video_id: post for post in existing_posts
        }

        posts_to_create = []
        for video in video_items_response['items']:
            video_info = video['snippet']
            video_stats = video['statistics']
            existing_post = existing_posts_by_youtube_video_id.get(video['id'])
            values = {
                'stream_id': self.id,
                'message': video_info['description'],
                'link_title': video_info['title'],
                'link_image_url': video_info['thumbnails'].get('medium', {}).get('url'),
                'author_name': video_info['channelTitle'],
                'published_date': fields.Datetime.from_string(
                    dateutil.parser.parse(video_info['publishedAt']).strftime('%Y-%m-%d %H:%M:%S')),
                'youtube_video_id': video['id'],
                'youtube_comments_count': video_stats.get('commentCount', 0),
                'youtube_likes_count': video_stats.get('likeCount', 0),
                'youtube_dislikes_count': video_stats.get('dislikeCount', 0),
                'youtube_views_count': video_stats.get('viewCount', 0)
            }

            if existing_post:
                existing_post.sudo().write(values)
            else:
                posts_to_create.append(values)

        stream_posts = self.env['social.stream.post'].sudo().create(posts_to_create)
        return any(stream_post.stream_id.create_uid.id == self.env.uid for stream_post in stream_posts)
