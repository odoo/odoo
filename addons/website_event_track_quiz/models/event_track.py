# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request


class EventTrack(models.Model):
    _name = "event.track"
    _inherit = ['event.track']

    quiz_id = fields.Many2one('event.quiz', string="Quiz")
    quiz_questions_count = fields.Integer(string="Numbers of Questions", compute='_compute_questions_count')

    @api.depends('quiz_id.question_ids')
    def _compute_questions_count(self):
        for track in self:
            track.quiz_questions_count = len(track.quiz_id.question_ids)

    def _find_track_visitor(self, force_create=False):
        partner = request.env.user.partner_id
        if partner:
            track_visitors = self.env['event.track.visitor'].sudo().search([('track_id', 'in', self.ids), ('partner_id', '=', partner.id)])
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request(force_create=False)
            track_visitors = self.env['event.track.visitor'].sudo().search([('track_id', 'in', self.ids), ('visitor_id', '=', visitor.id)])
        if force_create and not track_visitors:
            values = {
                'partner_id': partner.id,
                'quiz_completed': False,
                'quiz_points': 0,
                'track_id': self.id
            }
            return request.env['event.track.visitor'].sudo().create(values)
        return track_visitors
