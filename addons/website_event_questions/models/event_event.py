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

    question_ids = fields.One2many('event.question', 'event_id', 'Questions', copy=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('once_per_order', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('once_per_order', '=', False)])

    @api.onchange('event_type_id')
    def _onchange_type(self):
        super(EventEvent, self)._onchange_type()
        if self.event_type_id.use_questions and self.event_type_id.question_ids:
            self.question_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'title': question.title,
                    'sequence': question.sequence,
                    'once_per_order': question.once_per_order,
                })
                for question in self.event_type_id.question_ids
            ]
