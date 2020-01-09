# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from uuid import uuid4

from odoo import _, api, fields, models


class SurveyUserInputSession(models.Model):
    _name = 'survey.user_input_session'
    _description = 'Survey User Input Session'
    _rec_name = 'survey_id'
    _order = 'create_date desc'

    survey_id = fields.Many2one('survey.survey', string="Survey", required=True, readonly=True)
    answer_ids = fields.One2many('survey.user_input', 'user_input_session_id', string="Collected Answers")
    answer_ids_count = fields.Integer('Participants', compute='_compute_answer_ids_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed')
        ], default='draft', string="State", required=True)
    uuid = fields.Char('UUID', index=True, default=lambda self: str(uuid4()), copy=False)

    # current question fields
    current_question_id = fields.Many2one('survey.question', string="Current Question")
    current_question_start_time = fields.Datetime(string="Current Question Start Time")
    current_question_answer_count = fields.Integer('Answers Count', compute='_compute_current_question_answer_count')

    # settings
    competitive_mode = fields.Boolean('Competitive Mode',
        help="When activated, this mode will allow displaying a ranking chart of all attendees.")

    # question settings
    is_questions_time_limited = fields.Boolean("The question is limited in time")
    questions_time_limit = fields.Integer("Time limit (seconds)")
    speed_rating = fields.Boolean("Reward quick answers", store=True, readonly=False,
        compute="_compute_speed_rating", help="Attendees get more points if they answer quickly")

    @api.depends('answer_ids')
    def _compute_answer_ids_count(self):
        statistics = self.env['survey.user_input'].read_group(
            [('user_input_session_id', 'in', self.ids)],
            ['user_input_session_id'],
            ['user_input_session_id']
        )
        statistics_by_survey = {
            statistics_item['user_input_session_id'][0]: statistics_item['user_input_session_id_count']
            for statistics_item in statistics
        }
        for survey in self:
            survey.answer_ids_count = statistics_by_survey.get(survey.id, 0)

    @api.depends('is_questions_time_limited')
    def _compute_speed_rating(self):
        for session in self:
            if not session.is_questions_time_limited:
                session.speed_rating = False

    @api.depends('current_question_id', 'answer_ids.user_input_line_ids')
    def _compute_current_question_answer_count(self):
        for session in self:
            answer_count = 0
            input_line_count = self.env['survey.user_input.line'].read_group(
                [('question_id', '=', session.current_question_id.id), ('user_input_id', 'in', self.answer_ids.ids)],
                ['user_input_id:count_distinct'],
                ['question_id'],
            )
            if input_line_count:
                answer_count = input_line_count[0].get('user_input_id')

            session.current_question_answer_count = answer_count

    def action_open_session_manager(self):
        self.ensure_one()
        self.write({'state': 'ready'})

        return {
            'type': 'ir.actions.act_url',
            'name': "Open Session Manager",
            'target': 'self',
            'url': '/survey/session_manage/%s' % self.survey_id.access_token
        }

    def action_end_session(self):
        self.write({'state': 'closed'})
        self.answer_ids.sudo().write({'state': 'done'})
        self.answer_ids.sudo().flush(['state'])
        self.env['bus.bus'].sendone(self.uuid, {'type': 'end_session'})

    def action_result_session(self):
        """ Open the website page with the survey session results view """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Session",
            'target': 'self',
            'url': '/survey/results/%s/%s' % (self.survey_id.id, self.id)
        }

    def next_question(self):
        """ Triggers the next question of this session.

        We artificially add 3 seconds to the 'current_question_start_time' to account for server delay.
        As the timing can influence the attendees score, we try to be fair with everyone by giving them
        an extra few seconds before we start counting down.

        Frontend should take the delay into account by delaying the appropriate animations. """

        self.ensure_one()

        if not self.survey_id.question_ids:
            return

        if not self.current_question_id:
            question = self.survey_id.question_ids[0]
        else:
            question_ids = list(enumerate(self.survey_id.question_ids))
            current_question_index = question_ids.index(
                next(question for question in question_ids if question[1] == self.current_question_id)
            )
            question = self.survey_id.question_ids[current_question_index + 1]

        self.write({
            'current_question_id': question.id,
            'current_question_start_time': fields.Datetime.now() + relativedelta(seconds=3)
        })
        self.flush(['current_question_id', 'current_question_start_time'])
        self.env['bus.bus'].sendone(self.uuid, {'type': 'next_question'})

    def _prepare_ranking_values(self):
        """  Prepare the necessary values to display a ranking of the attendees for this session.
        The ranking is descending and takes the total of the attendee points up to the current question. """
        self.ensure_one()

        survey_results = self.env['survey.user_input.line'].read_group(
            [('user_input_id', 'in', self.answer_ids.ids)],
            ['user_input_id', 'answer_score:sum'],
            ['user_input_id'],
            orderby="answer_score desc",
            limit=25
        )

        nicknames_by_user_input = {
            user_input.id: user_input.survey_user_nickname
            for user_input in self.answer_ids
        }

        return [{
            'score': round(survey_result.get('answer_score'), 0),
            'nickname': nicknames_by_user_input.get(survey_result.get('user_input_id')[0]) or _('Anonymous')
        } for survey_result in survey_results]
