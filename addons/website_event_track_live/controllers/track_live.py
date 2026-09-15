from odoo import http
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_event_track.controllers.event_track import EventTrackController

_debug = DebugLog(__name__)


class EventTrackLiveController(EventTrackController):
    @http.route(
        "/event_track/get_track_suggestion", type="jsonrpc", auth="public", website=True
    )
    def get_next_track_suggestion(self, track_id):
        track = self._get_track(track_id)
        track_suggestion = track._get_track_suggestions(
            restrict_domain=Domain.AND(
                [
                    self._get_domain_event_tracks(track.event_id),
                    Domain("youtube_video_url", "!=", False),
                ]
            ),
            limit=1,
        )
        if not track_suggestion:
            _debug.logic("no_live_track_suggestion", track=track, event=track.event_id)
            return False
        _debug.pipeline(
            "live_track_suggestion",
            track=track,
            suggestion=track_suggestion,
            event=track.event_id,
        )
        track_suggestion_sudo = track_suggestion.sudo()
        track_sudo = track.sudo()
        return self._prepare_track_suggestion_values(track_sudo, track_suggestion_sudo)

    def _prepare_track_suggestion_values(self, track, track_suggestion):
        return {
            "current_track": {
                "name": track.name,
                "website_image_url": track.website_image_url,
            },
            "suggestion": {
                "id": track_suggestion.id,
                "name": track_suggestion.name,
                "speaker_name": track_suggestion.partner_name,
                "website_url": track_suggestion.website_url,
            },
        }
