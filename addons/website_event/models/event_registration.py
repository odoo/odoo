# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _name = 'event.registration'
    _inherit = ['event.registration']

    visitor_id = fields.Many2one('website.visitor', string='Visitor', ondelete='set null')
    registration_answer_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Answers')
    registration_selection_answer_ids = fields.One2many('event.registration.answer', string='Attendee Selection Answers',
        compute="_compute_registration_selection_answer_ids")

    @api.depends('registration_answer_ids')
    def _compute_registration_selection_answer_ids(self):
        for registration in self:
            registration.registration_selection_answer_ids = registration.registration_answer_ids.filtered(lambda answer: answer.question_type == 'simple_choice')

    def _get_website_registration_allowed_fields(self):
        return {'name', 'phone', 'email', 'mobile', 'company_name', 'event_id', 'partner_id', 'event_ticket_id'}
