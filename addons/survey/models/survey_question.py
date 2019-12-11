# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import json
import itertools
import operator

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class SurveyQuestion(models.Model):
    """ Questions asked in a survey. Questions can either be open (with inputs
    being text, date, datetimes, numerical) or based on suggested values (
    selection or matrix).

    Question model also holds fake questions being page based on the is_page field
    allowing to have all pages / questions within a single model and o2m.
    """
    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'title'
    _order = 'sequence,id'

    @api.model
    def default_get(self, fields):
        defaults = super(SurveyQuestion, self).default_get(fields)
        if (not fields or 'question_type' in fields):
            defaults['question_type'] = False if defaults.get('is_page') == True else 'text_box'
        return defaults

    # question generic data
    title = fields.Char('Title', required=True, translate=True)
    description = fields.Html('Description', help="Use this field to add additional explanations about your question", translate=True)
    survey_id = fields.Many2one('survey.survey', string='Survey', ondelete='cascade')
    scoring_type = fields.Selection(related='survey_id.scoring_type', string='Scoring Type', readonly=True)
    sequence = fields.Integer('Sequence', default=10)
    # page specific
    is_page = fields.Boolean('Is a page?')
    question_ids = fields.One2many('survey.question', 'page_id', string='Questions', depends=['sequence', 'page_id'])
    questions_selection = fields.Selection(
        related='survey_id.questions_selection', readonly=True,
        help="If randomized is selected, add the number of random questions next to the section.")
    random_questions_count = fields.Integer(
        'Random questions count', default=1,
        help="Used on randomized sections to take X random questions from all the questions of that section.")
    # question specific
    page_id = fields.Many2one('survey.question', string='Page', compute="_compute_page_id", store=True)
    question_type = fields.Selection([
        ('text_box', 'Multiple Lines Text Box'),
        ('char_box', 'Single Line Text Box'),
        ('numerical_box', 'Numerical Value'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('answer_selection', 'Multiple choice'),
        ('answer_matrix', 'Matrix')], string='Question Type')
    # -- char_box
    save_as_email = fields.Boolean(
        "Save as user email", compute='_compute_save_as_email', readonly=False, store=True,
        help="If checked, this option will save the user's answer as its email address.")
    # -- multiple choice / matrix
    matrix_column_ids = fields.One2many(
        'survey.question.answer.label', 'question_column_id',
        string='Matrix Columns', copy=True)
    matrix_row_ids = fields.One2many(
        'survey.question.answer.label', 'question_row_id',
        string='Matrix Rows', copy=True)
    suggested_answer_ids = fields.One2many(
        'survey.question.answer', 'question_id', string='Types of answers', copy=True,
        compute='_compute_suggested_answer_ids', store=True, readonly=False,
        help='Labels used for proposed choices: simple choice, multiple choice and columns of matrix')
    selection_mode = fields.Selection([
        ('single', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Selection Mode', default='single')
    # -- display options
    column_nb = fields.Selection([
        ('12', '1'), ('6', '2'), ('4', '3'), ('3', '4'), ('2', '6')],
        string='Number of columns', default='12',
        help='These options refer to col-xx-[12|6|4|3|2] classes in Bootstrap for dropdown-based simple and multiple choice questions.')
    display_mode = fields.Selection(
        [('columns', 'Radio Buttons'), ('dropdown', 'Selection Box')],
        string='Display Mode', default='columns', help='Display mode of simple choice questions.')
    # -- comments (simple choice, multiple choice, matrix (without count as an answer))
    comments_allowed = fields.Boolean('Show Comments Field')
    comments_message = fields.Char('Comment Message', translate=True, default=lambda self: _("If other, please specify:"))
    comment_count_as_answer = fields.Boolean('Comment Field is an Answer Choice')
    # question validation
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
    constr_mandatory = fields.Boolean('Mandatory Answer')
    constr_error_msg = fields.Char('Error message', translate=True, default=lambda self: _("This question requires an answer."))
    # answers
    user_input_line_ids = fields.One2many(
        'survey.user_input.line', 'question_id', string='Answers',
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
    def _onchange_validation_email(self):
        if self.validation_email:
            self.validation_required = False

    @api.onchange('is_page')
    def _onchange_is_page(self):
        if self.is_page:
            self.question_type = False

    @api.depends('survey_id.question_and_page_ids.is_page', 'survey_id.question_and_page_ids.sequence')
    def _compute_page_id(self):
        """Will find the page to which this question belongs to by looking inside the corresponding survey"""
        for question in self:
            if question.is_page:
                question.page_id = None
            else:
                question.page_id = next(
                    (iter(question.survey_id.question_and_page_ids.filtered(
                        lambda q: q.is_page and q.sequence < question.sequence
                    ).sorted(reverse=True))),
                    None
                )

    @api.depends('question_type', 'validation_email')
    def _compute_save_as_email(self):
        for question in self:
            if question.question_type != 'char_box' or not question.validation_email:
                question.save_as_email = False

    @api.depends('question_type', 'matrix_row_ids', 'matrix_column_ids')
    def _compute_suggested_answer_ids(self):
        for question in self:
            print('computing _compute_suggested_answer_ids', question, question.question_type)
            if question.question_type == 'answer_matrix':
                value = []
                existing = self.env['survey.question.answer']
                for row, col in itertools.product(question.matrix_row_ids, question.matrix_column_ids):
                    print('checking', row, row.name, '-', col, col.name)
                    existing |= question.suggested_answer_ids.filtered(
                        lambda answer:
                            answer.matrix_row_label_id.id == row._origin.id and
                            answer.matrix_column_label_id.id == col._origin.id
                    )
                    if not existing:
                        value += [
                            (0, 0, {
                                'question_id': question.id,
                                'matrix_row_label_id': row.id,
                                'matrix_column_label_id': col.id,
                                'value': '%s-%s' % (row.name, col.name),
                            })
                        ]
                print('\texisting', existing)
                to_delete = question.suggested_answer_ids - existing
                print('\ttodelete', to_delete)
                caca = [(3, answer.id) for answer in to_delete] + value
                print('\tfinalcommand', caca)
                question.suggested_answer_ids = caca
            else:
                question.suggested_answer_ids = []

    def create(self, values):
        print('creating question with', values)
        res = super(SurveyQuestion, self).create(values)
        return res

    # Validation methods
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
        if self.constr_mandatory and not answer and self.question_type != 'answer_selection':
            return {self.id: self.constr_error_msg}

        # because in choices question types, comment can count as answer
        if answer or self.question_type == 'answer_selection':
            if self.question_type == 'char_box':
                return self._validate_char_box(answer)
            elif self.question_type == 'numerical_box':
                return self._validate_numerical_box(answer)
            elif self.question_type in ['date', 'datetime']:
                return self._validate_date(answer)
            elif self.question_type == 'answer_selection':
                return self._validate_choice(answer, comment)
            elif self.question_type == 'answer_matrix':
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
            with tools.ignore(Exception):
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
            if question.question_type in ['answer_selection', 'answer_matrix']:
                answer_lines = all_lines.filtered(
                    lambda line: line.answer_type == 'suggestion' or (
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
        if self.question_type == 'answer_selection':
            table_data, graph_data = self._get_stats_data_answers(user_input_lines)
            if self.selection_mode == 'multiple':
                graph_data = [{'key': self.title, 'values': graph_data}]
            return table_data, graph_data
        elif self.question_type in ['answer_matrix']:
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
            if line.suggested_answer_id or (line.value_char_box and self.comment_count_as_answer):
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
        if self.question_type in ['answer_selection']:
            return self._get_stats_summary_data_choice(user_input_lines)
        if self.question_type in ['numerical_box']:
            return self._get_stats_summary_data_numerical(user_input_lines)
        return {}

    def _get_stats_summary_data_choice(self, user_input_lines):
        right_inputs, partial_inputs = self.env['survey.user_input'], self.env['survey.user_input']
        right_answers = self.suggested_answer_ids.filtered(lambda label: label.is_correct)
        if self.selection_mode == 'multiple':
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
            'right_inputs': right_inputs,
            'partial_inputs': partial_inputs,
        }

    def _get_stats_summary_data_numerical(self, user_input_lines):
        all_values = user_input_lines.filtered(lambda line: not line.skipped).mapped('value_numerical_box')
        lines_sum = sum(all_values)
        return {
            'numerical_max': max(all_values, default=0),
            'numerical_min': min(all_values, default=0),
            'numerical_average': round(lines_sum / len(all_values) or 1, 2),
            'numerical_common_lines': collections.Counter(all_values).most_common(5),
        }


class SurveyQuestionAnswerLabel(models.Model):
    """ Labels used for matrix question (either as row or column) """
    _name = 'survey.question.answer.label'
    _rec_name = 'name'
    _order = 'name, sequence'
    _description = 'Col/Row values'

    name = fields.Char('Value')
    sequence = fields.Integer('Sequence')
    question_column_id = fields.Many2one('survey.question', string='Question (as column)', ondelete='cascade')
    question_row_id = fields.Many2one('survey.question', string='Question (as row)', ondelete='cascade')

    @api.constrains('question_column_id', 'question_row_id')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field matrix_question_id is not null"""
        for label in self:
            if not bool(label.question_column_id) != bool(label.question_row_id):
                raise ValidationError(_("A label must be attached to only one question."))


class SurveyQuestionAnswer(models.Model):
    """ A suggested answer for a question. This model stores values used
    for answer_selection and answer_matrix. """
    _name = 'survey.question.answer'
    _rec_name = 'value'
    _order = 'sequence, id'
    _description = 'Survey Label'

    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade')
    matrix_column_label_id = fields.Many2one(
        'survey.question.answer.label', string='Column Label',
        domain="[('question_column_id', '=', question_id)]")
    matrix_row_label_id = fields.Many2one(
        'survey.question.answer.label', string='Row Label',
        domain="[('question_row_id', '=', question_id)]")
    matrix_question_id = fields.Many2one('survey.question')  # delete me
    sequence = fields.Integer('Label Sequence order', default=10)
    value = fields.Char('Value', translate=True, required=True)
    is_correct = fields.Boolean('Is correct')
    answer_score = fields.Float('Score for this choice', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    # @api.constrains('question_id', 'matrix_column_label_id', 'matrix_row_label_id')
    # def _check_matrix_answers(self):
    #     """Ensure that field question_id XOR field matrix_question_id is not null"""
    #     for answer in self:
    #         if answer.question_id.question_type == 'answer_matrix' and (not answer.matrix_column_label_id or not answer.matrix_row_label_id):
    #             raise ValidationError(_('A suggested answer for matrix question should have a column and a row.'))
