# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.gamification_quiz.controllers.main import GamificationQuiz
from odoo.addons.website_event_track_session.controllers.session import WebsiteEventSessionController
from odoo.http import request


class GamificationQuiz(GamificationQuiz):

    def _get_m2o_field_name(self, model):
        return 'track_id' if model == 'event.track' else super(WebsiteEventTrackQuiz, self)._get_m2o_field_name(model)

    def _get_quiz_partner_model(self, object_model):
        return 'event.track.visitor' if object_model == 'event.track' else super(WebsiteEventTrackQuiz, self)._get_quiz_partner_model(object_model)

class WebsiteEventTrackQuiz(WebsiteEventSessionController):

    def _event_track_get_values(self, event, track, **options):
        values = super(WebsiteEventTrackQuiz, self)._event_track_get_values(event, track)
        if 'quiz' in options:
            values.update({
                'show_quiz': True,
                'visitor': self._get_event_track_visitor_info(track)
            })
        return values

    def _get_event_track_visitor_info(self, track):
        track_visitor = request.env['event.track.visitor'].sudo().search([('track_id', '=', track.id), ('partner_id', '=', request.env.user.partner_id.id)])
        return {
            'quiz_completed': track_visitor.quiz_completed if track_visitor else 0,
            'points_gained': track_visitor.points_gained if track_visitor else 0
        }
