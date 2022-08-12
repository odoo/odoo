# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import contextlib
import json
import itertools
import operator

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class SurveyQuestion(models.Model):
    """ Questions that will be asked in a survey.

        Each question can have one of more suggested answers (eg. in case of
        multi-answer checkboxes, radio buttons...).

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
    _rec_name = 'title'
    _order = 'sequence,id'

    # question generic data
    title = fields.Char('Title', required=True, translate=True)
    description = fields.Html(
        'Description', translate=True, sanitize=False,  # TDE TODO: sanitize but find a way to keep youtube iframe media stuff
        help="Use this field to add additional explanations about your question or to illustrate it with pictures or a video")
    question_placeholder = fields.Char("Placeholder", translate=True, compute="_compute_question_placeholder", store=True, readonly=False)
    background_image = fields.Image("Background Image", compute="_compute_background_image", store=True, readonly=False)
    background_image_url = fields.Char("Background Url", compute="_compute_background_image_url")
    survey_id = fields.Many2one('survey.survey', string='Survey', ondelete='cascade')
    scoring_type = fields.Selection(related='survey_id.scoring_type', string='Scoring Type', readonly=True)
    sequence = fields.Integer('Sequence', default=10)
    # page specific
    is_page = fields.Boolean('Is a page?')
    question_ids = fields.One2many('survey.question', string='Questions', compute="_compute_question_ids")
    questions_selection = fields.Selection(
        related='survey_id.questions_selection', readonly=True,
        help="If randomized is selected, add the number of random questions next to the section.")
    random_questions_count = fields.Integer(
        '# Questions Randomly Picked', default=1,
        help="Used on randomized sections to take X random questions from all the questions of that section.")
    # question specific
    page_id = fields.Many2one('survey.question', string='Page', compute="_compute_page_id", store=True)
    question_type = fields.Selection([
        ('simple_choice', 'Multiple choice: only one answer'),
        ('multiple_choice', 'Multiple choice: multiple answers allowed'),
        ('text_box', 'Multiple Lines Text Box'),
        ('char_box', 'Single Line Text Box'),
        ('numerical_box', 'Numerical Value'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('matrix', 'Matrix')], string='Question Type',
        compute='_compute_question_type', readonly=False, store=True)
    is_scored_question = fields.Boolean(
        'Scored', compute='_compute_is_scored_question',
        readonly=False, store=True, copy=True,
        help="Include this question as part of quiz scoring. Requires an answer and answer score to be taken into account.")
    # -- scoreable/answerable simple answer_types: numerical_box / date / datetime
    answer_numerical_box = fields.Float('Correct numerical answer', help="Correct number answer for this question.")
    answer_date = fields.Date('Correct date answer', help="Correct date answer for this question.")
    answer_datetime = fields.Datetime('Correct datetime answer', help="Correct date and time answer for this question.")
    answer_score = fields.Float('Score', help="Score value for a correct answer to this question.")
    # -- char_box
    save_as_email = fields.Boolean(
        "Save as user email", compute='_compute_save_as_email', readonly=False, store=True, copy=True,
        help="If checked, this option will save the user's answer as its email address.")
    save_as_nickname = fields.Boolean(
        "Save as user nickname", compute='_compute_save_as_nickname', readonly=False, store=True, copy=True,
        help="If checked, this option will save the user's answer as its nickname.")
    # -- simple choice / multiple choice / matrix
    suggested_answer_ids = fields.One2many(
        'survey.question.answer', 'question_id', string='Types of answers', copy=True,
        help='Labels used for proposed choices: simple choice, multiple choice and columns of matrix')
    # -- matrix
    matrix_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    matrix_row_ids = fields.One2many(
        'survey.question.answer', 'matrix_question_id', string='Matrix Rows', copy=True,
        help='Labels used for proposed choices: rows of matrix')
    # -- display & timing options
    is_time_limited = fields.Boolean("The question is limited in time",
        help="Currently only supported for live sessions.")
    time_limit = fields.Integer("Time limit (seconds)")
    # -- comments (simple choice, multiple choice, matrix (without count as an answer))
    comments_allowed = fields.Boolean('Show Comments Field')
    comments_message = fields.Char('Comment Message', translate=True, default=lambda self: _("If other, please specify:"))
    comment_count_as_answer = fields.Boolean('Comment Field is an Answer Choice')
    # question validation
    validation_required = fields.Boolean('Validate entry', compute='_compute_validation_required', readonly=False, store=True)
    validation_email = fields.Boolean('Input must be an email')
    validation_length_min = fields.Integer('Minimum Text Length', default=0)
    validation_length_max = fields.Integer('Maximum Text Length', default=0)
    validation_min_float_value = fields.Float('Minimum value', default=0.0)
    validation_max_float_value = fields.Float('Maximum value', default=0.0)
    validation_min_date = fields.Date('Minimum Date')
    validation_max_date = fields.Date('Maximum Date')
    validation_min_datetime = fields.Datetime('Minimum Datetime')
    validation_max_datetime = fields.Datetime('Maximum Datetime')
    validation_error_msg = fields.Char('Validation Error message', translate=True, default=lambda self: _("The answer you entered is not valid."))
    constr_mandatory = fields.Boolean('Mandatory Answer')
    constr_error_msg = fields.Char('Error message', translate=True, default=lambda self: _("This question requires an answer."))
    # answers
    user_input_line_ids = fields.One2many(
        'survey.user_input.line', 'question_id', string='Answers',
        domain=[('skipped', '=', False)], groups='survey.group_survey_user')

    # Conditional display
    is_conditional = fields.Boolean(
        string='Conditional Display', copy=True, help="""If checked, this question will be displayed only
        if the specified conditional answer have been selected in a previous question""")
    triggering_question_id = fields.Many2one(
        'survey.question', string="Triggering Question", copy=False, compute="_compute_triggering_question_id",
        store=True, readonly=False, help="Question containing the triggering answer to display the current question.",
        domain="[('survey_id', '=', survey_id), \
                 '&', ('question_type', 'in', ['simple_choice', 'multiple_choice']), \
                 '|', \
                     ('sequence', '<', sequence), \
                     '&', ('sequence', '=', sequence), ('id', '<', id)]")
    triggering_answer_id = fields.Many2one(
        'survey.question.answer', string="Triggering Answer", copy=False, compute="_compute_triggering_answer_id",
        store=True, readonly=False, help="Answer that will trigger the display of the current question.",
        domain="[('question_id', '=', triggering_question_id)]")

    _sql_constraints = [
        ('positive_len_min', 'CHECK (validation_length_min >= 0)', 'A length must be positive!'),
        ('positive_len_max', 'CHECK (validation_length_max >= 0)', 'A length must be positive!'),
        ('validation_length', 'CHECK (validation_length_min <= validation_length_max)', 'Max length cannot be smaller than min length!'),
        ('validation_float', 'CHECK (validation_min_float_value <= validation_max_float_value)', 'Max value cannot be smaller than min value!'),
        ('validation_date', 'CHECK (validation_min_date <= validation_max_date)', 'Max date cannot be smaller than min date!'),
        ('validation_datetime', 'CHECK (validation_min_datetime <= validation_max_datetime)', 'Max datetime cannot be smaller than min datetime!'),
        ('positive_answer_score', 'CHECK (answer_score >= 0)', 'An answer score for a non-multiple choice question cannot be negative!'),
        ('scored_datetime_have_answers', "CHECK (is_scored_question != True OR question_type != 'datetime' OR answer_datetime is not null)",
            'All "Is a scored question = True" and "Question Type: Datetime" questions need an answer'),
        ('scored_date_have_answers', "CHECK (is_scored_question != True OR question_type != 'date' OR answer_date is not null)",
            'All "Is a scored question = True" and "Question Type: Date" questions need an answer')
    ]

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains("is_page")
    def _check_question_type_for_pages(self):
        invalid_pages = self.filtered(lambda question: question.is_page and question.question_type)
        if invalid_pages:
            raise ValidationError(_("Question type should be empty for these pages: %s", ', '.join(invalid_pages.mapped('title'))))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('question_type')
    def _compute_question_placeholder(self):
        for question in self:
            if question.question_type in ('simple_choice', 'multiple_choice', 'matrix') \
                    or not question.question_placeholder:  # avoid CacheMiss errors
                question.question_placeholder = False

    @api.depends('is_page')
    def _compute_background_image(self):
        """ Background image is only available on sections. """
        for question in self.filtered(lambda q: not q.is_page):
            question.background_image = False

    @api.depends('survey_id.access_token', 'background_image', 'page_id', 'survey_id.background_image_url')
    def _compute_background_image_url(self):
        """ How the background url is computed:
        - For a question: it depends on the related section (see below)
        - For a section:
            - if a section has a background, then we create the background URL using this section's ID
            - if not, then we fallback on the survey background url """
        base_bg_url = "/survey/%s/%s/get_background_image"
        for question in self:
            if question.is_page:
                background_section_id = question.id if question.background_image else False
            else:
                background_section_id = question.page_id.id if question.page_id.background_image else False

            if background_section_id:
                question.background_image_url = base_bg_url % (
                    question.survey_id.access_token,
                    background_section_id
                )
            else:
                question.background_image_url = question.survey_id.background_image_url

    @api.depends('is_page')
    def _compute_question_type(self):
        pages = self.filtered(lambda question: question.is_page)
        pages.question_type = False
        (self - pages).filtered(lambda question: not question.question_type).question_type = 'simple_choice'

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

                question.question_ids = question.survey_id.question_ids.filtered(
                    lambda q: q._index() > question._index() and (not next_page_index or q._index() < next_page_index)
                )
            else:
                question.question_ids = self.env['survey.question']

    @api.depends('survey_id.question_and_page_ids.is_page', 'survey_id.question_and_page_ids.sequence')
    def _compute_page_id(self):
        """Will find the page to which this question belongs to by looking inside the corresponding survey"""
        for question in self:
            if question.is_page:
                question.page_id = None
            else:
                page = None
                for q in question.survey_id.question_and_page_ids.sorted():
                    if q == question:
                        break
                    if q.is_page:
                        page = q
                question.page_id = page

    @api.depends('question_type', 'validation_email')
    def _compute_save_as_email(self):
        for question in self:
            if question.question_type != 'char_box' or not question.validation_email:
                question.save_as_email = False

    @api.depends('question_type')
    def _compute_save_as_nickname(self):
        for question in self:
            if question.question_type != 'char_box':
                question.save_as_nickname = False

    @api.depends('question_type')
    def _compute_validation_required(self):
        for question in self:
            if not question.validation_required or question.question_type not in ['char_box', 'numerical_box', 'date', 'datetime']:
                question.validation_required = False

    @api.depends('is_conditional')
    def _compute_triggering_question_id(self):
        """ Used as an 'onchange' : Reset the triggering question if user uncheck 'Conditional Display'
            Avoid CacheMiss : set the value to False if the value is not set yet."""
        for question in self:
            if not question.is_conditional or question.triggering_question_id is None:
                question.triggering_question_id = False

    @api.depends('triggering_question_id')
    def _compute_triggering_answer_id(self):
        """ Used as an 'onchange' : Reset the triggering answer if user unset or change the triggering question
            or uncheck 'Conditional Display'.
            Avoid CacheMiss : set the value to False if the value is not set yet."""
        for question in self:
            if not question.triggering_question_id \
                    or question.triggering_question_id != question.triggering_answer_id.question_id\
                    or question.triggering_answer_id is None:
                question.triggering_answer_id = False

    @api.depends('question_type', 'scoring_type', 'answer_date', 'answer_datetime', 'answer_numerical_box')
    def _compute_is_scored_question(self):
        """ Computes whether a question "is scored" or not. Handles following cases:
          - inconsistent Boolean=None edge case that breaks tests => False
          - survey is not scored => False
          - 'date'/'datetime'/'numerical_box' question types w/correct answer => True
            (implied without user having to activate, except for numerical whose correct value is 0.0)
          - 'simple_choice / multiple_choice': set to True even if logic is a bit different (coming from answers)
          - question_type isn't scoreable (note: choice questions scoring logic handled separately) => False
        """
        for question in self:
            if question.is_scored_question is None or question.scoring_type == 'no_scoring':
                question.is_scored_question = False
            elif question.question_type == 'date':
                question.is_scored_question = bool(question.answer_date)
            elif question.question_type == 'datetime':
                question.is_scored_question = bool(question.answer_datetime)
            elif question.question_type == 'numerical_box' and question.answer_numerical_box:
                question.is_scored_question = True
            elif question.question_type in ['simple_choice', 'multiple_choice']:
                question.is_scored_question = True
            else:
                question.is_scored_question = False

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    def validate_question(self, answer, comment=None):
        """ Validate question, depending on question type and parameters
         for simple choice, text, date and number, answer is simply the answer of the question.
         For other multiple choices questions, answer is a list of answers (the selected choices
         or a list of selected answers per question -for matrix type-):
            - Simple answer : answer = 'example' or 2 or question_answer_id or 2019/10/10
            - Multiple choice : answer = [question_answer_id1, question_answer_id2, question_answer_id3]
            - Matrix: answer = { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] }

         return dict {question.id (int): error (str)} -> empty dict if no validation error.
         """
        self.ensure_one()
        if isinstance(answer, str):
            answer = answer.strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer and self.question_type not in ['simple_choice', 'multiple_choice']:
            return {self.id: self.constr_error_msg}

        # because in choices question types, comment can count as answer
        if answer or self.question_type in ['simple_choice', 'multiple_choice']:
            if self.question_type == 'char_box':
                return self._validate_char_box(answer)
            elif self.question_type == 'numerical_box':
                return self._validate_numerical_box(answer)
            elif self.question_type in ['date', 'datetime']:
                return self._validate_date(answer)
            elif self.question_type in ['simple_choice', 'multiple_choice']:
                return self._validate_choice(answer, comment)
            elif self.question_type == 'matrix':
                return self._validate_matrix(answer)
        return {}

    def _validate_char_box(self, answer):
        # Email format validation
        # all the strings of the form "<something>@<anything>.<extension>" will be accepted
        if self.validation_email:
            if not tools.email_normalize(answer):
                return {self.id: _('This answer must be an email address')}

        # Answer validation (if properly defined)
        # Length of the answer must be in a range
        if self.validation_required:
            if not (self.validation_length_min <= len(answer) <= self.validation_length_max):
                return {self.id: self.validation_error_msg}
        return {}

    def _validate_numerical_box(self, answer):
        try:
            floatanswer = float(answer)
        except ValueError:
            return {self.id: _('This is not a number')}

        if self.validation_required:
            # Answer is not in the right range
            with contextlib.suppress(Exception):
                if not (self.validation_min_float_value <= floatanswer <= self.validation_max_float_value):
                    return {self.id: self.validation_error_msg}
        return {}

    def _validate_date(self, answer):
        isDatetime = self.question_type == 'datetime'
        # Checks if user input is a date
        try:
            dateanswer = fields.Datetime.from_string(answer) if isDatetime else fields.Date.from_string(answer)
        except ValueError:
            return {self.id: _('This is not a date')}
        if self.validation_required:
            # Check if answer is in the right range
            if isDatetime:
                min_date = fields.Datetime.from_string(self.validation_min_datetime)
                max_date = fields.Datetime.from_string(self.validation_max_datetime)
                dateanswer = fields.Datetime.from_string(answer)
            else:
                min_date = fields.Date.from_string(self.validation_min_date)
                max_date = fields.Date.from_string(self.validation_max_date)
                dateanswer = fields.Date.from_string(answer)

            if (min_date and max_date and not (min_date <= dateanswer <= max_date))\
                    or (min_date and not min_date <= dateanswer)\
                    or (max_date and not dateanswer <= max_date):
                return {self.id: self.validation_error_msg}
        return {}

    def _validate_choice(self, answer, comment):
        # Empty comment
        if self.constr_mandatory \
                and not answer \
                and not (self.comments_allowed and self.comment_count_as_answer and comment):
            return {self.id: self.constr_error_msg}
        return {}

    def _validate_matrix(self, answers):
        # Validate that each line has been answered
        if self.constr_mandatory and len(self.matrix_row_ids) != len(answers):
            return {self.id: self.constr_error_msg}
        return {}

    def _index(self):
        """We would normally just use the 'sequence' field of questions BUT, if the pages and questions are
        created without ever moving records around, the sequence field can be set to 0 for all the questions.

        However, the order of the recordset is always correct so we can rely on the index method."""
        self.ensure_one()
        return list(self.survey_id.question_and_page_ids).index(self)

    # ------------------------------------------------------------
    # STATISTICS / REPORTING
    # ------------------------------------------------------------

    def _prepare_statistics(self, user_input_lines):
        """ Compute statistical data for questions by counting number of vote per choice on basis of filter """
        all_questions_data = []
        for question in self:
            question_data = {'question': question, 'is_page': question.is_page}

            if question.is_page:
                all_questions_data.append(question_data)
                continue

            # fetch answer lines, separate comments from real answers
            all_lines = user_input_lines.filtered(lambda line: line.question_id == question)
            if question.question_type in ['simple_choice', 'multiple_choice', 'matrix']:
                answer_lines = all_lines.filtered(
                    lambda line: line.answer_type == 'suggestion' or (
                        line.skipped and not line.answer_type) or (
                        line.answer_type == 'char_box' and question.comment_count_as_answer)
                    )
                comment_line_ids = all_lines.filtered(lambda line: line.answer_type == 'char_box')
            else:
                answer_lines = all_lines
                comment_line_ids = self.env['survey.user_input.line']
            skipped_lines = answer_lines.filtered(lambda line: line.skipped)
            done_lines = answer_lines - skipped_lines
            question_data.update(
                answer_line_ids=answer_lines,
                answer_line_done_ids=done_lines,
                answer_input_done_ids=done_lines.mapped('user_input_id'),
                answer_input_skipped_ids=skipped_lines.mapped('user_input_id'),
                comment_line_ids=comment_line_ids)
            question_data.update(question._get_stats_summary_data(answer_lines))

            # prepare table and graph data
            table_data, graph_data = question._get_stats_data(answer_lines)
            question_data['table_data'] = table_data
            question_data['graph_data'] = json.dumps(graph_data)

            all_questions_data.append(question_data)
        return all_questions_data

    def _get_stats_data(self, user_input_lines):
        if self.question_type == 'simple_choice':
            return self._get_stats_data_answers(user_input_lines)
        elif self.question_type == 'multiple_choice':
            table_data, graph_data = self._get_stats_data_answers(user_input_lines)
            return table_data, [{'key': self.title, 'values': graph_data}]
        elif self.question_type == 'matrix':
            return self._get_stats_graph_data_matrix(user_input_lines)
        return [line for line in user_input_lines], []

    def _get_stats_data_answers(self, user_input_lines):
        """ Statistics for question.answer based questions (simple choice, multiple
        choice.). A corner case with a void record survey.question.answer is added
        to count comments that should be considered as valid answers. This small hack
        allow to have everything available in the same standard structure. """
        suggested_answers = [answer for answer in self.mapped('suggested_answer_ids')]
        if self.comment_count_as_answer:
            suggested_answers += [self.env['survey.question.answer']]

        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if line.suggested_answer_id in count_data\
               or (line.value_char_box and self.comment_count_as_answer):
                count_data[line.suggested_answer_id] += 1

        table_data = [{
            'value': _('Other (see comments)') if not sug_answer else sug_answer.value,
            'suggested_answer': sug_answer,
            'count': count_data[sug_answer]
            }
            for sug_answer in suggested_answers]
        graph_data = [{
            'text': _('Other (see comments)') if not sug_answer else sug_answer.value,
            'count': count_data[sug_answer]
            }
            for sug_answer in suggested_answers]

        return table_data, graph_data

    def _get_stats_graph_data_matrix(self, user_input_lines):
        suggested_answers = self.mapped('suggested_answer_ids')
        matrix_rows = self.mapped('matrix_row_ids')

        count_data = dict.fromkeys(itertools.product(matrix_rows, suggested_answers), 0)
        for line in user_input_lines:
            if line.matrix_row_id and line.suggested_answer_id:
                count_data[(line.matrix_row_id, line.suggested_answer_id)] += 1

        table_data = [{
            'row': row,
            'columns': [{
                'suggested_answer': sug_answer,
                'count': count_data[(row, sug_answer)]
            } for sug_answer in suggested_answers],
        } for row in matrix_rows]
        graph_data = [{
            'key': sug_answer.value,
            'values': [{
                'text': row.value,
                'count': count_data[(row, sug_answer)]
                }
                for row in matrix_rows
            ]
        } for sug_answer in suggested_answers]

        return table_data, graph_data

    def _get_stats_summary_data(self, user_input_lines):
        stats = {}
        if self.question_type in ['simple_choice', 'multiple_choice']:
            stats.update(self._get_stats_summary_data_choice(user_input_lines))
        elif self.question_type == 'numerical_box':
            stats.update(self._get_stats_summary_data_numerical(user_input_lines))

        if self.question_type in ['numerical_box', 'date', 'datetime']:
            stats.update(self._get_stats_summary_data_scored(user_input_lines))
        return stats

    def _get_stats_summary_data_choice(self, user_input_lines):
        right_inputs, partial_inputs = self.env['survey.user_input'], self.env['survey.user_input']
        right_answers = self.suggested_answer_ids.filtered(lambda label: label.is_correct)
        if self.question_type == 'multiple_choice':
            for user_input, lines in tools.groupby(user_input_lines, operator.itemgetter('user_input_id')):
                user_input_answers = self.env['survey.user_input.line'].concat(*lines).filtered(lambda l: l.answer_is_correct).mapped('suggested_answer_id')
                if user_input_answers and user_input_answers < right_answers:
                    partial_inputs += user_input
                elif user_input_answers:
                    right_inputs += user_input
        else:
            right_inputs = user_input_lines.filtered(lambda line: line.answer_is_correct).mapped('user_input_id')
        return {
            'right_answers': right_answers,
            'right_inputs_count': len(right_inputs),
            'partial_inputs_count': len(partial_inputs),
        }

    def _get_stats_summary_data_numerical(self, user_input_lines):
        all_values = user_input_lines.filtered(lambda line: not line.skipped).mapped('value_numerical_box')
        lines_sum = sum(all_values)
        return {
            'numerical_max': max(all_values, default=0),
            'numerical_min': min(all_values, default=0),
            'numerical_average': round(lines_sum / (len(all_values) or 1), 2),
        }

    def _get_stats_summary_data_scored(self, user_input_lines):
        return {
            'common_lines': collections.Counter(
                user_input_lines.filtered(lambda line: not line.skipped).mapped('value_%s' % self.question_type)
            ).most_common(5),
            'right_inputs_count': len(user_input_lines.filtered(lambda line: line.answer_is_correct).mapped('user_input_id'))
        }


class SurveyQuestionAnswer(models.Model):
    """ A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;
      * matrix: row and column values;

    """
    _name = 'survey.question.answer'
    _rec_name = 'value'
    _order = 'sequence, id'
    _description = 'Survey Label'

    # question and question related fields
    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade')
    matrix_question_id = fields.Many2one('survey.question', string='Question (as matrix row)', ondelete='cascade')
    question_type = fields.Selection(related='question_id.question_type')
    sequence = fields.Integer('Label Sequence order', default=10)
    scoring_type = fields.Selection(related='question_id.scoring_type')
    # answer related fields
    value = fields.Char('Suggested value', translate=True, required=True)
    value_image = fields.Image('Image', max_width=1024, max_height=1024)
    value_image_filename = fields.Char('Image Filename')
    is_correct = fields.Boolean('Correct')
    answer_score = fields.Float('Score', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    @api.constrains('question_id', 'matrix_question_id')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field matrix_question_id is not null"""
        for label in self:
            if not bool(label.question_id) != bool(label.matrix_question_id):
                raise ValidationError(_("A label must be attached to only one question."))
