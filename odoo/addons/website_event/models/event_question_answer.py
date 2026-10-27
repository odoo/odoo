# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventQuestionAnswer(models.Model):
    """ Contains suggested answers to a 'simple_choice' event.question. """
    _name = 'event.question.answer'
    _order = 'sequence,id'
    _description = 'Event Question Answer'

    name = fields.Char('Answer', required=True, translate=True)
    question_id = fields.Many2one('event.question', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_selected_answer(self):
        if self.env['event.registration.answer'].search_count([('value_answer_id', 'in', self.ids)]):
            raise UserError(_('You cannot delete an answer that has already been selected by attendees.'))
