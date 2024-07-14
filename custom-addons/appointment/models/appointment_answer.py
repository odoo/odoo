# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarAppointmentAnswer(models.Model):
    _name = "appointment.answer"
    _description = "Appointment Question Answers"
    _order = "sequence,id"

    question_id = fields.Many2one('appointment.question', 'Question', required=True, ondelete="cascade")
    name = fields.Char('Answer', translate=True, required=True)
    sequence = fields.Integer(default=10)

class CalendarAppointmentAnswerInput(models.Model):
    _name = "appointment.answer.input"
    _rec_name = "question_id"
    _description = "Appointment Answer Inputs"
    _order = "id desc"

    question_id = fields.Many2one('appointment.question', 'Question', required=True, ondelete="cascade")
    value_answer_id = fields.Many2one('appointment.answer', 'Selected Answer', ondelete="restrict")
    value_text_box = fields.Text('Text Answer')
    # Reporting
    appointment_type_id = fields.Many2one(related='question_id.appointment_type_id', required=True, store=True, ondelete="cascade")
    calendar_event_id = fields.Many2one('calendar.event', 'Calendar Event', required=True, ondelete="cascade")
    partner_id = fields.Many2one('res.partner', 'Customer')
    question_type = fields.Selection(related='question_id.question_type')

    _sql_constraints = [
        ('value_check',
         "CHECK(value_answer_id IS NOT NULL OR COALESCE(value_text_box, '') <> '')",
         "An answer input must either have a text value or a predefined answer."
        )
    ]
