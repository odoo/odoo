# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class EventType(models.Model):
    _inherit = 'event.type'

    def _default_question_ids(self):
        return [
            (0, 0, {'title': _('Name'), 'question_type': 'name', 'is_mandatory_answer': True}),
            (0, 0, {'title': _('Email'), 'question_type': 'email', 'is_mandatory_answer': True}),
            (0, 0, {'title': _('Phone'), 'question_type': 'phone'}),
        ]

    question_ids = fields.One2many(
        'event.question', 'event_type_id', default=_default_question_ids,
        string='Questions', copy=True)
