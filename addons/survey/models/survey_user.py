# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    """ Metadata for a set of one user's answers to a particular survey """
    _name = "survey.user_input"
    _rec_name = 'survey_id'
    _description = 'Survey User Input'

    # answer description
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True, readonly=True, ondelete='cascade')
    scoring_type = fields.Selection(string="Scoring", related="survey_id.scoring_type")
    start_datetime = fields.Datetime('Start date and time', readonly=True)
    deadline = fields.Datetime('Deadline', help="Datetime until customer can open the survey and submit answers")
    state = fields.Selection([
        ('new', 'Not started yet'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed')], string='Status', default='new', readonly=True)
    test_entry = fields.Boolean(readonly=True)
    last_displayed_page_id = fields.Many2one('survey.question', string='Last displayed question/page')
    # attempts management
    is_attempts_limited = fields.Boolean("Limited number of attempts", related='survey_id.is_attempts_limited')
    attempts_limit = fields.Integer("Number of attempts", related='survey_id.attempts_limit')
    attempts_number = fields.Integer("Attempt n°", compute='_compute_attempts_number')
    is_time_limit_reached = fields.Boolean("Is time limit reached?", compute='_compute_is_time_limit_reached')
    # identification / access
    access_token = fields.Char('Identification token', default=lambda self: str(uuid.uuid4()), readonly=True, required=True, copy=False)
    invite_token = fields.Char('Invite token', readonly=True, copy=False)  # no unique constraint, as it identifies a pool of attempts
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    email = fields.Char('Email', readonly=True)
    # questions / answers
    user_input_line_ids = fields.One2many('survey.user_input.line', 'user_input_id', string='Answers', copy=True)
    predefined_question_ids = fields.Many2many('survey.question', string='Predefined Questions', readonly=True)
    scoring_percentage = fields.Float("Score (%)", compute="_compute_scoring_percentage", store=True, compute_sudo=True)  # stored for perf reasons
    scoring_success = fields.Boolean('Quizz Passed', compute='_compute_scoring_success', store=True, compute_sudo=True)  # stored for perf reasons

    _sql_constraints = [
        ('unique_token', 'UNIQUE (access_token)', 'An access token must be unique!'),
    ]

    @api.depends('user_input_line_ids.answer_score', 'user_input_line_ids.question_id')
    def _compute_scoring_percentage(self):
        for user_input in self:
            total_possible_score = sum([
                answer_score if answer_score > 0 else 0
                for answer_score in user_input.predefined_question_ids.mapped('suggested_answer_ids.answer_score')
            ])

            if total_possible_score == 0:
                user_input.scoring_percentage = 0
            else:
                score = (sum(user_input.user_input_line_ids.mapped('answer_score')) / total_possible_score) * 100
                user_input.scoring_percentage = round(score, 2) if score > 0 else 0

    @api.depends('scoring_percentage', 'survey_id.scoring_success_min')
    def _compute_scoring_success(self):
        for user_input in self:
            user_input.scoring_success = user_input.scoring_percentage >= user_input.survey_id.scoring_success_min

    @api.depends('start_datetime', 'survey_id.is_time_limited', 'survey_id.time_limit')
    def _compute_is_time_limit_reached(self):
        """ Checks that the user_input is not exceeding the survey's time limit. """
        for user_input in self:
            user_input.is_time_limit_reached = user_input.survey_id.is_time_limited and fields.Datetime.now() \
                > user_input.start_datetime + relativedelta(minutes=user_input.survey_id.time_limit)

    @api.depends('state', 'test_entry', 'survey_id.is_attempts_limited', 'partner_id', 'email', 'invite_token')
    def _compute_attempts_number(self):
        attempts_to_compute = self.filtered(
            lambda user_input: user_input.state == 'done' and not user_input.test_entry and user_input.survey_id.is_attempts_limited
        )

        for user_input in (self - attempts_to_compute):
            user_input.attempts_number = 1

        if attempts_to_compute:
            self.env.cr.execute("""SELECT user_input.id, (COUNT(previous_user_input.id) + 1) AS attempts_number
                FROM survey_user_input user_input
                LEFT OUTER JOIN survey_user_input previous_user_input
                ON user_input.survey_id = previous_user_input.survey_id
                AND previous_user_input.state = 'done'
                AND previous_user_input.test_entry = False
                AND previous_user_input.id < user_input.id
                AND (user_input.invite_token IS NULL OR user_input.invite_token = previous_user_input.invite_token)
                AND (user_input.partner_id = previous_user_input.partner_id OR user_input.email = previous_user_input.email)
                WHERE user_input.id IN %s
                GROUP BY user_input.id;
            """, (tuple(attempts_to_compute.ids),))

            attempts_count_results = self.env.cr.dictfetchall()

            for user_input in attempts_to_compute:
                attempts_number = 1
                for attempts_count_result in attempts_count_results:
                    if attempts_count_result['id'] == user_input.id:
                        attempts_number = attempts_count_result['attempts_number']
                        break

                user_input.attempts_number = attempts_number

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'predefined_question_ids' not in vals:
                suvey_id = vals.get('survey_id', self.env.context.get('default_survey_id'))
                survey = self.env['survey.survey'].browse(suvey_id)
                vals['predefined_question_ids'] = [(6, 0, survey._prepare_user_input_predefined_questions().ids)]
        return super(SurveyUserInput, self).create(vals_list)

    # ------------------------------------------------------------
    # ACTIONS / BUSINESS
    # ------------------------------------------------------------

    def action_resend(self):
        partners = self.env['res.partner']
        emails = []
        for user_answer in self:
            if user_answer.partner_id:
                partners |= user_answer.partner_id
            elif user_answer.email:
                emails.append(user_answer.email)

        return self.survey_id.with_context(
            default_existing_mode='resend',
            default_partner_ids=partners.ids,
            default_emails=','.join(emails)
        ).action_send_survey()

    def action_print_answers(self):
        """ Open the website page with the survey form """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "View Answers",
            'target': 'self',
            'url': '/survey/print/%s?answer_token=%s' % (self.survey_id.access_token, self.access_token)
        }

    @api.model
    def _generate_invite_token(self):
        return str(uuid.uuid4())

    def _mark_done(self):
        """ This method will:
        1. mark the state as 'done'
        2. send the certification email with attached document if
        - The survey is a certification
        - It has a certification_mail_template_id set
        - The user succeeded the test
        Will also run challenge Cron to give the certification badge if any."""
        self.write({'state': 'done'})
        Challenge = self.env['gamification.challenge'].sudo()
        badge_ids = []
        for user_input in self:
            if user_input.survey_id.certification and user_input.scoring_success:
                if user_input.survey_id.certification_mail_template_id and not user_input.test_entry:
                    user_input.survey_id.certification_mail_template_id.send_mail(user_input.id, notif_layout="mail.mail_notification_light")
                if user_input.survey_id.certification_give_badge:
                    badge_ids.append(user_input.survey_id.certification_badge_id.id)

        if badge_ids:
            challenges = Challenge.search([('reward_id', 'in', badge_ids)])
            if challenges:
                Challenge._cron_update(ids=challenges.ids, commit=False)

    def get_start_url(self):
        self.ensure_one()
        return '%s?answer_token=%s' % (self.survey_id.get_start_url(), self.access_token)

    def get_print_url(self):
        self.ensure_one()
        return '%s?answer_token=%s' % (self.survey_id.get_print_url(), self.access_token)

    # ------------------------------------------------------------
    # CREATE / UPDATE LINES FROM SURVEY FRONTEND INPUT
    # ------------------------------------------------------------

    def save_lines(self, question, answer, comment=None):
        """ Save answers to questions, depending on question type

            If an answer already exists for question and user_input_id, it will be
            overwritten (or deleted for 'choice' questions) (in order to maintain data consistency).
        """
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])

        if question.question_type in ['char_box', 'text_box', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
        elif question.question_type in ['simple_choice', 'multiple_choice']:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)
        else:
            raise AttributeError(question.question_type + ": This type of question has no saving function")

    def _save_line_simple_answer(self, question, old_answers, answer):
        vals = self._get_line_answer_values(question, answer, question.question_type)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env['survey.user_input.line'].create(vals)

    def _save_line_choice(self, question, old_answers, answers, comment):
        if not (isinstance(answers, list)):
            answers = [answers]
        vals_list = []

        if question.question_type == 'simple_choice':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'multiple_choice':
            vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    def _save_line_matrix(self, question, old_answers, answers, comment):
        vals_list = []

        for row_key, row_answer in answers.items():
            for answer in row_answer:
                vals = self._get_line_answer_values(question, answer, 'suggestion')
                vals['matrix_row_id'] = row_key
                vals_list.append(vals.copy())

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    def _get_line_answer_values(self, question, answer, answer_type):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals

        if answer_type == 'suggestion':
            vals['suggested_answer_id'] = answer
        elif answer_type == 'numerical_box':
            vals['value_numerical_box'] = float(answer)
        else:
            vals['value_%s' % answer_type] = answer
        return vals

    def _get_line_comment_values(self, question, comment):
        return {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'char_box',
            'value_char_box': comment,
        }

    # ------------------------------------------------------------
    # STATISTICS / RESULTS
    # ------------------------------------------------------------

    def _prepare_statistics(self):
        res = dict((user_input, {
            'correct': 0,
            'incorrect': 0,
            'partial': 0,
            'skipped': 0,
        }) for user_input in self)

        scored_questions = self.mapped('predefined_question_ids').filtered(
            lambda question: question.question_type in ['simple_choice', 'multiple_choice']
        )

        for question in scored_questions:
            question_answer_correct = question.suggested_answer_ids.filtered(lambda answer: answer.is_correct)
            for user_input in self:
                user_answer_lines_question = user_input.user_input_line_ids.filtered(lambda line: line.question_id == question)
                user_answer_correct = user_answer_lines_question.filtered(lambda line: line.answer_is_correct and not line.skipped).mapped('suggested_answer_id')
                user_answer_incorrect = user_answer_lines_question.filtered(lambda line: not line.answer_is_correct and not line.skipped)

                if user_answer_correct == question_answer_correct:
                    res[user_input]['correct'] += 1
                elif user_answer_correct and user_answer_correct < question_answer_correct:
                    res[user_input]['partial'] += 1
                if not user_answer_correct and user_answer_incorrect:
                    res[user_input]['incorrect'] += 1
                if not user_answer_correct and not user_answer_incorrect:
                    res[user_input]['skipped'] += 1

        return [[
            {'text': _("Correct"), 'count': res[user_input]['correct']},
            {'text': _("Partially"), 'count': res[user_input]['partial']},
            {'text': _("Incorrect"), 'count': res[user_input]['incorrect']},
            {'text': _("Unanswered"), 'count': res[user_input]['skipped']}
        ] for user_input in self]


class SurveyUserInputLine(models.Model):
    _name = 'survey.user_input.line'
    _description = 'Survey User Input Line'
    _rec_name = 'user_input_id'
    _order = 'question_sequence, id'

    # survey data
    user_input_id = fields.Many2one('survey.user_input', string='User Input', ondelete='cascade', required=True)
    survey_id = fields.Many2one(related='user_input_id.survey_id', string='Survey', store=True, readonly=False)
    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade', required=True)
    page_id = fields.Many2one(related='question_id.page_id', string="Section", readonly=False)
    question_sequence = fields.Integer('Sequence', related='question_id.sequence', store=True)
    # answer
    skipped = fields.Boolean('Skipped')
    answer_type = fields.Selection([
        ('text_box', 'Free Text'),
        ('char_box', 'Text'),
        ('numerical_box', 'Number'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('suggestion', 'Suggestion')], string='Answer Type')
    value_char_box = fields.Char('Text answer')
    value_numerical_box = fields.Float('Numerical answer')
    value_date = fields.Date('Date answer')
    value_datetime = fields.Datetime('Datetime answer')
    value_text_box = fields.Text('Free Text answer')
    suggested_answer_id = fields.Many2one('survey.question.answer', string="Suggested answer")
    matrix_row_id = fields.Many2one('survey.question.answer', string="Row answer")
    # scoring
    answer_score = fields.Float('Score')
    answer_is_correct = fields.Boolean('Correct', compute='_compute_answer_is_correct')

    @api.depends('suggested_answer_id', 'question_id')
    def _compute_answer_is_correct(self):
        for answer in self:
            if answer.suggested_answer_id and answer.question_id.question_type in ['simple_choice', 'multiple_choice']:
                answer.answer_is_correct = answer.suggested_answer_id.is_correct
            else:
                answer.answer_is_correct = False

    @api.constrains('skipped', 'answer_type')
    def _check_answered_or_skipped(self):
        if any(line.skipped == bool(line.answer_type) for line in self):
            raise ValidationError(_('A question is either skipped, either answered. Not both.'))

    @api.constrains('answer_type')
    def _check_answer_type(self):
        for line in self:
            if line.answer_type == 'suggestion':
                field_name = 'suggested_answer_id'
            elif line.answer_type:
                field_name = 'value_%s' % line.answer_type
            else:
                field_name = False
            if field_name and not line[field_name]:
                raise ValidationError(_('The answer must be in the right type'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            suggested_answer_id = vals.get('suggested_answer_id')
            if suggested_answer_id:
                vals.update({'answer_score': self.env['survey.question.answer'].browse(int(suggested_answer_id)).answer_score})
        return super(SurveyUserInputLine, self).create(vals_list)

    def write(self, vals):
        suggested_answer_id = vals.get('suggested_answer_id')
        if suggested_answer_id:
            vals.update({'answer_score': self.env['survey.question.answer'].browse(int(suggested_answer_id)).answer_score})
        return super(SurveyUserInputLine, self).write(vals)
