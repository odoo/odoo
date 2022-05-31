# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class EventRegistration(models.Model):
    """ Store answers on attendees. """
    _inherit = 'event.registration'

    registration_answer_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Answers')

class EventRegistrationAnswer(models.Model):
    """ Represents the user input answer for a single event.question """
    _name = 'event.registration.answer'
    _description = 'Event Registration Answer'

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
    def name_get(self):
        return [
            (reg.id,
             reg.value_answer_id.name if reg.question_type == "simple_choice" else reg.value_text_box
             )
            for reg in self
        ]

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """ Search records whose selected answer or text answer are matching the ``name`` argument. """
        if name and operator == 'ilike':
            if not args:
                args = []

            # search on both selected answer OR text answer (combined with passed args)
            selected_answer_domain = [('value_answer_id', operator, name)]
            text_answer_domain = [('value_text_box', operator, name)]
            domain = expression.AND([args, expression.OR([
                selected_answer_domain,
                text_answer_domain,
            ])])
        else:
            domain = args or []

        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
