# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventType(models.Model):
    _inherit = 'event.type'

    use_questions = fields.Boolean('Questions to Attendees')
    question_ids = fields.One2many(
        'event.question', 'event_type_id',
        string='Questions', copy=True)


class EventEvent(models.Model):
    """ Override Event model to add optional questions when buying tickets. """
    _inherit = 'event.event'

    question_ids = fields.One2many('event.question', 'event_id', 'Questions', copy=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('is_individual', '=', False)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('is_individual', '=', True)])

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(EventEvent, self)._onchange_type()
        if self.event_type_id.use_questions and self.event_type_id.question_ids:
            self.question_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'title': question.title,
                    'sequence': question.sequence,
                    'is_individual': question.is_individual,
                })
                for question in self.event_type_id.question_ids
            ]


class EventRegistrationAnswer(models.Model):
    ''' This m2m table has to be explicitly instanciated as we need unique ids
    in the reporting view event.question.report.

    This model is purely technical. '''

    _name = 'event.registration.answer'
    _table = 'event_registration_answer'
    _description = 'Event Registration Answer'

    event_answer_id = fields.Many2one('event.answer', required=True, ondelete='cascade')
    event_registration_id = fields.Many2one('event.registration', required=True, ondelete='cascade')


class EventRegistration(models.Model):
    """ Store answers on attendees. """
    _inherit = 'event.registration'

    answer_ids = fields.Many2many('event.answer', 'event_registration_answer', string='Answers')


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
    is_individual = fields.Boolean('Ask each attendee',
                                   help="If True, this question will be asked for every attendee of a reservation. If "
                                        "not it will be asked only once and its value propagated to every attendees.")

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
