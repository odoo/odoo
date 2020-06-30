# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import re
import requests

from odoo import api, fields, models


class Track(models.Model):
    _inherit = 'event.track'

    youtube_video_url = fields.Char('Youtube Video URL',
        help="Configure this URL so that event attendees can see your Track in video!")
    youtube_video_id = fields.Char('Youtube video ID', compute='_compute_youtube_video_id',
        help="Extracted from the video URL and used to infer various links (embed/thumbnail/...)")

    @api.depends('youtube_video_url')
    def _compute_youtube_video_id(self):
        for track in self:
            if track.youtube_video_url:
                regex = r'^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*'
                match = re.match(regex, track.youtube_video_url)
                if match and len(match.groups()) == 2 and len(match.group(2)) == 11:
                    track.youtube_video_id = match.group(2)

            if not track.youtube_video_id:
                track.youtube_video_id = False

    def _get_viewers_count(self):
        """ Uses the Youtube Data API to request the viewers count of all tracks in recordset (self).
        We collect data for both live and past videos, returning a dict with the following structure:
        {'trackId': {
            'live_views': 42, // relevant for streamings that are currently live
            'total_views': 5899 // relevant for existing videos or recorded live streams that are passed
        }}
        This is obviously only relevant for tracks that have a configured 'youtube_video_url'.
        The method is called when necessary, it would not make sense to make actual 'fields' for those values
        as it's constantly changing (we need to make the API call every time). """

        youtube_api_key = self.env['website'].get_current_website().website_event_track_youtube_api_key
        video_ids = {track.youtube_video_id: track.id for track in self if track.youtube_video_id}
        viewers_by_track = {}
        if video_ids.keys() and youtube_api_key:
            youtube_api_request = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'statistics,liveStreamingDetails',
                'id': ','.join(video_ids.keys()),
                'key': youtube_api_key,
            })
            for youtube_result in youtube_api_request.json().get('items', []):
                viewers_by_track[video_ids[youtube_result['id']]] = {
                    'live_views': youtube_result.get('liveStreamingDetails', {}).get('concurrentViewers', 0),
                    'total_views': youtube_result.get('statistics', {}).get('viewCount', 0),
                }

        return viewers_by_track

    def _get_next_track_suggestion(self):
        """ Returns the next track that can be auto-played when this one is done.
        It will search among all event.tracks in the same event and then filter
        the ones that have the lowest common starting date.
        Once it gets those track 'candidates', it will search by priority:
        - Find a track that the user has manually wishlisted
        - Find a track that is wishlisted by default
        - Find a track that has the most common tags with the current one
        - Find a track that starts in the same room as the current one
        - And finally, if nothing has been found, pick a random one. """

        self.ensure_one()

        track_candidates = self.search([
            ('event_id', '=', self.event_id.id),
            ('date_end', '>', self.date_end),
            ('id', '!=', self.id),
            ('youtube_video_url', '!=', False)
        ], order='date asc')

        if not track_candidates:
            return self.env['event.track']

        min_date = min(track_candidates.mapped('date'))
        track_candidates = track_candidates.filtered(lambda track: track.date == min_date)

        # 1. Try to find a manually wishlisted track
        manually_wishlisted_tracks = self.env['website.visitor']._get_visitor_from_request().event_track_ids
        manually_wishlisted_track = next((track for track in track_candidates if track in manually_wishlisted_tracks), False)
        if manually_wishlisted_track:
            return manually_wishlisted_track

        # 2. Try to find a default wishlisted track
        default_wishlisted_track = next((track for track in track_candidates if track.wishlisted_by_default), False)
        if default_wishlisted_track:
            return default_wishlisted_track

        # 3. Try to find the track that has the most common tag with our current track
        max_common_tags = 0
        max_common_tags_track = False
        for track_candidate in track_candidates:
            common_tags = len(track_candidate.tag_ids & self.tag_ids)
            if common_tags > max_common_tags:
                max_common_tags = common_tags
                max_common_tags_track = track_candidate

        if max_common_tags_track:
            return max_common_tags_track

        # 4. Try to find a track in the same 'room'
        if self.location_id:
            same_room_track = next((track for track in track_candidates if track.location_id == self.location_id), False)
            if same_room_track:
                return same_room_track

        # 5. No more common properties to look for, just pick one at random
        return random.choice(track_candidates)
