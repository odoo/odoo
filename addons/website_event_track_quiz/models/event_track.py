# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class EventTrack(models.Model):
    _inherit = ['event.track']

    quiz_id = fields.Many2one('event.quiz', string="Quiz", groups="event.group_event_user")
    quiz_questions_count = fields.Integer(string="# Quiz Questions", compute='_compute_quiz_questions_count', groups="event.group_event_user")
    is_quiz_completed = fields.Boolean('Is Quiz Done', compute='_compute_quiz_data')
    quiz_points = fields.Integer('Quiz Points', compute='_compute_quiz_data')

    @api.depends('quiz_id.question_ids')
    def _compute_quiz_questions_count(self):
        for track in self:
            track.quiz_questions_count = len(track.quiz_id.question_ids)

    @api.depends('quiz_id', 'event_track_visitor_ids.visitor_id',
                 'event_track_visitor_ids.partner_id', 'event_track_visitor_ids.quiz_completed',
                 'event_track_visitor_ids.quiz_points')
    @api.depends_context('uid')
    def _compute_quiz_data(self):
        tracks_quiz = self.filtered(lambda track: track.quiz_id)
        (self - tracks_quiz).is_quiz_completed = False
        (self - tracks_quiz).quiz_points = 0
        if tracks_quiz:
            current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
            if self.env.user._is_public() and not current_visitor:
                for track in tracks_quiz:
                    track.is_quiz_completed = False
                    track.quiz_points = 0
            else:
                if self.env.user._is_public():
                    domain = [('visitor_id', '=', current_visitor.id)]
                elif current_visitor:
                    domain = [
                        '|',
                        ('partner_id', '=', self.env.user.partner_id.id),
                        ('visitor_id', '=', current_visitor.id)
                    ]
                else:
                    domain = [('partner_id', '=', self.env.user.partner_id.id)]

                event_track_visitors = self.env['event.track.visitor'].sudo().search_read(
                    expression.AND([
                        domain,
                        [('track_id', 'in', tracks_quiz.ids)]
                    ]), fields=['track_id', 'quiz_completed', 'quiz_points']
                )

                quiz_visitor_map = {
                    track_visitor['track_id'][0]: {
                        'quiz_completed': track_visitor['quiz_completed'],
                        'quiz_points': track_visitor['quiz_points']
                    } for track_visitor in event_track_visitors
                }
                for track in tracks_quiz:
                    if quiz_visitor_map.get(track.id):
                        track.is_quiz_completed = quiz_visitor_map[track.id]['quiz_completed']
                        track.quiz_points = quiz_visitor_map[track.id]['quiz_points']
                    else:
                        track.is_quiz_completed = False
                        track.quiz_points = 0
