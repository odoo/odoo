# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventQuestion(models.Model):
    _name = 'event.question'
    _rec_name = 'title'
    _order = 'sequence,id'
    _description = 'Event Question'

    title = fields.Char(required=True, translate=True)
    event_type_id = fields.Many2one('event.type', 'Event Type', ondelete='cascade')
    event_id = fields.Many2one('event.event', 'Event', ondelete='cascade')
    answer_ids = fields.One2many('event.answer', 'question_id', "Answers", required=True, copy=True)
    sequence = fields.Integer(default=10)
    once_per_order = fields.Boolean('Ask only once per order',
                                    help="If True, this question will be asked only once and its value will be propagated to every attendees."
                                         "If not it will be asked for every attendee of a reservation.")

    @api.constrains('event_type_id', 'event_id')
    def _constrains_event(self):
        if any(question.event_type_id and question.event_id for question in self):
            raise UserError(_('Question cannot belong to both the event category and itself.'))

    @api.model
    def create(self, vals):
        event_id = vals.get('event_id', False)
        if event_id:
            event = self.env['event.event'].browse([event_id])
            if event.event_type_id.use_questions and event.event_type_id.question_ids:
                vals['answer_ids'] = vals.get('answer_ids', []) + [(0, 0, {
                    'name': answer.name,
                    'sequence': answer.sequence,
                }) for answer in event.event_type_id.question_ids.filtered(lambda question: question.title == vals.get('title')).mapped('answer_ids')]
        return super(EventQuestion, self).create(vals)


class EventAnswer(models.Model):
    _name = 'event.answer'
    _order = 'sequence,id'
    _description = 'Event Answer'

    name = fields.Char('Answer', required=True, translate=True)
    question_id = fields.Many2one('event.question', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
