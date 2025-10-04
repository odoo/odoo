# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event_track_live.controllers.track_live import EventTrackLiveController


class EventTrackLiveQuizController(EventTrackLiveController):

    def _prepare_track_suggestion_values(self, track, track_suggestion):
        res = super(EventTrackLiveQuizController, self)._prepare_track_suggestion_values(track, track_suggestion)
        res['current_track']['show_quiz'] = bool(track.quiz_id) and not track.is_quiz_completed
        return res
