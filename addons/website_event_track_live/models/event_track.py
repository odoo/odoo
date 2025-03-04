# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning


class EventTrack(models.Model):
    _inherit = 'event.track'

    youtube_post_id = fields.Many2one('event.track.live.post', 'YouTube Post', ondelete='set null')
    youtube_video_url = fields.Char('YouTube Video Link', compute='_compute_youtube_video_url', store=True)
    youtube_video_id = fields.Char('YouTube Video ID', compute='_compute_youtube_video_id',
        help="Extracted from the video URL and used to infer various links (embed/thumbnail/...)")
    is_youtube_replay = fields.Boolean('Is YouTube Replay',
        help="Check this option if the video is already available on YouTube to avoid showing 'Direct' options (Chat, ...)")
    is_youtube_chat_available = fields.Boolean('Is Chat Available', compute='_compute_is_youtube_chat_available')

    @api.depends('youtube_post_id.youtube_video_id')
    def _compute_youtube_video_url(self):
        for record in self:
            record.youtube_video_url = record.youtube_post_id.youtube_video_url

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
        super(EventTrack, self - youtube_thumbnail_tracks)._compute_website_image_url()
        for track in youtube_thumbnail_tracks:
            track.website_image_url = f'https://img.youtube.com/vi/{track.youtube_video_id}/maxresdefault.jpg'

    @api.depends('youtube_video_url', 'is_youtube_replay', 'date', 'date_end', 'is_track_upcoming', 'is_track_live')
    def _compute_is_youtube_chat_available(self):
        for track in self:
            track.is_youtube_chat_available = track.youtube_video_url and not track.is_youtube_replay and (track.is_track_soon or track.is_track_live)

    def action_publish_on_youtube(self):
        """Publish live stream on YouTube or trigger OAuth flow if account is missing."""
        youtube_account = self.env['event.track.live.account'].search([], limit=1)
        if youtube_account:
            return {
                "type": "ir.actions.act_window",
                "name": "Create YouTube Live",
                "res_model": "event.track.post.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_company_id": self[0].company_id.id if len(self) == 1 else False,
                    "active_ids": self.ids,
                },
            }
        else:
            msg = _("No YouTue Account Found! You need to have at least one Youtube account to publish a live event on Youtube.")
            redirect_action = self.env.ref('website_event_track_live.event_track_live_account_action')
            raise RedirectWarning(msg, redirect_action.id, _('Add Account'))

    def action_see_post(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.track.live.post',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.youtube_post_id.id,
        }
