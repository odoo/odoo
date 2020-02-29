# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
