# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistrationAnswer(models.Model):
    """ Represents the user input answer for a single event.question """
    _name = 'event.registration.answer'
    _description = 'Event Registration Answer'
    _rec_names_search = ['value_answer_id', 'value_text_box']

    question_id = fields.Many2one(
        'event.question', ondelete='restrict', required=True,
        domain="[('event_id', '=', event_id)]")
    registration_id = fields.Many2one('event.registration', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='registration_id.partner_id')
    event_id = fields.Many2one('event.event', related='registration_id.event_id')
    question_type = fields.Selection(related='question_id.question_type')
    value_answer_id = fields.Many2one('event.question.answer', string="Suggested answer")
    value_text_box = fields.Text('Text answer')

    _sql_constraints = [
        ('value_check', "CHECK(value_answer_id IS NOT NULL OR COALESCE(value_text_box, '') <> '')", "There must be a suggested value or a text value.")
    ]

    # for displaying selected answers by attendees in attendees list view
    @api.depends('value_answer_id', 'question_type', 'value_text_box')
    def _compute_display_name(self):
        for reg in self:
            reg.display_name = reg.value_answer_id.name if reg.question_type == "simple_choice" else reg.value_text_box
