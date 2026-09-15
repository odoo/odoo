from odoo.libs.debug_log import DebugLog

from odoo.addons.website_event_track_live.controllers.track_live import (
    EventTrackLiveController,
)

_debug = DebugLog(__name__)


class EventTrackLiveQuizController(EventTrackLiveController):
    def _prepare_track_suggestion_values(self, track, track_suggestion):
        res = super()._prepare_track_suggestion_values(track, track_suggestion)
        res["current_track"]["show_quiz"] = (
            bool(track.quiz_id) and not track.is_quiz_completed
        )
        _debug.logic(
            "track_suggestion_quiz",
            track=track,
            quiz=track.quiz_id,
            completed=track.is_quiz_completed,
            show_quiz=res["current_track"]["show_quiz"],
        )
        return res
