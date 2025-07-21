# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import contextlib
import itertools
import json
import operator
from textwrap import shorten

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


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
        links on the list view of questions, enabling a faster encoding.

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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if default_survey_id := self.env.context.get('default_survey_id'):
            survey = self.env['survey.survey'].browse(default_survey_id)
            if 'is_time_limited' in fields_list and 'is_time_limited' not in res:
                res['is_time_limited'] = survey.session_speed_rating
            if 'time_limit' in fields_list and 'time_limit' not in res:
                res['time_limit'] = survey.session_speed_rating_time_limit
        return res

    # question generic data
    title = fields.Char('Title', required=True, translate=True)
    description = fields.Html(
        'Description', translate=True, sanitize=True, sanitize_overridable=True,
        help="Use this field to add additional explanations about your question or to illustrate it with pictures or a video")
    question_placeholder = fields.Char("Placeholder", translate=True, compute="_compute_question_placeholder", store=True, readonly=False)
    background_image = fields.Image("Background Image", compute="_compute_background_image", store=True, readonly=False)
    background_image_url = fields.Char("Background Url", compute="_compute_background_image_url")
    survey_id = fields.Many2one('survey.survey', string='Survey', ondelete='cascade')
    scoring_type = fields.Selection(related='survey_id.scoring_type', string='Scoring Type', readonly=True)
    sequence = fields.Integer('Sequence', default=10)
    session_available = fields.Boolean(related='survey_id.session_available', string='Live Session available', readonly=True)
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
        ('scale', 'Scale'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('matrix', 'Matrix')], string='Question Type',
        compute='_compute_question_type', readonly=False, store=True)
    is_scored_question = fields.Boolean(
        'Scored', compute='_compute_is_scored_question',
        readonly=False, store=True, copy=True,
        help="Include this question as part of quiz scoring. Requires an answer and answer score to be taken into account.")
    has_image_only_suggested_answer = fields.Boolean(
        "Has image only suggested answer", compute='_compute_has_image_only_suggested_answer')
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
    # -- scale
    scale_min = fields.Integer("Scale Minimum Value", default=0)
    scale_max = fields.Integer("Scale Maximum Value", default=10)
    scale_min_label = fields.Char("Scale Minimum Label", translate=True)
    scale_mid_label = fields.Char("Scale Middle Label", translate=True)
    scale_max_label = fields.Char("Scale Maximum Label", translate=True)
    # -- display & timing options
    is_time_limited = fields.Boolean("The question is limited in time",
        help="Currently only supported for live sessions.")
    is_time_customized = fields.Boolean("Customized speed rewards")
    time_limit = fields.Integer("Time limit (seconds)")
    # -- comments (simple choice, multiple choice, matrix (without count as an answer))
    comments_allowed = fields.Boolean('Show Comments Field')
    comments_message = fields.Char('Comment Message', translate=True)
    comment_count_as_answer = fields.Boolean('Comment is an answer')
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
    validation_error_msg = fields.Char('Validation Error', translate=True)
    constr_mandatory = fields.Boolean('Mandatory Answer')
    constr_error_msg = fields.Char('Error message', translate=True)
    # answers
    user_input_line_ids = fields.One2many(
        'survey.user_input.line', 'question_id', string='Answers',
        domain=[('skipped', '=', False)], groups='survey.group_survey_user')

    # Not stored, convenient for trigger display computation.
    triggering_question_ids = fields.Many2many(
        'survey.question', string="Triggering Questions", compute="_compute_triggering_question_ids",
        store=False, help="Questions containing the triggering answer(s) to display the current question.")

    allowed_triggering_question_ids = fields.Many2many(
        'survey.question', string="Allowed Triggering Questions", copy=False, compute="_compute_allowed_triggering_question_ids")
    is_placed_before_trigger = fields.Boolean(
        string='Is misplaced?', help="Is this question placed before any of its trigger questions?",
        compute="_compute_allowed_triggering_question_ids")
    triggering_answer_ids = fields.Many2many(
        'survey.question.answer', string="Triggering Answers", copy=False, store=True,
        readonly=False, help="Picking any of these answers will trigger this question.\n"
                             "Leave the field empty if the question should always be displayed.",
        domain="""[
            ('question_id.survey_id', '=', survey_id),
            '&', ('question_id.question_type', 'in', ['simple_choice', 'multiple_choice']),
                 '|',
                     ('question_id.sequence', '<', sequence),
                     '&', ('question_id.sequence', '=', sequence), ('question_id.id', '<', id)
        ]"""
    )

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
            'All "Is a scored question = True" and "Question Type: Date" questions need an answer'),
        ('scale', "CHECK (question_type != 'scale' OR (scale_min >= 0 AND scale_max <= 10 AND scale_min < scale_max))",
            'The scale must be a growing non-empty range between 0 and 10 (inclusive)'),
        ('is_time_limited_have_time_limit', "CHECK (is_time_limited != TRUE OR time_limit IS NOT NULL AND time_limit > 0)",
            'All time-limited questions need a positive time limit'),
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

    @api.depends('suggested_answer_ids', 'suggested_answer_ids.value')
    def _compute_has_image_only_suggested_answer(self):
        questions_with_image_only_answer = self.env['survey.question'].search(
            [('id', 'in', self.ids), ('suggested_answer_ids.value', 'in', [False, ''])])
        questions_with_image_only_answer.has_image_only_suggested_answer = True
        (self - questions_with_image_only_answer).has_image_only_suggested_answer = False

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
        for question in self:
            if question.is_page:
                question.question_ids = question.survey_id.question_ids\
                    .filtered(lambda q: q.page_id == question).sorted(lambda q: q._index())
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

    @api.depends('survey_id', 'survey_id.question_ids', 'triggering_answer_ids')
    def _compute_allowed_triggering_question_ids(self):
        """Although the question (and possible trigger questions) sequence
        is used here, we do not add these fields to the dependency list to
        avoid cascading rpc calls when reordering questions via the webclient.
        """
        possible_trigger_questions = self.search([
            ('is_page', '=', False),
            ('question_type', 'in', ['simple_choice', 'multiple_choice']),
            ('suggested_answer_ids', '!=', False),
            ('survey_id', 'in', self.survey_id.ids)
        ])
        # Using the sequence stored in db is necessary for existing questions that are passed as
        # NewIds because the sequence provided by the JS client can be incorrect.
        (self | possible_trigger_questions).flush_recordset()
        self.env.cr.execute(
            "SELECT id, sequence FROM survey_question WHERE id =ANY(%s)",
            [self.ids]
        )
        conditional_questions_sequences = dict(self.env.cr.fetchall())  # id: sequence mapping

        for question in self:
            question_id = question._origin.id
            if not question_id:  # New question
                question.allowed_triggering_question_ids = possible_trigger_questions.filtered(
                    lambda q: q.survey_id.id == question.survey_id._origin.id)
                question.is_placed_before_trigger = False
                continue

            question_sequence = conditional_questions_sequences[question_id]

            question.allowed_triggering_question_ids = possible_trigger_questions.filtered(
                lambda q: q.survey_id.id == question.survey_id._origin.id
                and (q.sequence < question_sequence or q.sequence == question_sequence and q.id < question_id)
            )
            question.is_placed_before_trigger = bool(
                set(question.triggering_answer_ids.question_id.ids)
                - set(question.allowed_triggering_question_ids.ids)  # .ids necessary to match ids with newIds
            )

    @api.depends('triggering_answer_ids')
    def _compute_triggering_question_ids(self):
        for question in self:
            question.triggering_question_ids = question.triggering_answer_ids.question_id

    @api.depends('question_type', 'scoring_type', 'answer_date', 'answer_datetime', 'answer_numerical_box', 'suggested_answer_ids.is_correct')
    def _compute_is_scored_question(self):
        """ Computes whether a question "is scored" or not. Handles following cases:
          - inconsistent Boolean=None edge case that breaks tests => False
          - survey is not scored => False
          - 'date'/'datetime'/'numerical_box' question types w/correct answer => True
            (implied without user having to activate, except for numerical whose correct value is 0.0)
          - 'simple_choice / multiple_choice': set to True if any of suggested answers are marked as correct
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
                question.is_scored_question = any(question.suggested_answer_ids.mapped('is_correct'))
            else:
                question.is_scored_question = False

    @api.onchange('question_type', 'validation_required')
    def _onchange_validation_parameters(self):
        """Ensure no value stays set but not visible on form,
        preventing saving (+consistency with question type)."""
        self.validation_email = False
        self.validation_length_min = 0
        self.validation_length_max = 0
        self.validation_min_date = False
        self.validation_max_date = False
        self.validation_min_datetime = False
        self.validation_max_datetime = False
        self.validation_min_float_value = 0
        self.validation_max_float_value = 0

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def copy(self, default=None):
        new_questions = super().copy(default)
        for old_question, new_question in zip(self, new_questions):
            if old_question.triggering_answer_ids:
                new_question.triggering_answer_ids = old_question.triggering_answer_ids
        return new_questions

    def create(self, vals_list):
        questions = super().create(vals_list)
        questions.filtered(
            lambda q: q.survey_id
            and (q.survey_id.session_speed_rating != q.is_time_limited
                 or q.is_time_limited and q.survey_id.session_speed_rating_time_limit != q.time_limit)
        ).is_time_customized = True
        return questions

    @api.ondelete(at_uninstall=False)
    def _unlink_except_live_sessions_in_progress(self):
        running_surveys = self.survey_id.filtered(lambda survey: survey.session_state == 'in_progress')
        if running_surveys:
            raise UserError(_(
                'You cannot delete questions from surveys "%(survey_names)s" while live sessions are in progress.',
                survey_names=', '.join(running_surveys.mapped('title')),
            ))

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
        # because in choices question types, comment can count as answer
        if not answer and self.question_type not in ['simple_choice', 'multiple_choice']:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {self.id: self.constr_error_msg or _('This question requires an answer.')}
        else:
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
            elif self.question_type == 'scale':
                return self._validate_scale(answer)
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
                return {self.id: self.validation_error_msg or _('The answer you entered is not valid.')}
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
                    return {self.id: self.validation_error_msg  or _('The answer you entered is not valid.')}
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
                return {self.id: self.validation_error_msg or _('The answer you entered is not valid.')}
        return {}

    def _validate_choice(self, answer, comment):
        # Empty comment
        if not self.survey_id.users_can_go_back \
                and self.constr_mandatory \
                and not answer \
                and not (self.comments_allowed and self.comment_count_as_answer and comment):
            return {self.id: self.constr_error_msg or _('This question requires an answer.')}
        return {}

    def _validate_matrix(self, answers):
        # Validate that each line has been answered
        if self.constr_mandatory and len(self.matrix_row_ids) != len(answers):
            return {self.id: self.constr_error_msg or _('This question requires an answer.')}
        return {}

    def _validate_scale(self, answer):
        if not self.survey_id.users_can_go_back \
                and self.constr_mandatory \
                and not answer:
            return {self.id: self.constr_error_msg or _('This question requires an answer.')}
        return {}

    def _index(self):
        """We would normally just use the 'sequence' field of questions BUT, if the pages and questions are
        created without ever moving records around, the sequence field can be set to 0 for all the questions.

        However, the order of the recordset is always correct so we can rely on the index method."""
        self.ensure_one()
        return list(self.survey_id.question_and_page_ids).index(self)

    # ------------------------------------------------------------
    # SPEED RATING
    # ------------------------------------------------------------

    def _update_time_limit_from_survey(self, is_time_limited=None, time_limit=None):
        """Update the speed rating values after a change in survey's speed rating configuration.

        * Questions that were not customized will take the new default values from the survey
        * Questions that were customized will not change their values, but this method will check
          and update the `is_time_customized` flag if necessary (to `False`) such that the user
          won't need to "actively" do it to make the question sensitive to change in survey values.

        This is not done with `_compute`s because `is_time_limited` (and `time_limit`) would depend
        on `is_time_customized` and vice versa.
        """
        write_vals = {}
        if is_time_limited is not None:
            write_vals['is_time_limited'] = is_time_limited
        if time_limit is not None:
            write_vals['time_limit'] = time_limit
        non_time_customized_questions = self.filtered(lambda s: not s.is_time_customized)
        non_time_customized_questions.write(write_vals)

        # Reset `is_time_customized` as necessary
        customized_questions = self - non_time_customized_questions
        back_to_default_questions = customized_questions.filtered(
            lambda q: q.is_time_limited == q.survey_id.session_speed_rating
            and (q.is_time_limited is False or q.time_limit == q.survey_id.session_speed_rating_time_limit))
        back_to_default_questions.is_time_customized = False

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
                answer_input_ids=answer_lines.mapped('user_input_id'),
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
        elif self.question_type == 'scale':
            table_data, graph_data = self._get_stats_data_scale(user_input_lines)
            return table_data, [{'key': self.title, 'values': graph_data}]
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
            'value': _('Other (see comments)') if not suggested_answer else suggested_answer.value_label,
            'suggested_answer': suggested_answer,
            'count': count_data[suggested_answer],
            'count_text': self.env._("%s Votes", count_data[suggested_answer]),
            }
            for suggested_answer in suggested_answers]
        graph_data = [{
            'text': self.env._('Other (see comments)') if not suggested_answer else suggested_answer.value_label,
            'count': count_data[suggested_answer]
            }
            for suggested_answer in suggested_answers]

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
                'suggested_answer': suggested_answer,
                'count': count_data[(row, suggested_answer)]
            } for suggested_answer in suggested_answers],
        } for row in matrix_rows]
        graph_data = [{
            'key': suggested_answer.value,
            'values': [{
                'text': row.value,
                'count': count_data[(row, suggested_answer)]
                }
                for row in matrix_rows
            ]
        } for suggested_answer in suggested_answers]

        return table_data, graph_data

    def _get_stats_data_scale(self, user_input_lines):
        suggested_answers = range(self.scale_min, self.scale_max + 1)
        # Scale doesn't support comment as answer, so no extra value added

        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if not line.skipped and line.value_scale in count_data:
                count_data[line.value_scale] += 1

        table_data = []
        graph_data = []
        for sug_answer in suggested_answers:
            table_data.append({'value': str(sug_answer),
                               'suggested_answer': self.env['survey.question.answer'],
                               'count': count_data[sug_answer],
                               'count_text': _("%s Votes", count_data[sug_answer]),
                               })
            graph_data.append({'text': str(sug_answer),
                               'count': count_data[sug_answer]
                               })

        return table_data, graph_data

    def _get_stats_summary_data(self, user_input_lines):
        stats = {}
        if self.question_type in ['simple_choice', 'multiple_choice']:
            stats.update(self._get_stats_summary_data_choice(user_input_lines))
        elif self.question_type == 'numerical_box':
            stats.update(self._get_stats_summary_data_numerical(user_input_lines))
        elif self.question_type == 'scale':
            stats.update(self._get_stats_summary_data_numerical(user_input_lines, 'value_scale'))

        if self.question_type in ['numerical_box', 'date', 'datetime', 'scale']:
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

    def _get_stats_summary_data_numerical(self, user_input_lines, fname='value_numerical_box'):
        all_values = user_input_lines.filtered(lambda line: not line.skipped).mapped(fname)
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

    # ------------------------------------------------------------
    # OTHERS
    # ------------------------------------------------------------

    def _get_correct_answers(self):
        """ Return a dictionary linking the scorable question ids to their correct answers.
        The questions without correct answers are not considered.
        """
        correct_answers = {}

        # Simple and multiple choice
        choices_questions = self.filtered(lambda q: q.question_type in ['simple_choice', 'multiple_choice'])
        if choices_questions:
            suggested_answers_data = self.env['survey.question.answer'].search_read(
                [('question_id', 'in', choices_questions.ids), ('is_correct', '=', True)],
                ['question_id', 'id'],
                load='', # prevent computing display_names
            )
            for data in suggested_answers_data:
                if not data.get('id'):
                    continue
                correct_answers.setdefault(data['question_id'], []).append(data['id'])

        # Numerical box, date, datetime
        for question in self - choices_questions:
            if question.question_type not in ['numerical_box', 'date', 'datetime']:
                continue
            answer = question[f'answer_{question.question_type}']
            if question.question_type == 'date':
                answer = tools.format_date(self.env, answer)
            elif question.question_type == 'datetime':
                answer = tools.format_datetime(self.env, answer, tz='UTC', dt_format=False)
            correct_answers[question.id] = answer

        return correct_answers

class SurveyQuestionAnswer(models.Model):
    """ A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;
      * matrix: row and column values;

    """
    _name = 'survey.question.answer'
    _rec_name = 'value'
    _rec_names_search = ['question_id.title', 'value']
    _order = 'question_id, sequence, id'
    _description = 'Survey Label'

    MAX_ANSWER_NAME_LENGTH = 90  # empirically tested in client dropdown

    # question and question related fields
    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade', index='btree_not_null')
    matrix_question_id = fields.Many2one('survey.question', string='Question (as matrix row)', ondelete='cascade', index='btree_not_null')
    question_type = fields.Selection(related='question_id.question_type')
    sequence = fields.Integer('Label Sequence order', default=10)
    scoring_type = fields.Selection(related='question_id.scoring_type')
    # answer related fields
    value = fields.Char('Suggested value', translate=True)
    value_image = fields.Image('Image', max_width=1024, max_height=1024)
    value_image_filename = fields.Char('Image Filename')
    value_label = fields.Char('Value Label', compute='_compute_value_label',
                              help="Answer label as either the value itself if not empty "
                                   "or a letter representing the index of the answer otherwise.")
    is_correct = fields.Boolean('Correct')
    answer_score = fields.Float('Score', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    _sql_constraints = [
        ('value_not_empty', "CHECK (value IS NOT NULL OR value_image_filename IS NOT NULL)",
         'Suggested answer value must not be empty (a text and/or an image must be provided).'),
    ]

    @api.depends('value_label', 'question_id.question_type', 'question_id.title', 'matrix_question_id')
    def _compute_display_name(self):
        """Render an answer name as "Question title : Answer label value", making sure it is not too long.

        Unless the answer is part of a matrix-type question, this implementation makes sure we have
        at least 30 characters for the question title, then we elide it, leaving the rest of the
        space for the answer.
        """
        for answer in self:
            answer_label = answer.value_label
            if not answer.question_id or answer.question_id.question_type == 'matrix':
                answer.display_name = answer_label
                continue
            title = answer.question_id.title or _("[Question Title]")
            n_extra_characters = len(title) + len(answer_label) + 3 - self.MAX_ANSWER_NAME_LENGTH  # 3 for `" : "`
            if n_extra_characters <= 0:
                answer.display_name = f'{title} : {answer_label}'
            else:
                answer.display_name = shorten(
                    f'{shorten(title, max(30, len(title) - n_extra_characters), placeholder="...")} : {answer_label}',
                    self.MAX_ANSWER_NAME_LENGTH,
                    placeholder="..."
                )

    @api.depends('question_id.suggested_answer_ids', 'sequence', 'value')
    def _compute_value_label(self):
        """ Compute the label as the value if not empty or a letter representing the index of the answer otherwise. """
        for answer in self:
            # using image -> use a letter to represent the value
            if not answer.value and answer.question_id and answer.id:
                answer_idx = answer.question_id.suggested_answer_ids.ids.index(answer.id)
                answer.value_label = chr(65 + answer_idx) if answer_idx < 27 else ''
            else:
                answer.value_label = answer.value or ''

    @api.constrains('question_id', 'matrix_question_id')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field matrix_question_id is not null"""
        for label in self:
            if not bool(label.question_id) != bool(label.matrix_question_id):
                raise ValidationError(_("A label must be attached to only one question."))

    def _get_answer_matching_domain(self, row_id=False):
        self.ensure_one()
        if self.question_type == "matrix":
            return ['&', '&', ('question_id', '=', self.question_id.id), ('matrix_row_id', '=', row_id), ('suggested_answer_id', '=', self.id)]
        elif self.question_type in ('multiple_choice', 'simple_choice'):
            return ['&', ('question_id', '=', self.question_id.id), ('suggested_answer_id', '=', self.id)]
        return []
