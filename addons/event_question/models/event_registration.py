# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventRegistration(models.Model):
    _name = 'event.registration'
    _inherit = ['event.registration']

    registration_answer_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Answers')
    registration_answer_choice_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Selection Answers',
        domain=[('question_type', '=', 'simple_choice')])

    def _get_registration_summary(self):
        res = super()._get_registration_summary()
        res['registration_answers'] = self.registration_answer_ids.filtered('value_answer_id').mapped('display_name')
        return res
