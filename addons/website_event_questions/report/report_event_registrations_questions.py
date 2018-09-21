# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ReportEventRegistrationQuestions(models.Model):
    _name = "event.question.report"
    _auto = False
    _description = 'Event Question Report'

    attendee_id = fields.Many2one(comodel_name='event.registration', string='Registration')
    question_id = fields.Many2one(comodel_name='event.question', string='Question')
    answer_id = fields.Many2one(comodel_name='event.answer', string='Answer')
    event_id = fields.Many2one(comodel_name='event.event', string='Event')

    @api.model_cr
    def init(self):
        """ Event Question main report """
        tools.drop_view_if_exists(self._cr, 'event_question_report')
        self._cr.execute(""" CREATE VIEW event_question_report AS (
            SELECT
                att_answer.id as id,
                att_answer.event_registration_id as attendee_id,
                answer.question_id as question_id,
                answer.id as answer_id,
                question.event_id as event_id
            FROM
                event_registration_answer as att_answer
            LEFT JOIN
                event_answer as answer ON answer.id = att_answer.event_answer_id
            LEFT JOIN
                event_question as question ON question.id = answer.question_id
            GROUP BY
                attendee_id,
                event_id,
                question_id,
                answer_id,
                att_answer.id
        )""")
