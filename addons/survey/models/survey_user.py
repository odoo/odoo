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
            'url': '/survey/print/%s?answer_token=%s' % (self.survey_id.access_token, self.token)
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
        ('datetime', 'Datetime'),
        ('free_text', 'Free Text'),
        ('suggestion', 'Suggestion')], string='Answer Type')
    value_text = fields.Char('Text answer')
    value_number = fields.Float('Numerical answer')
    value_date = fields.Date('Date answer')
    value_datetime = fields.Datetime('Datetime answer')
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

    @api.model
    def save_lines(self, user_input_id, question, post, answer_tag):
        """ Save answers to questions, depending on question type

            If an answer already exists for question and user_input_id, it will be
            overwritten (in order to maintain data consistency).
        """
        try:
            saver = getattr(self, 'save_line_' + question.question_type)
        except AttributeError:
            _logger.error(question.question_type + ": This type of question has no saving function")
            return False
        else:
            saver(user_input_id, question, post, answer_tag)

    @api.model
    def save_line_free_text(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False,
        }
        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'free_text', 'value_free_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil.create(vals)
        return True

    @api.model
    def save_line_textbox(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'text', 'value_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil.create(vals)
        return True

    @api.model
    def save_line_numerical_box(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'number', 'value_number': float(post[answer_tag])})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil.create(vals)
        return True

    @api.model
    def save_line_date(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'date', 'value_date': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil.create(vals)
        return True

    @api.model
    def save_line_datetime(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'datetime', 'value_datetime': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        if old_uil:
            old_uil.write(vals)
        else:
            old_uil.create(vals)
        return True

    @api.model
    def save_line_simple_choice(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        old_uil.sudo().unlink()

        if answer_tag in post and post[answer_tag].strip():
            vals.update({'answer_type': 'suggestion', 'value_suggested': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})

        # '-1' indicates 'comment count as an answer' so do not need to record it
        if post.get(answer_tag) and post.get(answer_tag) != '-1':
            self.create(vals)

        comment_answer = post.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer, 'skipped': False, 'value_suggested': False})
            self.create(vals)

        return True

    @api.model
    def save_line_multiple_choice(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        old_uil.sudo().unlink()

        ca_dict = dict_keys_startswith(post, answer_tag + '_')
        comment_answer = ca_dict.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if len(ca_dict) > 0:
            for key in ca_dict:
                # '-1' indicates 'comment count as an answer' so do not need to record it
                if key != ('%s_%s' % (answer_tag, '-1')):
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca_dict[key]})
                    self.create(vals)
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer, 'value_suggested': False})
            self.create(vals)
        if not ca_dict and not comment_answer:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(vals)
        return True

    @api.model
    def save_line_matrix(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search([
            ('user_input_id', '=', user_input_id),
            ('survey_id', '=', question.survey_id.id),
            ('question_id', '=', question.id)
        ])
        old_uil.sudo().unlink()

        no_answers = True
        ca_dict = dict_keys_startswith(post, answer_tag + '_')

        comment_answer = ca_dict.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer})
            self.create(vals)
            no_answers = False

        if question.matrix_subtype == 'simple':
            for row in question.labels_ids_2:
                a_tag = "%s_%s" % (answer_tag, row.id)
                if a_tag in ca_dict:
                    no_answers = False
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca_dict[a_tag], 'value_suggested_row': row.id})
                    self.create(vals)

        elif question.matrix_subtype == 'multiple':
            for col in question.labels_ids:
                for row in question.labels_ids_2:
                    a_tag = "%s_%s_%s" % (answer_tag, row.id, col.id)
                    if a_tag in ca_dict:
                        no_answers = False
                        vals.update({'answer_type': 'suggestion', 'value_suggested': col.id, 'value_suggested_row': row.id})
                        self.create(vals)
        if no_answers:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(vals)
        return True
