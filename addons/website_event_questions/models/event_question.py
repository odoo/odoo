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
    question_type = fields.Selection([
        ('simple_choice', 'Selection'),
        ('text_box', 'Text Input')], default='simple_choice', string="Question Type", required=True)
    event_type_id = fields.Many2one('event.type', 'Event Type', ondelete='cascade')
    event_id = fields.Many2one('event.event', 'Event', ondelete='cascade')
    answer_ids = fields.One2many('event.question.answer', 'question_id', "Answers", copy=True)
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

    def write(self, vals):
        """ We add a check to prevent changing the question_type of a question that already has answers.
        Indeed, it would mess up the event.registration.answer (answer type not matching the question type). """

        if 'question_type' in vals:
            questions_new_type = self.filtered(lambda question: question.question_type != vals['question_type'])
            if questions_new_type:
                answer_count = self.env['event.registration.answer'].search_count([('question_id', 'in', questions_new_type.ids)])
                if answer_count > 0:
                    raise UserError(_("You cannot change the question type of a question that already has answers!"))
        return super(EventQuestion, self).write(vals)


class EventQuestionAnswer(models.Model):
    """ Contains suggested answers to a 'simple_choice' event.question. """
    _name = 'event.question.answer'
    _order = 'sequence,id'
    _description = 'Event Question Answer'

    name = fields.Char('Answer', required=True, translate=True)
    question_id = fields.Many2one('event.question', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
