# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    use_questions = fields.Boolean('Questions to Attendees')
    question_ids = fields.One2many(
        'event.question', 'event_type_id',
        string='Questions', copy=True)


class EventEvent(models.Model):
    """ Override Event model to add optional questions when buying tickets. """
    _inherit = 'event.event'

    question_ids = fields.One2many(
        'event.question', 'event_id', 'Questions', copy=True,
        compute='_compute_from_event_type', readonly=False, store=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('once_per_order', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('once_per_order', '=', False)])

    @api.depends('event_type_id')
    def _compute_from_event_type(self):
        super(EventEvent, self)._compute_from_event_type()
        for event in self:
            if event.event_type_id.use_questions and event.event_type_id.question_ids:
                event.question_ids = [(5, 0, 0)] + [
                    (0, 0, {
                        'title': question.title,
                        'question_type': question.question_type,
                        'sequence': question.sequence,
                        'once_per_order': question.once_per_order,
                        'answer_ids': [(0, 0, {
                            'name': answer.name,
                            'sequence': answer.sequence
                        }) for answer in question.answer_ids],
                    })
                    for question in event.event_type_id.question_ids
                ]
