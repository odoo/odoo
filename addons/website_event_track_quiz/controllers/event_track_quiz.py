# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.http import request


class WebsiteEventTrackQuiz(EventTrackController):

    # QUIZZES IN PAGE
    # ----------------------------------------------------------

    @http.route('/event_track/quiz/submit', type="json", auth="public", website=True)
    def event_track_quiz_submit(self, event_id, track_id, answer_ids):
        track = self._fetch_track(track_id)
        track_sudo = track.sudo()

        event_track_visitor = track._get_event_track_visitors(force_create=True)
        visitor_sudo = event_track_visitor.visitor_id
        if event_track_visitor.quiz_completed:
            return {'error': 'track_quiz_done'}

        # fetch as sudo because questions / answers may not be freely available to public
        answers_details = self._get_quiz_answers_details(track_sudo, answer_ids)
        if answers_details.get('error'):
            return answers_details

        event_track_visitor.write({
            'quiz_completed': True,
            'quiz_points': answers_details['points'],
        })

        result = {
            'answers': {
                answer.question_id.id: {
                    'awarded_points': answer.awarded_points,
                    'correct_answer': answer.question_id.correct_answer_id.text_value,
                    'is_correct': answer.is_correct,
                    'comment': answer.comment
                } for answer in answers_details['user_answers']
            },
            'quiz_completed': event_track_visitor.quiz_completed,
            'quiz_points': answers_details['points']
        }
        if visitor_sudo and request.httprequest.cookies.get('visitor_uuid', '') != visitor_sudo.access_token:
            result['visitor_uuid'] = visitor_sudo.access_token
        return result

    @http.route('/event_track/quiz/reset', type="json", auth="public", website=True)
    def quiz_reset(self, event_id, track_id):
        track = self._fetch_track(track_id)
        # When the 'unlimited tries' option is disabled and the user is not
        # identifed as an event manager, we do not allow the user to reset
        # the quiz. The event managers will always be able to reset the quiz
        # even if the option is disabled (for testing purposes).
        if not request.env.user.has_group('event.group_event_manager') and not track.sudo().quiz_id.repeatable:
            raise Forbidden()

        event_track_visitor = track._get_event_track_visitors(force_create=True)
        event_track_visitor.write({
            'quiz_completed': False,
            'quiz_points': 0,
        })

    def _get_quiz_answers_details(self, track, answer_ids):
        questions_count = len(track.quiz_ids)
        user_answers = request.env['event.quiz.answer'].sudo().search([('id', 'in', answer_ids)])

        if len(user_answers.mapped('question_id')) != questions_count:
            return {'error': 'quiz_incomplete'}

        return {
            'user_answers': user_answers,
            'points': sum([
                answer.awarded_points
                for answer in user_answers
            ])
        }
