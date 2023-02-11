# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    question_ids = fields.One2many(
        'event.question', 'event_type_id',
        string='Questions', copy=True)


class EventEvent(models.Model):
    """ Override Event model to add optional questions when buying tickets. """
    _inherit = 'event.event'

    question_ids = fields.One2many(
        'event.question', 'event_id', 'Questions', copy=True,
        compute='_compute_question_ids', readonly=False, store=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('once_per_order', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('once_per_order', '=', False)])

    @api.depends('event_type_id')
    def _compute_question_ids(self):
        """ Update event questions from its event type. Depends are set only on
        event_type_id itself to emulate an onchange. Changing event type content
        itself should not trigger this method.

        When synchronizing questions:

          * lines that no answer are removed;
          * type lines are added;
        """
        if self._origin.question_ids:
            # lines to keep: those with already given answers
            questions_tokeep_ids = self.env['event.registration.answer'].search(
                [('question_id', 'in', self._origin.question_ids.ids)]
            ).question_id.ids
        else:
            questions_tokeep_ids = []
        for event in self:
            if not event.event_type_id and not event.question_ids:
                event.question_ids = False
                continue

            if questions_tokeep_ids:
                questions_toremove = event._origin.question_ids.filtered(lambda question: question.id not in questions_tokeep_ids)
                command = [(3, question.id) for question in questions_toremove]
            else:
                command = [(5, 0)]
            if event.event_type_id.question_ids:
                command += [
                    (0, 0, {
                        'title': question.title,
                        'question_type': question.question_type,
                        'sequence': question.sequence,
                        'once_per_order': question.once_per_order,
                        'answer_ids': [(0, 0, {
                            'name': answer.name,
                            'sequence': answer.sequence
                        }) for answer in question.answer_ids],
                    }) for question in event.event_type_id.question_ids
                ]
            event.question_ids = command
