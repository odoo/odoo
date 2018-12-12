# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

email_validator = re.compile(r"[^@]+@[^@]+\.[^@]+")
_logger = logging.getLogger(__name__)


def dict_keys_startswith(dictionary, string):
    """Returns a dictionary containing the elements of <dict> whose keys start with <string>.
        .. note::
            This function uses dictionary comprehensions (Python >= 2.7)
    """
    return {k: v for k, v in dictionary.items() if k.startswith(string)}


class SurveyQuestion(models.Model):
    """ Questions that will be asked in a survey.

        Each question can have one of more suggested answers (eg. in case of
        dropdown choices, multi-answer checkboxes, radio buttons...).

        Technical note:

        survey.question is also the model used for the survey's pages (with the "is_page" field set to True).

        A page corresponds to a "section" in the interface, and the fact that it separates the survey in
        actual pages in the interface depends on the "questions_layout" parameter on the survey.survey model.
        Pages are also used when randomizing questions. The randomization can happen within a "page".

        Using the same model for questions and pages allows to put all the pages and questions together in a o2m field
        (see survey.survey.question_and_page_ids) on the view side and easily reorganize your survey by dragging the
        items around.

        It also removes on level of encoding by directly having 'Add a page' and 'Add a question'
        links on the tree view of questions, enabling a faster encoding.

        However, this has the downside of making the code reading a little bit more complicated.
        Efforts were made at the model level to create computed fields so that the use of these models
        still seems somewhat logical. That means:
        - A survey still has "page_ids" (question_and_page_ids filtered on is_page = True)
        - These "page_ids" still have question_ids (questions located between this page and the next)
        - These "question_ids" still have a "page_id"

        That makes the use and display of these information at view and controller levels easier to understand.
    """

    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence,id'

    # Question metadata
    survey_id = fields.Many2one('survey.survey', string='Survey', ondelete='cascade')
    page_id = fields.Many2one('survey.question', string='Page', compute="_compute_page_id", store=True)
    question_ids = fields.One2many('survey.question', string='Questions', compute="_compute_question_ids")
    scoring_type = fields.Selection(related='survey_id.scoring_type', string='Scoring Type', readonly=True)
    sequence = fields.Integer('Sequence', default=10)
    # Question
    is_page = fields.Boolean('Is a page?')
    questions_selection = fields.Selection(related='survey_id.questions_selection', readonly=True,
        help="If randomized is selected, add the number of random questions next to the section.")
    random_questions_count = fields.Integer('Random questions count', default=1,
        help="Used on randomized sections to take X random questions from all the questions of that section.")
    title = fields.Char('Title', required=True, translate=True)
    question = fields.Char('Question', related="title")
    description = fields.Html('Description', help="Use this field to add additional explanations about your question", translate=True)

    question_type = fields.Selection([
        ('free_text', 'Multiple Lines Text Box'),
        ('textbox', 'Single Line Text Box'),
        ('numerical_box', 'Numerical Value'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('simple_choice', 'Multiple choice: only one answer'),
        ('multiple_choice', 'Multiple choice: multiple answers allowed'),
        ('matrix', 'Matrix')], string='Question Type',
        default='free_text', required=True, oldname='type')
    # simple choice / multiple choice / matrix
    labels_ids = fields.One2many(
        'survey.label', 'question_id', string='Types of answers', copy=True,
        help='Labels used for proposed choices: simple choice, multiple choice and columns of matrix')
    # matrix
    matrix_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    labels_ids_2 = fields.One2many(
        'survey.label', 'question_id_2', string='Rows of the Matrix', copy=True,
        help='Labels used for proposed choices: rows of matrix')
    # Display options
    column_nb = fields.Selection([
        ('12', '1'), ('6', '2'), ('4', '3'), ('3', '4'), ('2', '6')],
        string='Number of columns', default='12',
        help='These options refer to col-xx-[12|6|4|3|2] classes in Bootstrap for dropdown-based simple and multiple choice questions.')
    display_mode = fields.Selection(
        [('columns', 'Radio Buttons'), ('dropdown', 'Selection Box')],
        string='Display Mode', default='columns', help='Display mode of simple choice questions.')
    # Comments
    comments_allowed = fields.Boolean('Show Comments Field')
    comments_message = fields.Char('Comment Message', translate=True, default=lambda self: _("If other, please specify:"))
    comment_count_as_answer = fields.Boolean('Comment Field is an Answer Choice')
    # Validation
    validation_required = fields.Boolean('Validate entry')
    validation_email = fields.Boolean('Input must be an email')
    validation_length_min = fields.Integer('Minimum Text Length')
    validation_length_max = fields.Integer('Maximum Text Length')
    validation_min_float_value = fields.Float('Minimum value')
    validation_max_float_value = fields.Float('Maximum value')
    validation_min_date = fields.Date('Minimum Date')
    validation_max_date = fields.Date('Maximum Date')
    validation_min_datetime = fields.Datetime('Minimum Datetime')
    validation_max_datetime = fields.Datetime('Maximum Datetime')
    validation_error_msg = fields.Char('Validation Error message', translate=True, default=lambda self: _("The answer you entered is not valid."))
    # Constraints on number of answers (matrices)
    constr_mandatory = fields.Boolean('Mandatory Answer')
    constr_error_msg = fields.Char('Error message', translate=True, default=lambda self: _("This question requires an answer."))
    # Answer
    user_input_line_ids = fields.One2many(
        'survey.user_input_line', 'question_id', string='Answers',
        domain=[('skipped', '=', False)], groups='survey.group_survey_user')

    _sql_constraints = [
        ('positive_len_min', 'CHECK (validation_length_min >= 0)', 'A length must be positive!'),
        ('positive_len_max', 'CHECK (validation_length_max >= 0)', 'A length must be positive!'),
        ('validation_length', 'CHECK (validation_length_min <= validation_length_max)', 'Max length cannot be smaller than min length!'),
        ('validation_float', 'CHECK (validation_min_float_value <= validation_max_float_value)', 'Max value cannot be smaller than min value!'),
        ('validation_date', 'CHECK (validation_min_date <= validation_max_date)', 'Max date cannot be smaller than min date!'),
        ('validation_datetime', 'CHECK (validation_min_datetime <= validation_max_datetime)','Max datetime cannot be smaller than min datetime!')
    ]

    @api.onchange('validation_email')
    def onchange_validation_email(self):
        if self.validation_email:
            self.validation_required = False

    # Validation methods

    @api.multi
    def validate_question(self, post, answer_tag):
        """ Validate question, depending on question type and parameters """
        self.ensure_one()
        try:
            checker = getattr(self, 'validate_' + self.question_type)
        except AttributeError:
            _logger.warning(self.question_type + ": This type of question has no validation method")
            return {}
        else:
            return checker(post, answer_tag)

    @api.multi
    def validate_free_text(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        return errors

    @api.multi
    def validate_textbox(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        # Email format validation
        # Note: this validation is very basic:
        #     all the strings of the form
        #     <something>@<anything>.<extension>
        #     will be accepted
        if answer and self.validation_email:
            if not email_validator.match(answer):
                errors.update({answer_tag: _('This answer must be an email address')})
        # Answer validation (if properly defined)
        # Length of the answer must be in a range
        if answer and self.validation_required:
            if not (self.validation_length_min <= len(answer) <= self.validation_length_max):
                errors.update({answer_tag: self.validation_error_msg})
        return errors

    @api.multi
    def validate_numerical_box(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        # Checks if user input is a number
        if answer:
            try:
                floatanswer = float(answer)
            except ValueError:
                errors.update({answer_tag: _('This is not a number')})
        # Answer validation (if properly defined)
        if answer and self.validation_required:
            # Answer is not in the right range
            with tools.ignore(Exception):
                floatanswer = float(answer)  # check that it is a float has been done hereunder
                if not (self.validation_min_float_value <= floatanswer <= self.validation_max_float_value):
                    errors.update({answer_tag: self.validation_error_msg})
        return errors

    def date_validation(self, date_type, post, answer_tag, min_value, max_value):
        self.ensure_one()
        errors = {}
        if date_type not in ('date', 'datetime'):
            raise ValueError("Unexpected date type value")
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        # Checks if user input is a date
        if answer:
            try:
                if date_type == 'datetime':
                    dateanswer = fields.Datetime.from_string(answer)
                else:
                    dateanswer = fields.Date.from_string(answer)
            except ValueError:
                errors.update({answer_tag: _('This is not a date')})
                return errors
        # Answer validation (if properly defined)
        if answer and self.validation_required:
            # Answer is not in the right range
            try:
                if date_type == 'datetime':
                    date_from_string = fields.Datetime.from_string
                else:
                    date_from_string = fields.Date.from_string
                dateanswer = date_from_string(answer)
                min_date = date_from_string(min_value)
                max_date = date_from_string(max_value)

                if min_date and max_date and not (min_date <= dateanswer <= max_date):
                    # If Minimum and Maximum Date are entered
                    errors.update({answer_tag: self.validation_error_msg})
                elif min_date and not min_date <= dateanswer:
                    # If only Minimum Date is entered and not Define Maximum Date
                    errors.update({answer_tag: self.validation_error_msg})
                elif max_date and not dateanswer <= max_date:
                    # If only Maximum Date is entered and not Define Minimum Date
                    errors.update({answer_tag: self.validation_error_msg})
            except ValueError:  # check that it is a date has been done hereunder
                pass
        return errors

    @api.multi
    def validate_date(self, post, answer_tag):
        return self.date_validation('date', post, answer_tag, self.validation_min_date, self.validation_max_date)

    @api.multi
    def validate_datetime(self, post, answer_tag):
        return self.date_validation('datetime', post, answer_tag, self.validation_min_datetime, self.validation_max_datetime)

    @api.multi
    def validate_simple_choice(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        if self.comments_allowed:
            comment_tag = "%s_%s" % (answer_tag, 'comment')
        # Empty answer to mandatory self
        if self.constr_mandatory and answer_tag not in post:
            errors.update({answer_tag: self.constr_error_msg})
        if self.constr_mandatory and answer_tag in post and not post[answer_tag].strip():
            errors.update({answer_tag: self.constr_error_msg})
        # Answer is a comment and is empty
        if self.constr_mandatory and answer_tag in post and post[answer_tag] == "-1" and self.comment_count_as_answer and comment_tag in post and not post[comment_tag].strip():
            errors.update({answer_tag: self.constr_error_msg})
        return errors

    @api.multi
    def validate_multiple_choice(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        if self.constr_mandatory:
            answer_candidates = dict_keys_startswith(post, answer_tag)
            comment_flag = answer_candidates.pop(("%s_%s" % (answer_tag, -1)), None)
            if self.comments_allowed:
                comment_answer = answer_candidates.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
            # Preventing answers with blank value
            if all(not answer.strip() for answer in answer_candidates.values()) and answer_candidates:
                errors.update({answer_tag: self.constr_error_msg})
            # There is no answer neither comments (if comments count as answer)
            if not answer_candidates and self.comment_count_as_answer and (not comment_flag or not comment_answer):
                errors.update({answer_tag: self.constr_error_msg})
            # There is no answer at all
            if not answer_candidates and not self.comment_count_as_answer:
                errors.update({answer_tag: self.constr_error_msg})
        return errors

    @api.multi
    def validate_matrix(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        if self.constr_mandatory:
            lines_number = len(self.labels_ids_2)
            answer_candidates = dict_keys_startswith(post, answer_tag)
            answer_candidates.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
            # Number of lines that have been answered
            if self.matrix_subtype == 'simple':
                answer_number = len(answer_candidates)
            elif self.matrix_subtype == 'multiple':
                answer_number = len({sk.rsplit('_', 1)[0] for sk in answer_candidates})
            else:
                raise RuntimeError("Invalid matrix subtype")
            # Validate that each line has been answered
            if answer_number != lines_number:
                errors.update({answer_tag: self.constr_error_msg})
        return errors

    @api.multi
    @api.depends('survey_id.question_and_page_ids.is_page', 'survey_id.question_and_page_ids.sequence')
    def _compute_question_ids(self):
        """Will take all questions of the survey for which the index is higher than the index of this page
        and lower than the index of the next page."""
        for question in self:
            if question.is_page:
                next_page_index = False
                for page in question.survey_id.page_ids:
                    if page._index() > question._index():
                        next_page_index = page._index()
                        break

                question.question_ids = question.survey_id.question_ids.filtered(lambda q:
                    q._index() > question._index() and (not next_page_index or q._index() < next_page_index))
            else:
                question.question_ids = self.env['survey.question']

    @api.multi
    @api.depends('survey_id.question_and_page_ids.is_page', 'survey_id.question_and_page_ids.sequence')
    def _compute_page_id(self):
        """Will find the page to which this question belongs to by looking inside the corresponding survey"""
        for question in self:
            if question.is_page:
                question.page_id = None
            else:
                question.page_id = next(
                    (iter(question
                        .survey_id
                        .question_and_page_ids
                        .filtered(lambda q: q.is_page and q.sequence < question.sequence)
                        .sorted(reverse=True))),
                    None
                )

    @api.multi
    def _index(self):
        """We would normally just use the 'sequence' field of questions BUT, if the pages and questions are
        created without ever moving records around, the sequence field can be set to 0 for all the questions.

        However, the order of the recordset is always correct so we can rely on the index method."""
        self.ensure_one()
        return list(self.survey_id.question_and_page_ids).index(self)

    def get_correct_answer_ids(self):
        self.ensure_one()

        return self.labels_ids.filtered(lambda label: label.is_correct)

class SurveyLabel(models.Model):
    """ A suggested answer for a question """
    _name = 'survey.label'
    _rec_name = 'value'
    _order = 'sequence,id'
    _description = 'Survey Label'

    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade')
    question_id_2 = fields.Many2one('survey.question', string='Question 2', ondelete='cascade')
    sequence = fields.Integer('Label Sequence order', default=10)
    value = fields.Char('Suggested value', translate=True, required=True)
    is_correct = fields.Boolean('Is a correct answer')
    answer_score = fields.Float('Score for this choice',
    help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    @api.constrains('question_id', 'question_id_2')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field question_id_2 is not null"""
        for label in self:
            if not bool(label.question_id) != bool(label.question_id_2):
                raise ValidationError(_("A label must be attached to only one question."))
