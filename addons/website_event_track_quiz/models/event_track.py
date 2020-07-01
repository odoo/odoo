# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EventTrack(models.Model):
    _name = "event.track"
    _inherit = ['event.track', 'quiz.config.mixin']

    question_ids = fields.One2many('quiz.question', 'track_id', string="Questions")
    questions_count = fields.Integer(string="Numbers of Questions", compute='_compute_questions_count')

    @api.depends('question_ids')
    def _compute_questions_count(self):
        for track in self:
            track.questions_count = len(track.question_ids)
