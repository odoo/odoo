# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

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
