# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
import re
from urlparse import urljoin
import uuid
from collections import Counter, OrderedDict
from itertools import product

from odoo import api, fields, models, _
from odoo.addons.website.models.website import slug
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class SurveyStage(models.Model):
    """Stages for Kanban view of surveys"""

    _name = 'survey.stage'
    _description = 'Survey Stage'
    _order = 'sequence,id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=1)
    closed = fields.Boolean(help="If closed, people won't be able to answer to surveys in this column.")
    fold = fields.Boolean(string="Folded in kanban view")

    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]


class Survey(models.Model):
    '''Settings for a multi-page/multi-question survey.
    Each survey can have one or more attached pages, and each page can display
    one or more questions.
    '''

    _name = 'survey.survey'
    _description = 'Survey'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_stage(self):
        return self.env['survey.stage'].search([], limit=1)

    # Model fields #

    title = fields.Char(required=True, translate=True)
    page_ids = fields.One2many('survey.page', 'survey_id', string='Pages', copy=True)
    stage_id = fields.Many2one('survey.stage', string="Stage", copy=False,
        default=_default_stage)
    auth_required = fields.Boolean(string='Login required',
        help="Users with a public link will be requested to login before taking part to the survey",
        oldname="authenticate")
    users_can_go_back = fields.Boolean(help="If checked, users can go back to previous pages.")
    tot_sent_survey = fields.Integer(compute="_compute_tot_sent_survey",
        string="Number of sent surveys")
    tot_start_survey = fields.Integer(compute="_compute_tot_start_survey",
        string="Number of started surveys")
    tot_comp_survey = fields.Integer(compute="_compute_tot_comp_survey",
        string="Number of completed surveys")
    description = fields.Html(translate=True,
        help="A long description of the purpose of the survey")
    color = fields.Integer(string='Color Index')
    user_input_ids = fields.One2many('survey.user_input', 'survey_id',
        string='User responses', readonly=True)
    designed = fields.Boolean(compute='_compute_designed', string="Is designed?")
    public_url = fields.Char(compute='_compute_public_url',
        string="Public link")
    public_url_html = fields.Char(compute='_compute_public_url_html',
        string="Public link (html version)")
    print_url = fields.Char(compute='_compute_print_url',
        string="Print link")
    result_url = fields.Char(compute='_compute_result_url',
        string="Results link")
    email_template_id = fields.Many2one('mail.template',
        string='Email Template')
    thank_you_message = fields.Html(translate=True,
        help="This message will be displayed when survey is completed")
    quizz_mode = fields.Boolean()
    active = fields.Boolean(default=True)

    ## Function fields ##

    @api.multi
    def _compute_designed(self):
        for survey in self:
            if not survey.page_ids or not survey.page_ids.filtered(lambda page: page.question_ids.ids).mapped('question_ids'):
                survey.designed = False
            else:
                survey.designed = True

    @api.multi
    def _compute_tot_sent_survey(self):
        """ Returns the number of invitations sent for this survey, be they
        (partially) completed or not """
        survey_data = self.env['survey.user_input'].read_group([('survey_id', 'in', self.ids), ('type', '=', 'link')], ['survey_id'], ['survey_id'])
        result = dict((data['survey_id'][0], data['survey_id_count']) for data in survey_data)
        for survey in self:
            survey.tot_sent_survey = result.get(survey.id, 0)

    @api.multi
    def _compute_tot_start_survey(self):
        """ Returns the number of started instances of this survey, be they
        completed or not """
        survey_data = self.env['survey.user_input'].read_group(['&', ('survey_id', 'in', self.ids), '|', ('state', '=', 'skip'), ('state', '=', 'done')], ['survey_id'], ['survey_id'])
        result = dict((data['survey_id'][0], data['survey_id_count']) for data in survey_data)
        for survey in self:
            survey.tot_start_survey = result.get(survey.id, 0)

    @api.multi
    def _compute_tot_comp_survey(self):
        """ Returns the number of completed instances of this survey """
        survey_data = self.env['survey.user_input'].read_group([('survey_id', 'in', self.ids), ('state', '=', 'done')], ['survey_id'], ['survey_id'])
        result = dict((data['survey_id'][0], data['survey_id_count']) for data in survey_data)
        for survey in self:
            survey.tot_comp_survey = result.get(survey.id, 0)

    @api.multi
    def _compute_public_url(self):
        """ Computes a public URL for the survey """
        base_url = '/' if self.env.context.get('relative_url') else self.env['ir.config_parameter'].get_param('web.base.url')
        for survey in self:
            survey.public_url = urljoin(base_url, "survey/start/%s" % slug(survey))

    @api.multi
    def _compute_public_url_html(self):
        """ Computes a public URL for the survey (html-embeddable version)"""
        for survey in self:
            survey.public_url_html = '<a href="%s">%s</a>' % (survey.public_url, _("Click here to start survey"))

    @api.multi
    def _compute_print_url(self):
        """ Computes a printing URL for the survey """
        base_url = '/' if self.env.context.get('relative_url') else self.env['ir.config_parameter'].get_param('web.base.url')
        for survey in self:
            survey.print_url = urljoin(base_url, "survey/print/%s" % slug(survey))

    @api.multi
    def _compute_result_url(self):
        """ Computes an URL for the survey results """
        base_url = '/' if self.env.context.get('relative_url') else self.env['ir.config_parameter'].get_param('web.base.url')
        for survey in self:
            survey.result_url = urljoin(base_url, "survey/results/%s" % slug(survey))

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the stages in the
        kanban view, even if they are empty """
        SurveyStage = self.env['survey.stage']
        order = SurveyStage._order
        access_rights_uid = access_rights_uid or self.env.uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = SurveyStage._search([], order=order, access_rights_uid=access_rights_uid)
        stages = SurveyStage.sudo(access_rights_uid).browse(stage_ids)
        result = stages.name_get()

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stages:
            fold[stage.id] = stage.fold
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    # Actions

    @api.multi
    def action_start_survey(self):
        ''' Open the website page with the survey form '''
        self.ensure_one()
        trail = ""
        context = dict(self.env.context, relative_url=True)
        if 'survey_token' in context:
            trail = "/" + context['survey_token']
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': self.with_context(context).public_url + trail
        }

    @api.multi
    def action_send_survey(self):
        ''' Open a window to compose an email, pre-filled with the survey
        message '''
        self.ensure_one()
        if not self.designed:
            raise UserError(_('You cannot send an invitation for a survey that has no questions.'))

        if self.stage_id.closed:
            raise UserError(_("You cannot send invitations for closed surveys."))
        template_id = self.env.ref('survey.email_template_survey', raise_if_not_found=False)
        ctx = dict(self.env.context)
        ctx.update({'default_model': 'survey.survey',
                    'default_res_id': self.id,
                    'default_survey_id': self.id,
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id and template_id.id or False,
                    'default_composition_mode': 'comment'}
                   )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_print_survey(self):
        ''' Open the website page with the survey printable view '''
        self.ensure_one()
        trail = ""
        if 'survey_token' in self.env.context:
            trail = "/" + self.env.context['survey_token']
        return {
            'type': 'ir.actions.act_url',
            'name': "Print Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).print_url + trail
        }

    @api.multi
    def action_result_survey(self):
        ''' Open the website page with the survey results view '''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).result_url
        }

    @api.multi
    def action_test_survey(self):
        ''' Open the website page with the survey form into test mode'''
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).public_url + "/phantom"
        }

    # Public methods #

    @api.multi
    def copy(self, default=None):
        default = dict(default or {}, title=_("%s (copy)") % self.title)
        return super(Survey, self).copy(default)

    def next_page(self, user_input, page_id, go_back=False):
        '''The next page to display to the user, knowing that page_id is the id
        of the last displayed page.

        If page_id == 0, it will always return the first page of the survey.

        If all the pages have been displayed and go_back == False, it will
        return None

        If go_back == True, it will return the *previous* page instead of the
        next page.

        .. note::
            It is assumed here that a careful user will not try to set go_back
            to True if she knows that the page to display is the first one!
            (doing this will probably cause a giant worm to eat her house)'''
        survey = user_input.survey_id
        pages = list(enumerate(survey.page_ids))

        # First page
        if page_id == 0:
            return (pages[0][1], 0, len(pages) == 1)

        current_page_index = pages.index((filter(lambda p: p[1].id == page_id, pages))[0])

        # All the pages have been displayed
        if current_page_index == len(pages) - 1 and not go_back:
            return (None, -1, False)
        # Let's get back, baby!
        elif go_back and survey.users_can_go_back:
            return (pages[current_page_index - 1][1], current_page_index - 1, False)
        else:
            # This will show the last page
            if current_page_index == len(pages) - 2:
                return (pages[current_page_index + 1][1], current_page_index + 1, True)
            # This will show a regular page
            else:
                return (pages[current_page_index + 1][1], current_page_index + 1, False)

    def filter_input_ids(self, filters, finished=False):
        '''If user applies any filters, then this function returns list of
           filtered user_input_id and label's strings for display data in web.
           :param filters: list of dictionary (having: row_id, ansewr_id)
           :param finished: True for completely filled survey,Falser otherwise.
           :returns list of filtered user_input_ids.
        '''
        if filters:
            domain_filter, choice = [], []
            for filter_data in filters:
                row_id, answer_id = filter_data['row_id'], filter_data['answer_id']
                if row_id == 0:
                    choice.append(answer_id)
                else:
                    domain_filter.extend(['|', ('value_suggested_row.id', '=', row_id), ('value_suggested.id', '=', answer_id)])
            if choice:
                domain_filter.insert(0, ('value_suggested.id', 'in', choice))
            else:
                domain_filter = domain_filter[1:]
            user_input_lines = self.env['survey.user_input_line'].search(domain_filter)
            filtered_input_ids = user_input_lines.mapped('user_input_id').ids if user_input_lines else []
        else:
            filtered_input_ids = []
        if finished:
            UserInput = self.env['survey.user_input']
            if not filtered_input_ids:
                user_inputs = UserInput.search([('survey_id', '=', self.id)])
            else:
                user_inputs = UserInput.browse(filtered_input_ids)
            return user_inputs.filtered(lambda user_input: user_input.state == 'done').ids
        return filtered_input_ids

    @api.model
    def get_filter_display_data(self, filters):
        '''Returns data to display current filters
        :param filters: list of dictionary (having: row_id, answer_id)
        :param finished: True for completely filled survey, False otherwise.
        :returns list of dict having data to display filters.
        '''
        filter_display_data = []
        if filters:
            Surveylabel = self.env['survey.label']
            for filter_data in filters:
                row_id, answer_id = filter_data['row_id'], filter_data['answer_id']
                survey_label = Surveylabel.browse(answer_id)
                if row_id == 0:
                    labels = survey_label
                else:
                    labels = Surveylabel.browse([row_id, answer_id])
                filter_display_data.append({'question_text': survey_label.question_id.question, 'labels': [label.value for label in labels]})
        return filter_display_data

    def prepare_result(self, question, current_filters=None):
        ''' Compute statistical data for questions by counting number of vote per choice on basis of filter '''
        current_filters = current_filters or []
        result_summary = {}

        #Calculate and return statistics for choice
        if question.type in ['simple_choice', 'multiple_choice']:
            answers = {}
            comments = []
            answers.update({label.id: {'text': label.value, 'count': 0, 'answer_id': label.id} for label in question.labels_ids})
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and answers.get(input_line.value_suggested.id) and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    answers[input_line.value_suggested.id]['count'] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': answers.values(), 'comments': comments}

        #Calculate and return statistics for matrix
        if question.type == 'matrix':
            rows = OrderedDict(sorted({label.id: label.value for label in question.labels_ids_2}.items()))
            answers = OrderedDict(sorted({label.id: label.value for label in question.labels_ids}.items()))
            res = dict()
            comments = []
            for cell in product(rows.keys(), answers.keys()):
                res[cell] = 0
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and (not(current_filters) or input_line.user_input_id.id in current_filters) and input_line.value_suggested_row:
                    res[(input_line.value_suggested_row.id, input_line.value_suggested.id)] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': answers, 'rows': rows, 'result': res, 'comments': comments}

        #Calculate and return statistics for free_text, textbox, datetime
        if question.type in ['free_text', 'textbox', 'datetime']:
            result_summary = []
            for input_line in question.user_input_line_ids:
                if not(current_filters) or input_line.user_input_id.id in current_filters:
                    result_summary.append(input_line)

        #Calculate and return statistics for numerical_box
        if question.type == 'numerical_box':
            result_summary = {'input_lines': []}
            all_inputs = []
            for input_line in question.user_input_line_ids:
                if not(current_filters) or input_line.user_input_id.id in current_filters:
                    all_inputs.append(input_line.value_number)
                    result_summary['input_lines'].append(input_line)
            if all_inputs:
                result_summary.update({'average': round(sum(all_inputs) / len(all_inputs), 2),
                                       'max': round(max(all_inputs), 2),
                                       'min': round(min(all_inputs), 2),
                                       'sum': sum(all_inputs),
                                       'most_common': Counter(all_inputs).most_common(5)})
        return result_summary

    def get_input_summary(self, question, current_filters=None):
        ''' Returns overall summary of question e.g. answered, skipped, total_inputs on basis of filter '''
        current_filters = current_filters or []
        result = {}
        if question.survey_id.user_input_ids:
            total_input_ids = current_filters or [input_id.id for input_id in question.survey_id.user_input_ids if input_id.state != 'new']
            result['total_inputs'] = len(total_input_ids)
            question_input_ids = []
            for user_input in question.user_input_line_ids:
                if not user_input.skipped:
                    question_input_ids.append(user_input.user_input_id.id)
            result['answered'] = len(set(question_input_ids) & set(total_input_ids))
            result['skipped'] = result['total_inputs'] - result['answered']
        return result


class SurveyPage(models.Model):
    '''A page for a survey.

    Pages are essentially containers, allowing to group questions by ordered
    screens.

    .. note::
        A page should be deleted if the survey it belongs to is deleted. '''

    _name = 'survey.page'
    _description = 'Survey Page'
    _rec_name = 'title'
    _order = 'sequence,id'

    # Model Fields #

    title = fields.Char(string='Page Title', required=True,
        translate=True)
    survey_id = fields.Many2one('survey.survey', string='Survey',
        ondelete='cascade', required=True)
    question_ids = fields.One2many('survey.question', 'page_id',
        string='Questions', copy=True)
    sequence = fields.Integer(string='Page number', default=10)
    description = fields.Html('Description',
        help="An introductory text to your page", translate=True,
        oldname="note")

class SurveyQuestion(models.Model):
    ''' Questions that will be asked in a survey.

    Each question can have one of more suggested answers (eg. in case of
    dropdown choices, multi-answer checkboxes, radio buttons...).'''
    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence,id'

    # Model fields #
    # Question metadata
    page_id = fields.Many2one('survey.page', string='Survey page',
        ondelete='cascade', required=True, default=lambda self: self.env.context.get('page_id'))
    survey_id = fields.Many2one('survey.survey', related='page_id.survey_id', string='Survey')
    sequence = fields.Integer(default=10)

    # Question
    question = fields.Char(string='Question Name', required=True, translate=True)
    description = fields.Html(help="Use this field to add \
        additional explanations about your question", translate=True,
        oldname='descriptive_text')

    # Answer
    type = fields.Selection([('free_text', 'Multiple Lines Text Box'),
            ('textbox', 'Single Line Text Box'),
            ('numerical_box', 'Numerical Value'),
            ('datetime', 'Date and Time'),
            ('simple_choice', 'Multiple choice: only one answer'),
            ('multiple_choice', 'Multiple choice: multiple answers allowed'),
            ('matrix', 'Matrix')], string='Type of Question', size=15, required=True, default='free_text')
    matrix_subtype = fields.Selection([('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    labels_ids = fields.One2many('survey.label',
        'question_id', string='Types of answers', oldname='answer_choice_ids', copy=True)
    labels_ids_2 = fields.One2many('survey.label',
        'question_id_2', string='Rows of the Matrix', copy=True)
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
        string='Number of columns', default='12')
        # These options refer to col-xx-[12|6|4|3|2] classes in Bootstrap
    display_mode = fields.Selection([('columns', 'Radio Buttons'),
                                      ('dropdown', 'Selection Box')], default='columns')

    # Comments
    comments_allowed = fields.Boolean(string='Show Comments Field',
        oldname="allow_comment")
    comments_message = fields.Char(string='Comment Message', translate=True, default='If other, precise:')
    comment_count_as_answer = fields.Boolean(string='Comment Field is an Answer Choice',
        oldname='make_comment_field')

    # Validation
    validation_required = fields.Boolean(string='Validate entry',
        oldname='is_validation_require')
    validation_email = fields.Boolean(string='Input must be an email')
    validation_length_min = fields.Integer(string='Minimum Text Length')
    validation_length_max = fields.Integer(string='Maximum Text Length')
    validation_min_float_value = fields.Float(string='Minimum value')
    validation_max_float_value = fields.Float(string='Maximum value')
    validation_min_date = fields.Datetime(string='Minimum Date')
    validation_max_date = fields.Datetime(string='Maximum Date')
    validation_error_msg = fields.Char(string='Error message',
                                        oldname='validation_valid_err_msg',
                                        translate=True, default='The answer you entered has an invalid format.')

    # Constraints on number of answers (matrices)
    constr_mandatory = fields.Boolean(string='Mandatory Answer',
        oldname="is_require_answer")
    constr_error_msg = fields.Char("Error message",
        oldname='req_error_msg', translate=True, default='This question requires an answer.')
    user_input_line_ids = fields.One2many('survey.user_input_line',
                                           'question_id', 'Answers',
                                           domain=[('skipped', '=', False)])

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

    def validate_question(self, post, answer_tag):
        ''' Validate question, depending on question type and parameters '''
        try:
            checker = getattr(self, 'validate_' + self.type)
        except AttributeError:
            _logger.warning(self.type + ": This type of question has no validation method")
            return {}
        else:
            return checker(post, answer_tag)

    def validate_free_text(self, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        return errors

    def validate_textbox(self, post, answer_tag):
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
            if not re.match(r"[^@]+@[^@]+\.[^@]+", answer):
                errors.update({answer_tag: _('This answer must be an email address')})
        # Answer validation (if properly defined)
        # Length of the answer must be in a range
        if answer and self.validation_required:
            if not (self.validation_length_min <= len(answer) <= self.validation_length_max):
                errors.update({answer_tag: self.validation_error_msg})
        return errors

    def validate_numerical_box(self, post, answer_tag):
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
            try:
                floatanswer = float(answer)  # check that it is a float has been done hereunder
                if not (self.validation_min_float_value <= floatanswer <= self.validation_max_float_value):
                    errors.update({answer_tag: self.validation_error_msg})
            except ValueError:
                pass
        return errors

    def validate_datetime(self, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer:
            errors.update({answer_tag: self.constr_error_msg})
        # Checks if user input is a datetime
        if answer:
            try:
                dateanswer = fields.Datetime.from_string(answer)
            except ValueError:
                errors.update({answer_tag: _('This is not a date/time')})
                return errors
        # Answer validation (if properly defined)
        if answer and self.validation_required:
            # Answer is not in the right range
            dateanswer = fields.Datetime.from_string(answer)
            min_date = self.validation_min_date and fields.Datetime.from_string(self.validation_min_date) or False
            max_date = self.validation_max_date and fields.Datetime.from_string(self.validation_max_date) or False

            if (min_date and max_date and not(min_date <= dateanswer <= max_date)):
                # If Minimum and Maximum Date are entered
                errors.update({answer_tag: self.validation_error_msg})
            elif (min_date and not(min_date <= dateanswer)):
                # If only Minimum Date is entered and not Define Maximum Date
                errors.update({answer_tag: self.validation_error_msg})
            elif (max_date and not(dateanswer <= max_date)):
                # If only Maximum Date is entered and not Define Minimum Date
                errors.update({answer_tag: self.validation_error_msg})
        return errors

    def validate_simple_choice(self, post, answer_tag):
        errors = {}
        if self.comments_allowed:
            comment_tag = "%s_%s" % (answer_tag, 'comment')
        # Empty answer to mandatory self
        if self.constr_mandatory and answer_tag not in post:
            errors.update({answer_tag: self.constr_error_msg})
        if self.constr_mandatory and answer_tag in post and post[answer_tag].strip() == '':
            errors.update({answer_tag: self.constr_error_msg})
        # Answer is a comment and is empty
        if self.constr_mandatory and answer_tag in post and post[answer_tag] == "-1" and self.comment_count_as_answer and comment_tag in post and not post[comment_tag].strip():
            errors.update({answer_tag: self.constr_error_msg})
        return errors

    def validate_multiple_choice(self, post, answer_tag):
        errors = {}
        if self.constr_mandatory:
            answer_candidates = dict_keys_startswith(post, answer_tag)
            comment_flag = answer_candidates.pop(("%s_%s" % (answer_tag, -1)), None)
            if self.comments_allowed:
                comment_answer = answer_candidates.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
            # Preventing answers with blank value
            if all([True if answer.strip() == '' else False for answer in answer_candidates.values()]):
                errors.update({answer_tag: self.constr_error_msg})
            # There is no answer neither comments (if comments count as answer)
            if not answer_candidates and self.comment_count_as_answer and (not comment_flag or not comment_answer):
                errors.update({answer_tag: self.constr_error_msg})
            # There is no answer at all
            if not answer_candidates and not self.comment_count_as_answer:
                errors.update({answer_tag: self.constr_error_msg})
        return errors

    def validate_matrix(self, post, answer_tag):
        errors = {}
        if self.constr_mandatory:
            lines_number = len(self.labels_ids_2)
            answer_candidates = dict_keys_startswith(post, answer_tag)
            # Number of lines that have been answered
            if self.matrix_subtype == 'simple':
                answer_number = len(answer_candidates)
            elif self.matrix_subtype == 'multiple':
                answer_number = len(set([sk.rsplit('_', 1)[0] for sk in answer_candidates.keys()]))
            else:
                raise RuntimeError("Invalid matrix subtype")
            # Validate that each line has been answered
            if answer_number != lines_number:
                errors.update({answer_tag: self.constr_error_msg})
        return errors


class SurveyLabel(models.Model):
    ''' A suggested answer for a question '''
    _name = 'survey.label'
    _rec_name = 'value'
    _order = 'sequence,id'
    _description = 'Survey Label'

    question_id = fields.Many2one('survey.question', string='Question',
        ondelete='cascade')
    question_id_2 = fields.Many2one('survey.question', string='Question',
        ondelete='cascade')
    sequence = fields.Integer(string='Label Sequence order', default=10)
    value = fields.Char(string="Suggested value", translate=True,
        required=True)
    quizz_mark = fields.Float(string='Score for this choice', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

    @api.constrains('question_id', 'question_id_2')
    def _check_question_not_empty(self):
        '''Ensure that field question_id XOR field question_id_2 is not null'''
        for label in self:
            # 'bool()' is required in order to make '!=' act as XOR with objects
            if not (bool(label.question_id) != bool(label.question_id_2)):
                raise UserError(_("A label must be attached to one and only one question"))

class SurveyUserInput(models.Model):
    ''' Metadata for a set of one user's answers to a particular survey '''
    _name = "survey.user_input"
    _rec_name = 'date_create'
    _description = 'Survey User Input'

    survey_id = fields.Many2one('survey.survey', string='Survey', required=True,
                                 readonly=True, ondelete='restrict')
    date_create = fields.Datetime(string='Creation Date', required=True,
                                   readonly=True, copy=False, default=fields.Datetime.now)
    deadline = fields.Datetime(string="Deadline",
                            help="Date by which the person can open the survey and submit answers",
                            oldname="date_deadline")
    type = fields.Selection([('manually', 'Manually'), ('link', 'Link')],
                             string='Answer Type', required=True, readonly=True,
                             oldname="response_type", default='manually')
    state = fields.Selection([('new', 'Not started yet'),
                               ('skip', 'Partially completed'),
                               ('done', 'Completed')],
                              string='Status',
                              readonly=True, default='new')
    test_entry = fields.Boolean(readonly=True)
    token = fields.Char(string="Identification token", readonly=True, required=True, copy=False, default=lambda self: uuid.uuid4().__str__())

    # Optional Identification data
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    email = fields.Char(string="E-mail", readonly=True)

    # Displaying data
    last_displayed_page_id = fields.Many2one('survey.page',
                                          string='Last displayed page')
    # The answers !
    user_input_line_ids = fields.One2many('survey.user_input_line',
                                           'user_input_id', string='Answers', copy=True)

    # URLs used to display the answers
    result_url = fields.Char(related='survey_id.result_url',
                                 string="Public link to the survey results")
    print_url = fields.Char(related='survey_id.print_url',
                                string="Public link to the empty survey")

    quizz_score = fields.Float(compute="_compute_quizz_score", string="Score for the quiz")

    _sql_constraints = [
        ('unique_token', 'UNIQUE (token)', 'A token must be unique!'),
        ('deadline_in_the_past', 'CHECK (deadline >= date_create)', 'The deadline cannot be in the past')
    ]

    @api.multi
    def _compute_quizz_score(self):
        result = self.env['survey.user_input_line'].read_group([('user_input_id', 'in', self.ids)], ['quizz_mark', 'user_input_id'], ['user_input_id'])
        val = {res['user_input_id'][0]: res['quizz_mark'] for res in result}
        for user_input in self:
            user_input.quizz_score = val.get(user_input.id, 0.0)

    @api.multi
    def action_survey_resent(self):
        ''' Sent again the invitation '''
        self.ensure_one()
        context = dict(self.env.context or {})
        context.update({
            'survey_resent_token': True,
            'default_partner_ids': self.partner_id.id and [self.partner_id.id] or [],
            'default_multi_email': self.email or "",
            'default_public': 'email_private',
        })
        return self.survey_id.with_context(context).action_send_survey()

    @api.multi
    def action_view_answers(self):
        ''' Open the website page with the survey form '''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "View Answers",
            'target': 'self',
            'url': '%s/%s' % (self.print_url, self.token)
        }

    @api.multi
    def action_survey_results(self):
        ''' Open the website page with the survey results '''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Survey Results",
            'target': 'self',
            'url': self.result_url
        }

    @api.multi
    def copy_data(self, default=None):
        raise UserError(_('You cannot duplicate this element!'))

    @api.model
    def do_clean_emptys(self, automatic=False):
        ''' Remove empty user inputs that have been created manually
            (used as a cronjob declared in data/survey_cron.xml) '''
        self.search([('type', '=', 'manually'),
                     ('state', '=', 'new'),
                     ('date_create', '<', fields.Datetime.to_string((fields.Datetime.from_string(fields.Datetime.now()) - datetime.timedelta(hours=1))))]).unlink()

class SurveyUserInputLine(models.Model):
    _name = 'survey.user_input_line'
    _description = 'Survey User Input Line'
    _rec_name = 'date_create'

    user_input_id = fields.Many2one('survey.user_input', string='User Input',
                                     ondelete='cascade', required=True)
    question_id = fields.Many2one('survey.question', string='Question',
                                   ondelete='restrict', required=True)
    page_id = fields.Many2one('survey.page', related='question_id.page_id',
                              string="Page", readonly=True)
    survey_id = fields.Many2one('survey.survey', related='user_input_id.survey_id',
                                string='Survey', store=True, readonly=True)
    date_create = fields.Datetime(string='Create Date', required=True, default=fields.Datetime.now)
    skipped = fields.Boolean()
    answer_type = fields.Selection([('text', 'Text'),
                                     ('number', 'Number'),
                                     ('date', 'Date'),
                                     ('free_text', 'Free Text'),
                                     ('suggestion', 'Suggestion')],
                                    string='Answer Type')
    value_text = fields.Char(string="Text answer")
    value_number = fields.Float(string="Numerical answer")
    value_date = fields.Datetime(string="Date answer")
    value_free_text = fields.Text(string="Free Text answer")
    value_suggested = fields.Many2one('survey.label', string="Suggested answer")
    value_suggested_row = fields.Many2one('survey.label', "Row answer")
    quizz_mark = fields.Float(compute="_compute_quizz_mark", string="Score given for this choice", store=True)

    @api.depends('value_suggested', 'value_suggested.quizz_mark')
    def _compute_quizz_mark(self):
        for user_input_line in self:
            user_input_line.quizz_mark = user_input_line.value_suggested.quizz_mark or 0.0

    @api.constrains('skipped', 'answer_type')
    def _answered_or_skipped(self):
        # 'bool()' is required in order to make '!=' act as XOR with objects
        for input_line in self.filtered(lambda input_line: input_line.skipped == bool(input_line.answer_type)):
            raise UserError(_("A question cannot be unanswered and skipped"))

    @api.constrains('answer_type')
    def _check_answer_type(self):
        for input_line in self.filtered(lambda line: line.answer_type):
            if not bool(eval('input_line.value_%s' % ('suggested' if input_line.answer_type == 'suggestion'\
             else input_line.answer_type))):
                raise UserError(_("The answer must be in the right type"))
            elif (input_line.value_number != 0) and (input_line.value_number == False):
                raise UserError(_("The answer must be in the right type"))
            return True

    @api.multi
    def copy_data(self, default=None):
        raise UserError(_('You cannot duplicate this element!'))

    @api.model
    def save_lines(self, user_input_id, question, post, answer_tag):
        ''' Save answers to questions, depending on question type

        If an answer already exists for question and user_input_id, it will be
        overwritten (in order to maintain data consistency). '''
        try:
            saver = getattr(self, 'save_line_' + question.type)
        except AttributeError:
            _logger.error(question.type + ": This type of question has no saving function")
            return False
        else:
            saver(user_input_id, question, post, answer_tag)

    def save_line_free_text(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False,
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'free_text', 'value_free_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_input_line = self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)], limit=1)
        if old_input_line:
            old_input_line.write(vals)
        else:
            self.create(vals)
        return True

    def save_line_textbox(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'text', 'value_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_input_line = self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)], limit=1)
        if old_input_line:
            old_input_line.write(vals)
        else:
            self.create(vals)
        return True

    def save_line_numerical_box(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'number', 'value_number': float(post[answer_tag])})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_input_line = self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)], limit=1)
        if old_input_line:
            old_input_line.write(vals)
        else:
            self.create(vals)
        return True

    def save_line_datetime(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'date', 'value_date': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_input_line = self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)], limit=1)
        if old_input_line:
            old_input_line.write(vals)
        else:
            self.create(vals)
        return True

    def save_line_simple_choice(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)]).sudo().unlink()

        if answer_tag in post and post[answer_tag].strip() != '':
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

    def save_line_multiple_choice(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        self.search([('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)]).sudo().unlink()

        ca = dict_keys_startswith(post, answer_tag)
        comment_answer = ca.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if len(ca) > 0:
            for a in ca:
                # '-1' indicates 'comment count as an answer' so do not need to record it
                if a != ('%s_%s' % (answer_tag, '-1')):
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca[a]})
                    self.create(vals)
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer, 'value_suggested': False})
            self.create(vals)
        if not ca and not comment_answer:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(vals)
        return True

    def save_line_matrix(self, user_input_id, question, post, answer_tag):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'skipped': False
        }
        self.search([('user_input_id', '=', user_input_id),
                    ('survey_id', '=', question.survey_id.id),
                    ('question_id', '=', question.id)]).sudo().unlink()

        no_answers = True
        ca = dict_keys_startswith(post, answer_tag)

        comment_answer = ca.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer})
            self.create(vals)
            no_answers = False

        if question.matrix_subtype == 'simple':
            for row in question.labels_ids_2:
                a_tag = "%s_%s" % (answer_tag, row.id)
                if a_tag in ca:
                    no_answers = False
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca[a_tag], 'value_suggested_row': row.id})
                    self.create(vals)

        elif question.matrix_subtype == 'multiple':
            for col in question.labels_ids:
                for row in question.labels_ids_2:
                    a_tag = "%s_%s_%s" % (answer_tag, row.id, col.id)
                    if a_tag in ca:
                        no_answers = False
                        vals.update({'answer_type': 'suggestion', 'value_suggested': col.id, 'value_suggested_row': row.id})
                        self.create(vals)
        if no_answers:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(vals)
        return True


def dict_keys_startswith(dictionary, string):
    '''Returns a dictionary containing the elements of <dict> whose keys start
    with <string>.

    .. note::
        This function uses dictionary comprehensions (Python >= 2.7)'''
    return {k: dictionary[k] for k in filter(lambda key: key.startswith(string), dictionary.keys())}
