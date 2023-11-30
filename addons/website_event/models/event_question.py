# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventQuestion(models.Model):
    _name = 'event.question'
    _rec_name = 'title'
    _order = 'sequence,id'
    _description = 'Event Question'

    title = fields.Char(required=True, translate=True)
    question_type = fields.Selection([
        ('simple_choice', 'Selection'),
        ('text_box', 'Text Input'),
        ('name', 'Name'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('company_name', 'Company'),
    ], default='simple_choice', string="Question Type", required=True)
    event_type_id = fields.Many2one('event.type', 'Event Type', ondelete='cascade')
    event_id = fields.Many2one('event.event', 'Event', ondelete='cascade')
    answer_ids = fields.One2many('event.question.answer', 'question_id', "Answers", copy=True)
    sequence = fields.Integer(default=10)
    once_per_order = fields.Boolean('Ask once per order',
                                    help="If True, this question will be asked only once and its value will be propagated to every attendees."
                                         "If not it will be asked for every attendee of a reservation.")
    is_mandatory_answer = fields.Boolean('Mandatory Answer')

    @api.constrains('event_type_id', 'event_id')
    def _constrains_event(self):
        if any(question.event_type_id and question.event_id for question in self):
            raise UserError(_("Question cannot be linked to both an Event and an Event Type."))

    def write(self, vals):
        """ We add a check to prevent changing the question_type of a question that already has answers.
        Indeed, it would mess up the event.registration.answer (answer type not matching the question type). """

        if 'question_type' in vals:
            questions_new_type = self.filtered(lambda question: question.question_type != vals['question_type'])
            if questions_new_type:
                answer_count = self.env['event.registration.answer'].search_count([('question_id', 'in', questions_new_type.ids)])
                if answer_count > 0:
                    raise UserError(_("You cannot change the question type of a question that already has answers!"))
        return super(EventQuestion, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_answered_question(self):
        if self.env['event.registration.answer'].search_count([('question_id', 'in', self.ids)]):
            raise UserError(_('You cannot delete a question that has already been answered by attendees.'))

    def action_view_question_answers(self):
        """ Allow analyzing the attendees answers to event questions in a convenient way:
        - A graph view showing counts of each suggestions for simple_choice questions
          (Along with secondary pivot and tree views)
        - A tree view showing textual answers values for text_box questions. """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("website_event.action_event_registration_report")
        action['domain'] = [('question_id', '=', self.id)]
        if self.question_type == 'simple_choice':
            action['views'] = [(False, 'graph'), (False, 'pivot'), (False, 'tree')]
        elif self.question_type == 'text_box':
            action['views'] = [(False, 'tree')]
        return action
