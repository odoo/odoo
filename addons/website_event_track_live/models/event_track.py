# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models


class Track(models.Model):
    _inherit = 'event.track'

    youtube_video_url = fields.Char('YouTube Video Link',
        help="Configure this URL so that event attendees can see your Track in video!")
    youtube_video_id = fields.Char('YouTube video ID', compute='_compute_youtube_video_id',
        help="Extracted from the video URL and used to infer various links (embed/thumbnail/...)")
    is_youtube_replay = fields.Boolean('Is YouTube Replay',
        help="Check this option if the video is already available on YouTube to avoid showing 'Direct' options (Chat, ...)")
    is_youtube_chat_available = fields.Boolean('Is Chat Available', compute='_compute_is_youtube_chat_available')

    @api.depends('youtube_video_url')
    def _compute_youtube_video_id(self):
        for track in self:
            if track.youtube_video_url:
                regex = r'^.*(youtu.be\/|v\/|u\/\w\/|embed\/|live\/|watch\?v=|&v=)([^#&?]*).*'
                match = re.match(regex, track.youtube_video_url)
                if match and len(match.groups()) == 2 and len(match.group(2)) == 11:
                    track.youtube_video_id = match.group(2)

            if not track.youtube_video_id:
                track.youtube_video_id = False

    @api.depends('youtube_video_id', 'is_youtube_replay', 'date_end', 'is_track_done')
    def _compute_website_image_url(self):
        youtube_thumbnail_tracks = self.filtered(lambda track: not track.website_image and track.youtube_video_id)
        super(Track, self - youtube_thumbnail_tracks)._compute_website_image_url()
        for track in youtube_thumbnail_tracks:
            track.website_image_url = f'https://img.youtube.com/vi/{track.youtube_video_id}/maxresdefault.jpg'

    @api.depends('youtube_video_url', 'is_youtube_replay', 'date', 'date_end', 'is_track_upcoming', 'is_track_live')
    def _compute_is_youtube_chat_available(self):
        for track in self:
            track.is_youtube_chat_available = track.youtube_video_url and not track.is_youtube_replay and (track.is_track_soon or track.is_track_live)
