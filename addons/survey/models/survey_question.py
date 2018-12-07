# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

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
    """

    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence,id'

    # Model fields #

    # Question metadata
    page_id = fields.Many2one('survey.page', string='Survey page',
            ondelete='cascade', required=True, default=lambda self: self.env.context.get('page_id'))
    survey_id = fields.Many2one('survey.survey', related='page_id.survey_id', string='Survey', readonly=False)
    sequence = fields.Integer('Sequence', default=10)

    # Question
    question = fields.Char('Question Name', required=True, translate=True)
    description = fields.Html('Description', help="Use this field to add \
        additional explanations about your question", translate=True,
        oldname='descriptive_text')

    # Answer
    question_type = fields.Selection([
            ('free_text', 'Multiple Lines Text Box'),
            ('textbox', 'Single Line Text Box'),
            ('numerical_box', 'Numerical Value'),
            ('date', 'Date'),
            ('simple_choice', 'Multiple choice: only one answer'),
            ('multiple_choice', 'Multiple choice: multiple answers allowed'),
            ('matrix', 'Matrix')], string='Type of Question', default='free_text', required=True, oldname='type')
    matrix_subtype = fields.Selection([('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    labels_ids = fields.One2many('survey.label', 'question_id', string='Types of answers', oldname='answer_choice_ids', copy=True)
    labels_ids_2 = fields.One2many('survey.label', 'question_id_2', string='Rows of the Matrix', copy=True)
    # labels are used for proposed choices
    # if question.type == simple choice | multiple choice
    #                    -> only labels_ids is used
    # if question.type == matrix
    #                    -> labels_ids are the columns of the matrix
    #                    -> labels_ids_2 are the rows of the matrix

    # Display options
    column_nb = fields.Selection([('12', '1'),
                                   ('6', '2'),
                                   ('4', '3'),
                                   ('3', '4'),
                                   ('2', '6')],
        'Number of columns', default='12')
    # These options refer to col-xx-[12|6|4|3|2] classes in Bootstrap
    display_mode = fields.Selection([('columns', 'Radio Buttons'),
                                      ('dropdown', 'Selection Box')],
                                    default='columns')

    # Comments
    comments_allowed = fields.Boolean('Show Comments Field',
        oldname="allow_comment")
    comments_message = fields.Char('Comment Message', translate=True, default=lambda self: _("If other, please specify:"))
    comment_count_as_answer = fields.Boolean('Comment Field is an Answer Choice',
        oldname='make_comment_field')

    # Validation
    validation_required = fields.Boolean('Validate entry', oldname='is_validation_require')
    validation_email = fields.Boolean('Input must be an email')
    validation_length_min = fields.Integer('Minimum Text Length')
    validation_length_max = fields.Integer('Maximum Text Length')
    validation_min_float_value = fields.Float('Minimum value')
    validation_max_float_value = fields.Float('Maximum value')
    validation_min_date = fields.Date('Minimum Date')
    validation_max_date = fields.Date('Maximum Date')
    validation_error_msg = fields.Char('Validation Error message', oldname='validation_valid_err_msg',
                                        translate=True, default=lambda self: _("The answer you entered has an invalid format."))

    # Constraints on number of answers (matrices)
    constr_mandatory = fields.Boolean('Mandatory Answer', oldname="is_require_answer")
    constr_error_msg = fields.Char('Error message', oldname='req_error_msg', translate=True, default=lambda self: _("This question requires an answer."))
    user_input_line_ids = fields.One2many('survey.user_input_line', 'question_id', string='Answers', domain=[('skipped', '=', False)])

    _sql_constraints = [
        ('positive_len_min', 'CHECK (validation_length_min >= 0)', 'A length must be positive!'),
        ('positive_len_max', 'CHECK (validation_length_max >= 0)', 'A length must be positive!'),
        ('validation_length', 'CHECK (validation_length_min <= validation_length_max)', 'Max length cannot be smaller than min length!'),
        ('validation_float', 'CHECK (validation_min_float_value <= validation_max_float_value)', 'Max value cannot be smaller than min value!'),
        ('validation_date', 'CHECK (validation_min_date <= validation_max_date)', 'Max date cannot be smaller than min date!')
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

    @api.multi
    def validate_date(self, post, answer_tag):
        self.ensure_one()
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        # Checks if user input is a date
        if answer:
            try:
                dateanswer = fields.Date.from_string(answer)
            except ValueError:
                errors.update({answer_tag: _('This is not a date')})
                return errors
        # Answer validation (if properly defined)
        if answer and self.validation_required:
            # Answer is not in the right range
            try:
                date_from_string = fields.Date.from_string
                dateanswer = date_from_string(answer)
                min_date = date_from_string(self.validation_min_date)
                max_date = date_from_string(self.validation_max_date)

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
    quizz_mark = fields.Float('Score for this choice', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    @api.one
    @api.constrains('question_id', 'question_id_2')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field question_id_2 is not null"""
        if not bool(self.question_id) != bool(self.question_id_2):
            raise ValidationError(_("A label must be attached to only one question."))
