# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AppointmentQuestion(models.Model):
    _name = "appointment.question"
    _description = "Appointment Questions"
    _order = "sequence"

    sequence = fields.Integer('Sequence')
    appointment_type_id = fields.Many2one('appointment.type', 'Appointment Type', ondelete="cascade")
    name = fields.Char('Question', translate=True, required=True)
    placeholder = fields.Char('Placeholder', translate=True)
    question_required = fields.Boolean('Mandatory Answer')
    question_type = fields.Selection([
        ('char', 'Single line text'),
        ('text', 'Multi-line text'),
        ('select', 'Dropdown (one answer)'),
        ('radio', 'Radio (one answer)'),
        ('checkbox', 'Checkboxes (multiple answers)')], 'Answer Type', default='char')
    answer_ids = fields.One2many('appointment.answer', 'question_id', string='Available Answers', copy=True)
    answer_input_ids = fields.One2many('appointment.answer.input', 'question_id', string='Submitted Answers')

    @api.constrains('question_type', 'answer_ids')
    def _check_question_type(self):
        incomplete_questions = self.filtered(lambda question: question.question_type in ['select', 'radio', 'checkbox'] and not question.answer_ids)
        if incomplete_questions:
            raise ValidationError(
                _('The following question(s) do not have any selectable answers : %s',
                  ', '.join(incomplete_questions.mapped('name'))
                  )
            )

    def action_view_question_answer_inputs(self):
        """ Allow analyzing the answers to a question on an appointment in a convenient way:
        - A graph view showing counts of each suggested answers for multiple-choice questions:
        select / radio / checkbox. (Along with secondary pivot and list views)
        - A list view showing textual answers values for char / text_box questions"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("appointment.appointment_answer_input_action_from_question")
        if self.question_type in ['select', 'radio', 'checkbox']:
            action['views'] = [(False, 'pivot'), (False, 'graph'), (False, 'list'), (False, 'form')]
        elif self.question_type in ['char', 'text_box']:
            action['views'] = [(False, 'list'), (False, 'form')]
        return action
