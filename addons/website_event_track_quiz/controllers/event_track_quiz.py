from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_event_track.controllers.event_track import EventTrackController

_debug = DebugLog(__name__)


class WebsiteEventTrackQuiz(EventTrackController):
    @http.route("/event_track/quiz/submit", type="jsonrpc", auth="public", website=True)
    def event_track_quiz_submit(self, event_id, track_id, answer_ids):
        track = self._get_track(track_id)
        track_sudo = track.sudo()

        event_track_visitor = track._get_event_track_visitors(force_create=True)
        if event_track_visitor.quiz_completed:
            return {"error": "track_quiz_done"}

        answers_details = self._get_quiz_answers_details(track_sudo, answer_ids)
        if answers_details.get("error"):
            return answers_details

        event_track_visitor.write(
            {
                "quiz_completed": True,
                "quiz_points": answers_details["points"],
            }
        )

        return {
            "answers": {
                answer.question_id.id: {
                    "awarded_points": answer.awarded_points,
                    "correct_answer": answer.question_id.correct_answer_id.text_value,
                    "is_correct": answer.is_correct,
                    "comment": answer.comment,
                }
                for answer in answers_details["user_answers"]
            },
            "quiz_completed": event_track_visitor.quiz_completed,
            "quiz_points": answers_details["points"],
        }

    @http.route("/event_track/quiz/reset", type="jsonrpc", auth="public", website=True)
    def quiz_reset(self, event_id, track_id):
        track = self._get_track(track_id)
        if (
            not request.env.user.has_group("event.group_event_manager")
            and not track.sudo().quiz_id.repeatable
        ):
            _debug.logic("quiz_refused", reason="not_repeatable", track=track.id)
            raise Forbidden

        event_track_visitor = track._get_event_track_visitors(force_create=True)
        event_track_visitor.write(
            {
                "quiz_completed": False,
                "quiz_points": 0,
            }
        )

    def _get_quiz_answers_details(self, track, answer_ids):
        questions_count = track.quiz_questions_count
        user_answers = (
            request.env["event.quiz.answer"].sudo().search([("id", "in", answer_ids)])
        )

        if len(user_answers.mapped("question_id")) != questions_count:
            return {"error": "quiz_incomplete"}

        return {
            "user_answers": user_answers,
            "points": sum(answer.awarded_points for answer in user_answers),
        }
