# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.osv import expression

class EventTrackLiveController(EventTrackController):

    @http.route('/event_track/get_track_suggestion', type='json', auth='public', website=True)
    def get_next_track_suggestion(self, track_id):
        track = self._fetch_track(track_id)
        track_suggestion = track._get_track_suggestions(
            restrict_domain=expression.AND([
                self._get_event_tracks_domain(track.event_id),
                [('youtube_video_url', '!=', False)]
            ]), limit=1)
        if not track_suggestion:
            return False
        track_suggestion_sudo = track_suggestion.sudo()
        track_sudo = track.sudo()
        return self._prepare_track_suggestion_values(track_sudo, track_suggestion_sudo)

    def _prepare_track_suggestion_values(self, track, track_suggestion):
        return {
            'current_track': {
                'name': track.name,
                'website_image_url': track.website_image_url,
            },
            'suggestion': {
                'id': track_suggestion.id,
                'name': track_suggestion.name,
                'speaker_name': track_suggestion.partner_name,
                'website_url': track_suggestion.website_url
            }
        }
