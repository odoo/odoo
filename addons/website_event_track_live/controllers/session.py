import re

from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_event_track.controllers.event_track import EventTrackController

_debug = DebugLog(__name__)


class WebsiteEventSessionLiveController(EventTrackController):
    def _event_track_page_get_values(self, event, track, **options):
        if "widescreen" not in options:
            options["widescreen"] = track.youtube_video_url and (
                track.is_youtube_replay
                or track.is_track_soon
                or track.is_track_live
                or track.is_track_done
            )
        _debug.logic(
            "track_page_layout",
            event=event,
            track=track,
            widescreen=options["widescreen"],
            replay=track.is_youtube_replay,
            live=track.is_track_live,
        )
        values = super()._event_track_page_get_values(event, track, **options)
        values["is_mobile_chat_disabled"] = bool(
            re.match(
                r"^.*(Android|iPad|iPhone).*",
                request.httprequest.headers.get(
                    "User-Agent", request.httprequest.headers.get("user-agent", "")
                ),
            )
        )
        return values
