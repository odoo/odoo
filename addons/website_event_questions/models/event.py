# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventEvent(models.Model):
    """ Override Event model to add optional questions when buying tickets. """
    _inherit = 'event.event'

    question_ids = fields.One2many('event.question', 'event_id', 'Questions', copy=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('is_individual', '=', False)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('is_individual', '=', True)])


class EventRegistrationAnswer(models.Model):
    ''' This m2m table has to be explicitly instanciated as we need unique ids
    in the reporting view event.question.report.

    This model is purely technical. '''

    _name = 'event.registration.answer'
    _table = 'event_registration_answer'

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

    title = fields.Char(required=True, translate=True)
    event_id = fields.Many2one('event.event', required=True, ondelete='cascade')
    answer_ids = fields.One2many('event.answer', 'question_id', "Answers", required=True, copy=True)
    sequence = fields.Integer(default=10)
    is_individual = fields.Boolean('Ask each attendee',
                                   help="If True, this question will be asked for every attendee of a reservation. If "
                                        "not it will be asked only once and its value propagated to every attendees.")


class EventAnswer(models.Model):
    _name = 'event.answer'
    _order = 'sequence,id'

    name = fields.Char('Answer', required=True, translate=True)
    question_id = fields.Many2one('event.question', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
