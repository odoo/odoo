# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.addons.website_event_track_session.controllers.session import WebsiteEventSessionController
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class WebsiteEventTrackQuiz(WebsiteEventSessionController):
    def _fetch_track(self, event_id, track_id):
        event = request.env['event.event'].browse(int(event_id)).exists()
        if not event:
            return {'error': 'event_wrong'}
        try:
            event.check_access_rights('read')
            event.check_access_rule('read')
        except AccessError:
            return {'error': 'event_access'}

        track = request.env['event.track'].browse(int(track_id)).exists()
        if not track:
            return {'error': 'track_wrong'}
        try:
            track.check_access_rights('read')
            track.check_access_rule('read')
        except AccessError:
            return {'error': 'track_access'}
        return {'track': track}

    def _event_track_get_values(self, event, track, **options):
        values = super(WebsiteEventTrackQuiz, self)._event_track_get_values(event, track)
        if 'quiz' in options:
            values.update({
                'show_quiz': True,
                'visitor': track._find_track_visitor(force_create=True)
            })
        return values

    def _find_track_visitor(self, track, force_create=False):
        partner = request.env.user.partner_id
        track_visitor = request.env['event.track.visitor'].sudo().search([('track_id', '=', track.id), ('partner_id', '=', request.env.user.partner_id.id)]) or request.env['website.visitor']._get_visitor_from_request(force_create=False)
        if force_create and not track_visitor:
            values = {
                'partner_id': partner.id,
                'quiz_completed': False,
                'quiz_points': 0,
                'track_id': track.id
            }
            track_visitor = request.env['event.track.visitor'].sudo().create(values)
        return track_visitor

    def _get_quiz_answers_details(self, track, answer_ids):
        all_questions = request.env['event.quiz.question'].sudo().search([('quiz_id', '=', track.quiz_id.id)])
        user_answers = request.env['event.quiz.question.answer'].sudo().search([('id', 'in', answer_ids)])

        if user_answers.mapped('question_id') != all_questions:
            return {'error': 'quiz_incomplete'}

        user_bad_answers = user_answers.filtered(lambda answer: not answer.is_correct)
        user_good_answers = user_answers - user_bad_answers
        return {
            'user_bad_answers': user_bad_answers,
            'user_good_answers': user_good_answers,
            'user_answers': user_answers,
            'points': sum([answer.awarded_points for answer in user_good_answers])
        }

    @http.route('/event_track/quiz/submit', type="json", auth="public", website=True)
    def event_track_quiz_submit(self, event_id, track_id, answer_ids):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_track(event_id, track_id)
        if fetch_res.get('error'):
            return fetch_res
        track = fetch_res['track']

        event_track_visitor = track._find_track_visitor(force_create=True)

        if event_track_visitor.quiz_completed:
            return {'error': 'track_quiz_done'}

        answers_details = self._get_quiz_answers_details(track, answer_ids)

        event_track_visitor.write({
            'quiz_completed': True,
            'quiz_points': answers_details['points'],
        })

        return {
            'answers': {
                answer.question_id.id: {
                    'is_correct': answer.is_correct,
                    'comment': answer.comment
                } for answer in answers_details['user_answers']
            },
            'quiz_completed': event_track_visitor.quiz_completed,
            'quiz_points': answers_details['points']
        }

    @http.route('/event_track/quiz/reset', type="json", auth="user", website=True)
    def quiz_reset(self, event_id, track_id):
        fetch_res = self._fetch_track(event_id, track_id)
        if fetch_res.get('error'):
            return fetch_res
        track = fetch_res['track']
        event_track_visitor = track._find_track_visitor(force_create=True)
        event_track_visitor.write({
            'quiz_completed': False,
            'quiz_points': 0,
        })

    @http.route(['/event_track/quiz/save'], type='json', auth='public', website=True)
    def quiz_save_to_session(self, quiz_answers):
        session_quiz_answers = json.loads(request.session.get('quiz_answers', '{}'))
        track_id = quiz_answers['track_id']
        session_quiz_answers[str(track_id)] = quiz_answers['quiz_answers']
        request.session['quiz_answers'] = json.dumps(session_quiz_answers)
