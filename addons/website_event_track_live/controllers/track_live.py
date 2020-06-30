# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http


class WebsiteEventTrackLiveController(http.Controller):
    @http.route('/event/track/<model("event.track"):track>/get_track_suggestion', type='json', auth='public')
    def get_next_track_suggestion(self, track):
        track_suggestion = track._get_next_track_suggestion()
        if track_suggestion:
            return {
                'id': track_suggestion.id,
                'name': track_suggestion.name,
                'has_image': bool(track_suggestion.image),
                'youtube_video_id': track_suggestion.youtube_video_id,
                'website_url': track_suggestion.website_url
            }
        else:
            return False
