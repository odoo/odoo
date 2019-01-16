# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

email_validator = re.compile(r"[^@]+@[^@]+\.[^@]+")
_logger = logging.getLogger(__name__)


def dict_keys_startswith(dictionary, string):
    """Returns a dictionary containing the elements of <dict> whose keys start with <string>.
        .. note::
            This function uses dictionary comprehensions (Python >= 2.7)
    """
    return {k: v for k, v in dictionary.items() if k.startswith(string)}


class SurveyUserInput(models.Model):
    """ Metadata for a set of one user's answers to a particular survey """

    _name = "survey.user_input"
    _rec_name = 'survey_id'
    _description = 'Survey User Input'

    # description
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True, readonly=True, ondelete='cascade')
    input_type = fields.Selection([
        ('manually', 'Manually'), ('link', 'Link')],
        string='Answer Type', default='manually', required=True, readonly=True,
        oldname="type")
    state = fields.Selection([
        ('new', 'Not started yet'),
        ('skip', 'Partially completed'),
        ('done', 'Completed')], string='Status', default='new', readonly=True)
    test_entry = fields.Boolean(readonly=True)
    # identification and access
    token = fields.Char('Identification token', default=lambda self: str(uuid.uuid4()), readonly=True, required=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    email = fields.Char('E-mail', readonly=True)
    # answers
    user_input_line_ids = fields.One2many('survey.user_input_line', 'user_input_id', string='Answers', copy=True)
    deadline = fields.Datetime('Deadline', help="Datetime until customer can open the survey and submit answers")
    last_displayed_page_id = fields.Many2one('survey.page', string='Last displayed page')
    quizz_score = fields.Float("Score for the quiz", compute="_compute_quizz_score", default=0.0)

    @api.depends('user_input_line_ids.quizz_mark')
    def _compute_quizz_score(self):
        for user_input in self:
            user_input.quizz_score = sum(user_input.user_input_line_ids.mapped('quizz_mark'))

    _sql_constraints = [
        ('unique_token', 'UNIQUE (token)', 'A token must be unique!'),
    ]

    def add_answer_line(self, question, answer_str, comment_str):
        """ UPDATE ME """
        answer_method_name = ' _get_answer_line_values_%s' % (question.question_type)
        answer_values = getattr(self, answer_method_name)(self, question, answer_str, comment_str)

        answer_lines = self.env['survey.user_input_line'].sudo().search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)])
        if answer_lines and answer_values and len(answer_lines) == 1 and len(answer_values) == 1:
            answer_lines.write(answer_values)
        else:
            answer_lines.unlink()

        if not answer_lines:
            create_values = self._prepare_answer_line_values(question)
            for values in create_values:
                values.update(**answer_values)
            answer_lines = self.env['survey.user_input_line'].sudo().create(create_values)

        return answer_lines

    def _prepare_answer_line_values(self, question, answer_str, comment_str):
        return {
            'user_input_id': self.id,
            'question_id': question.id,
            'survey_id': self.survey_id.id,
            'skipped': not bool(answer_str),
        }

    def _get_answer_line_values_free_text(self, question, answer_str, comment_str):
        return {
            'answer_type': 'free_text' if answer_str else None,
            'value_free_text': answer_str,
        }

    def _get_answer_line_values_textbox(self, question, answer_str, comment_str):
        return {
            'answer_type': 'text' if answer_str else None,
            'value_text': answer_str,
        }

    def _get_answer_line_values_numerical_box(self, question, answer_str, comment_str):
        try:
            value = float(answer_str)
        except:
            value = False
        return {
            'answer_type': 'number' if value is not False else None,
            'value_number': value,
            'skipped': not bool(value),
        }

    def _get_answer_line_values_date(self, question, answer_str, comment_str):
        try:
            value = fields.Date.from_string(answer_str)
        except:
            value = False
        return {
            'answer_type': 'date' if value is not False else None,
            'value_date': value,
            'skipped': not bool(value),
        }

    def _get_answer_line_values_simple_choice(self, question, answer_str, comment_str):
        vals = []

        try:
            suggested_id = int(answer_str)
        except:
            suggested_id = False
        if suggested_id and not self.env['survey.label'].sudo().browse(suggested_id).exists():
            suggested_id = False
        if suggested_id:
            vals.add({
                'answer_type': 'suggestion' if suggested_id else None,
                'value_suggested': suggested_id,
                'skipped': not bool(suggested_id),
            })
        if not suggested_id and (not comment_str or not question.comment_count_as_answer):
            vals.add({
                'answer_type': None,
                'skipped': True
            })

        if comment_str:
            vals.add({
                'answer_type': 'text',
                'value_text': comment_str,
            })

        return vals

    def _get_answer_line_values_multiple_choice(self, question, answer_list, comment_str):
        vals = []
        for answer in answer_list:
            try:
                suggested_id = int(answer)
            except:
                suggested_id = False
            if suggested_id and not self.env['survey.label'].sudo().browse(suggested_id).exists():
                suggested_id = False
            if suggested_id:
                vals.add({
                    'answer_type': 'suggestion' if suggested_id else None,
                    'value_suggested': suggested_id,
                    'skipped': not bool(suggested_id),
                })
        if not vals and (not comment_str or not question.comment_count_as_answer):
            vals.add({
                'answer_type': None,
                'skipped': True
            })

        if comment_str:
            vals.add({
                'answer_type': 'text',
                'value_text': comment_str,
            })

        return vals

    def _get_answer_line_values_matrix(self, question, answer_list, comment_str):
        vals = []
        for answer in answer_list:
            try:
                suggested_id = int(answer)
            except:
                suggested_id = False
            if suggested_id and not self.env['survey.label'].sudo().browse(suggested_id).exists():
                suggested_id = False
            if suggested_id:
                vals.add({
                    'answer_type': 'suggestion' if suggested_id else None,
                    'value_suggested': suggested_id,
                    'skipped': not bool(suggested_id),
                })
        if not vals and (not comment_str or not question.comment_count_as_answer):
            vals.add({
                'answer_type': None,
                'skipped': True
            })

        if comment_str:
            vals.add({
                'answer_type': 'text',
                'value_text': comment_str,
            })

        return vals

    @api.model
    def do_clean_emptys(self):
        """ Remove empty user inputs that have been created manually
            (used as a cronjob declared in data/survey_cron.xml)
        """
        an_hour_ago = fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(hours=1))
        self.search([('input_type', '=', 'manually'),
                     ('state', '=', 'new'),
                     ('create_date', '<', an_hour_ago)]).unlink()

    @api.multi
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

    @api.multi
    def action_print_answers(self):
        """ Open the website page with the survey form """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "View Answers",
            'target': 'self',
            'url': '/survey/print/%s?token=%s' % (self.survey_id.id, self.token)
        }


class SurveyUserInputLine(models.Model):
    _name = 'survey.user_input_line'
    _description = 'Survey User Input Line'
    _rec_name = 'user_input_id'

    user_input_id = fields.Many2one('survey.user_input', string='User Input', ondelete='cascade', required=True)
    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade', required=True)
    page_id = fields.Many2one(related='question_id.page_id', string="Page", readonly=False)
    survey_id = fields.Many2one(related='user_input_id.survey_id', string='Survey', store=True, readonly=False)
    skipped = fields.Boolean('Skipped')
    answer_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('free_text', 'Free Text'),
        ('suggestion', 'Suggestion')], string='Answer Type')
    value_text = fields.Char('Text answer')
    value_number = fields.Float('Numerical answer')
    value_date = fields.Date('Date answer')
    value_free_text = fields.Text('Free Text answer')
    value_suggested = fields.Many2one('survey.label', string="Suggested answer")
    value_suggested_row = fields.Many2one('survey.label', string="Row answer")
    quizz_mark = fields.Float('Score given for this choice')

    @api.constrains('skipped', 'answer_type')
    def _answered_or_skipped(self):
        for uil in self:
            if not uil.skipped != bool(uil.answer_type):
                raise ValidationError(_('This question cannot be unanswered or skipped.'))

    @api.constrains('answer_type')
    def _check_answer_type(self):
        for uil in self:
            fields_type = {
                'text': bool(uil.value_text),
                'number': (bool(uil.value_number) or uil.value_number == 0),
                'date': bool(uil.value_date),
                'free_text': bool(uil.value_free_text),
                'suggestion': bool(uil.value_suggested)
            }
            if not fields_type.get(uil.answer_type, True):
                raise ValidationError(_('The answer must be in the right type'))

    def _get_mark(self, value_suggested):
        label = self.env['survey.label'].browse(int(value_suggested))
        mark = label.quizz_mark if label.exists() else 0.0
        return mark

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            value_suggested = vals.get('value_suggested')
            if value_suggested:
                vals.update({'quizz_mark': self._get_mark(value_suggested)})
        return super(SurveyUserInputLine, self).create(vals_list)

    @api.multi
    def write(self, vals):
        value_suggested = vals.get('value_suggested')
        if value_suggested:
            vals.update({'quizz_mark': self._get_mark(value_suggested)})
        return super(SurveyUserInputLine, self).write(vals)
