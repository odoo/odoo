# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and / or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from urlparse import urljoin

import datetime
import logging
import re
import uuid
import traceback

_logger = logging.getLogger(__name__)


class survey_survey(osv.osv):
    '''Settings for a multi-page/multi-question survey.
    Each survey can have one or more attached pages, and each page can display
    one or more questions.
    '''

    _name = 'survey.survey'
    _description = 'Survey'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    # Protected methods #

    def _has_questions(self, cr, uid, ids, context=None):
        """ Ensure that this survey has at least one page with at least one
        question. """
        for survey in self.browse(cr, uid, ids, context=context):
            if not survey.page_ids or not [page.question_ids
                            for page in survey.page_ids if page.question_ids]:
                return False
        return True

    ## Function fields ##

    def _get_tot_start_survey(self, cr, uid, ids, name, arg, context=None):
        """ Returns the number of started instances of this survey, be they
        completed or not """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.user_input')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid,  # SUPERUSER_ID,
                [('survey_id', '=', id), ('state', '=', 'skip')],
                context=context, count=True)
        return res

    def _get_tot_comp_survey(self, cr, uid, ids, name, arg, context=None):
        """ Returns the number of completed instances of this survey """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.user_input')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid,  # SUPERUSER_ID,
                [('survey_id', '=', id), ('state', '=', 'done')],
                context=context, count=True)
        return res

    def _get_public_url(self, cr, uid, ids, name, arg, context=None):
        """ Computes a public URL for the survey """
        res = dict((id, 0) for id in ids)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid,
            'web.base.url')
        for survey_browse in self.browse(cr, uid, ids, context=context):
            res[survey_browse.id] = urljoin(base_url, "survey/start/%s/"
                                            % survey_browse.id)
        return res

    # Model fields #

    _columns = {
        'title': fields.char('Title', size=128, required=1,
            translate=True),
        'res_model': fields.char('Category'),
        'page_ids': fields.one2many('survey.page', 'survey_id', 'Pages'),
        'date_open': fields.datetime('Opening date'),
        'date_close': fields.datetime('Closing date'),
        'user_input_limit': fields.integer('Automatic closing limit',
            help="Limits the number of instances of this survey that can be completed (if set to 0, no limit is applied)",
            oldname='max_response_limit'),
        'state': fields.selection(
            [('draft', 'Draft'), ('open', 'Open'), ('close', 'Closed'),
            ('cancel', 'Cancelled')], 'Status', required=1, readonly=1,
            translate=1),
        'visible_to_user': fields.boolean('Public in website',
            help="If unchecked, only invited users will be able to open the survey."),
        'auth_required': fields.boolean('Login required',
            help="Users with a public link will be requested to login before taking part to the survey",
            oldname="authenticate"),
        'users_can_go_back': fields.boolean('Users can go back',
            help="If checked, users can go back to previous pages."),
        'tot_start_survey': fields.function(_get_tot_start_survey,
            string="Number of started surveys", type="integer"),
        'tot_comp_survey': fields.function(_get_tot_comp_survey,
            string="Number of completed surveys", type="integer"),
        'description': fields.html('Description', translate=True,
            oldname="description", help="A long description of the purpose of the survey"),
        'color': fields.integer('Color Index'),
        'user_input_ids': fields.one2many('survey.user_input', 'survey_id',
            'User responses', readonly=1),
        'public_url': fields.function(_get_public_url,
            string="Public link", type="char"),
        'email_template_id': fields.many2one('email.template',
            'Email Template', ondelete='set null'),
        'thank_you_message': fields.html('Thank you message', translate=True,
            help="This message will be displayed when survey is completed")
    }

    _defaults = {
        'user_input_limit': 0,
        'state': 'draft',
        'visible_to_user': True,
        'auth_required': True,
        'users_can_go_back': False
    }

    _sql_constraints = {
        ('positive_user_input_limit', 'CHECK (user_input_limit >= 0)', 'Automatic closing limit must be positive')
    }

    # Public methods #

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        vals['title'] = title
        vals['user_input_ids'] = []
        return super(survey_survey, self).copy(cr, uid, ids, vals,
            context=context)

    def action_print_survey_questions(self, cr, uid, ids, context=None):
        ''' Generates a printable view of an empty survey '''
        pass

    def action_print_survey_user_inputs(self, cr, uid, ids, context=None):
        ''' Generates printable views of answered surveys '''
        pass

    def action_print_survey_statistics(self, cr, uid, ids, context=None):
        ''' Generates a printable view of the survey results '''
        pass

    def action_fill_survey(self, cr, uid, ids, context=None):
        ''' Open a survey in filling view '''
        id = ids[0]
        survey = self.browse(cr, uid, id, context=context)
        context.update({'edit': False, 'survey_id': id,
            'survey_token': survey.token,
            'ir_actions_act_window_target': 'inline'})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'inline',
            'name': survey.title,
            'context': context
        }

    def action_test_survey(self, cr, uid, ids, context=None):
        ''' Open a survey in filling view '''
        context.update({'survey_test': True})
        return self.action_fill_survey(cr, uid, ids, context=context)

    def action_edit_survey(self, cr, uid, ids, context=None):
        ''' Open a survey in edition view '''
        id = ids[0]
        context.update({
            'survey_id': id,
            'edit': True,
            'ir_actions_act_window_target': 'new',
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': self.browse(cr, uid, id, context=context).title,
            'context': context
        }

    def action_send_survey(self, cr, uid, ids, context=None):
        ''' Open a window to compose an email, pre-filled with the survey
        message '''
        if not self._has_questions(cr, uid, ids, context=None):
            raise osv.except_osv(_('Error!'), _('You can not send a survey that has no questions.'))

        survey_browse = self.pool.get('survey.survey').browse(cr, uid, ids,
            context=context)[0]
        if survey_browse.state != "open":
            raise osv.except_osv(_('Warning!'),
                _("You cannot send invitations since the survey is not open."))

        assert len(ids) == 1, 'This option should only be used for a single \
                                survey at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid,
                                'survey.survey', 'email_template_survey')[1]
        except ValueError:
            template_id = False
        ctx = dict(context)

        ctx.update({
            'default_model': 'survey.survey',
            'default_res_id': ids[0],
            'default_survey_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'survey_state': survey_browse.state
            })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    def write(self, cr, uid, ids, vals, context=None):
        new_state = vals.get('state')
        if new_state == 'draft':
            vals.update({'date_open': None})
            vals.update({'date_close': None})
        elif new_state == 'open':
            if self._has_questions(cr, uid, ids, context=None):
                vals.update({'date_open': fields.datetime.now(), 'date_close': None})
            else:
                raise osv.except_osv(_('Error!'), _('You can not open a survey that has no questions.'))
        elif new_state == 'close':
            vals.update({'date_close': fields.datetime.now()})
        else:
            pass
        return super(survey_survey, self).write(cr, uid, ids, vals, context=None)


class survey_page(osv.osv):
    '''A page for a survey.

    Pages are essentially containers, allowing to group questions by ordered
    screens.

    .. note::
        A page should be deleted if the survey it belongs to is deleted. '''

    _name = 'survey.page'
    _description = 'Survey Page'
    _rec_name = 'title'
    _order = 'sequence'

    # Model Fields #

    _columns = {
        'title': fields.char('Page Title', size=128, required=1,
            translate=True),
        'survey_id': fields.many2one('survey.survey', 'Survey',
            ondelete='cascade'),
        'question_ids': fields.one2many('survey.question', 'page_id',
            'Questions'),
        'sequence': fields.integer('Page number'),
        'description': fields.html('Description',
            help="An introductory text to your page", translate=True,
            oldname="note"),
    }

    # Public methods #

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        vals.update({'title': title})
        return super(survey_page, self).copy(cr, uid, ids, vals,
            context=context)


class survey_question(osv.osv):
    ''' Questions that will be asked in a survey.

    Each question can have one of more suggested answers (eg. in case of
    dropdown choices, multi-answer checkboxes, radio buttons...).'''
    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence'

    # Model fields #

    _columns = {
        # Question metadata
        'page_id': fields.many2one('survey.page', 'Survey page',
            ondelete='cascade'),
        'survey_id': fields.related('page_id', 'survey_id', type='many2one',
            relation='survey.survey', string='Survey', store=True),
        'parent_id': fields.many2one('survey.question', 'Parent question',
            ondelete='cascade'),
        'children_ids': fields.one2many('survey.question', 'parent_id',
            'Children questions'),
        'sequence': fields.integer(string='Sequence'),

        # Question
        'question': fields.char('Question', required=1, translate=True),
        'description': fields.char('Description', help="Use this field to add \
            additional explanations about your question", translate=True,
            oldname='descriptive_text'),

        # Answer
        'type': fields.selection([('free_text', 'Long text zone'),
                ('textbox', 'Text box'),
                ('numerical_box', 'Numerical box'),
                ('datetime', 'Date and Time'),
                ('simple_choice', 'Multiple choice (one answer)'),
                ('multiple_choice', 'Multiple choice (multiple answers)'),
                ('matrix', 'Matrix')], 'Question Type', required=1),
        'matrix_subtype': fields.selection([('simple', 'One choice per line'),
            ('multiple', 'Several choices per line')], 'Matrix Type'),
        'labels_ids': fields.one2many('survey.label',
            'question_id', 'Suggested answers', oldname='answer_choice_ids'),
        'labels_ids_2': fields.one2many('survey.label',
            'question_id_2', 'Suggested answers'),

        # Display options
        'column_nb': fields.selection([('12', '1 column choices'),
                                       ('6', '2 columns choices'),
                                       ('4', '3 columns choices'),
                                       ('3', '4 columns choices'),
                                       ('2', '6 columns choices')],
            'Number of columns'),
        'display_mode': fields.selection([('columns', 'Columns'),
                                          ('dropdown', 'Dropdown menu')],
                                         'Display mode'),

        # Comments
        'comments_allowed': fields.boolean('Allow comments',
            oldname="allow_comment"),
        'comment_children_ids': fields.many2many('survey.question',
            'question_comment_children_ids', 'comment_id', 'parent_id',
            'Comment question'),  # one2one in fact
        'comment_count_as_answer': fields.boolean('Comment field is an answer choice',
            oldname='make_comment_field'),

        # Validation
        'validation_required': fields.boolean('Validate entry',
            oldname='is_validation_require'),
        'validation_type': fields.selection([
            ('has_length', 'Must have a specific length'),
            ('is_integer', 'Must be an integer'),
            ('is_decimal', 'Must be a decimal number'),
            #('is_date', 'Must be a date'),
            ('is_email', 'Must be an email address')],
            'Validation type', translate=True),
        'validation_length_min': fields.integer('Minimum length'),
        'validation_length_max': fields.integer('Maximum length'),
        'validation_min_float_value': fields.float('Minimum value'),
        'validation_max_float_value': fields.float('Maximum value'),
        'validation_min_int_value': fields.integer('Minimum value'),
        'validation_max_int_value': fields.integer('Maximum value'),
        'validation_min_date': fields.date('Start date range'),
        'validation_max_date': fields.date('End date range'),
        'validation_error_msg': fields.char('Error message',
                                            oldname='validation_valid_err_msg',
                                            translate=True),

        # Constraints on number of answers
        'constr_mandatory': fields.boolean('Mandatory question',
            oldname="is_require_answer"),
        'constr_type': fields.selection([('all', 'all'),
            ('at least', 'at least'),
            ('at most', 'at most'),
            ('exactly', 'exactly'),
            ('a range', 'a range')],
            'Constraint on answers number', oldname='required_type'),
        'constr_maximum_req_ans': fields.integer('Maximum Required Answer',
            oldname='maximum_req_ans'),
        'constr_minimum_req_ans': fields.integer('Minimum Required Answer',
            oldname='minimum_req_ans'),
        'constr_error_msg': fields.char("Error message",
            oldname='req_error_msg'),
    }
    _defaults = {
        'page_id': lambda s, cr, uid, c: c.get('page_id'),
        'type': 'free_text',
        'matrix_subtype': 'simple',
        'column_nb': '12',
        'display_mode': 'dropdown',
        'constr_type': 'at least',
        'constr_minimum_req_ans': 1,
        'constr_error_msg': lambda s, cr, uid, c:
                _('This question requires an answer.'),
        'validation_error_msg': lambda s, cr, uid, c: _('The answer you entered has an invalid format.'),
        'validation_required': False,
    }
    _sql_constraints = [
        ('positive_len_min', 'CHECK (validation_length_min >= 0)', 'A length must be positive!'),
        ('positive_len_max', 'CHECK (validation_length_max >= 0)', 'A length must be positive!'),
        ('validation_length', 'CHECK (validation_length_min <= validation_length_max)', 'Max length cannot be smaller than min length!'),
        ('validation_float', 'CHECK (validation_min_float_value <= validation_max_float_value)', 'Max value cannot be smaller than min value!'),
        ('validation_int', 'CHECK (validation_min_int_value <= validation_max_int_value)', 'Max value cannot be smaller than min value!'),
        ('validation_date', 'CHECK (validation_min_date <= validation_max_date)', 'Max date cannot be smaller than min date!')
    ]

    # def write(self, cr, uid, ids, vals, context=None):
    #     questions = self.read(cr, uid, ids, ['answer_choice_ids', 'type',
    #         'required_type', 'req_ans', 'minimum_req_ans', 'maximum_req_ans',
    #         'column_heading_ids', 'page_id', 'question'])
    #     for question in questions:
    #         col_len = len(question['column_heading_ids'])
    #         for col in vals.get('column_heading_ids', []):
    #             if type(col[2]) == type({}):
    #                 col_len += 1
    #             else:
    #                 col_len -= 1

    #         que_type = vals.get('type', question['type'])

    #         if que_type in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale']:
    #             if not col_len:
    #                 raise osv.except_osv(_('Warning!'), _('You must enter one or more column headings for question "%s" of page %s.') % (question['question'], question['page_id'][1]))
    #         ans_len = len(question['answer_choice_ids'])

    #         for ans in vals.get('answer_choice_ids', []):
    #             if type(ans[2]) == type({}):
    #                 ans_len += 1
    #             else:
    #                 ans_len -= 1

    #         if que_type not in ['descriptive_text', 'single_textbox', 'comment', 'table']:
    #             if not ans_len:
    #                 raise osv.except_osv(_('Warning!'), _('You must enter one or more Answers for question "%s" of page %s.') % (question['question'], question['page_id'][1]))

    #         req_type = vals.get('required_type', question['required_type'])

    #         if que_type in ['multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', \
    #                     'matrix_of_choices_only_multi_ans', 'rating_scale', 'multiple_textboxes', \
    #                     'numerical_textboxes', 'date', 'date_and_time']:
    #             if req_type in ['at least', 'at most', 'exactly']:
    #                 if 'req_ans' in vals:
    #                     if not vals['req_ans'] or vals['req_ans'] > ans_len:
    #                         raise osv.except_osv(_('Warning!'), _("#Required Answer you entered \
    #                                 is greater than the number of answer. \
    #                                 Please use a number that is smaller than %d.") % (ans_len + 1))
    #                 else:
    #                     if not question['req_ans'] or question['req_ans'] > ans_len:
    #                         raise osv.except_osv(_('Warning!'), _("#Required Answer you entered is \
    #                                 greater than the number of answer.\
    #                                 Please use a number that is smaller than %d.") % (ans_len + 1))

    #             if req_type == 'a range':
    #                 minimum_ans = 0
    #                 maximum_ans = 0
    #                 minimum_ans = 'minimum_req_ans' in vals and vals['minimum_req_ans'] or question['minimum_req_ans']
    #                 maximum_ans = 'maximum_req_ans' in vals and vals['maximum_req_ans'] or question['maximum_req_ans']

    #                 if not minimum_ans or minimum_ans > ans_len or not maximum_ans or maximum_ans > ans_len:
    #                     raise osv.except_osv(_('Warning!'), _("Minimum Required Answer you\
    #                              entered is greater than the number of answer. \
    #                              Please use a number that is smaller than %d.") % (ans_len + 1))
    #                 if maximum_ans <= minimum_ans:
    #                     raise osv.except_osv(_('Warning!'), _("Maximum Required Answer is greater \
    #                                 than Minimum Required Answer"))

    #     return super(survey_question, self).write(cr, uid, ids, vals, context=context)

    # def create(self, cr, uid, vals, context=None):
    #     page = self.pool.get('survey.page').browse(cr, uid, 'page_id' in vals and vals['page_id'] or context['page_id'], context=context)
    #     if 'answer_choice_ids' in vals and not len(vals.get('answer_choice_ids', [])) and \
    #         vals.get('type') not in ['descriptive_text', 'single_textbox', 'comment', 'table']:
    #         raise osv.except_osv(_('Warning!'), _('You must enter one or more answers for question "%s" of page %s .') % (vals['question'], page.title))

    #     if 'column_heading_ids' in vals and not len(vals.get('column_heading_ids', [])) and \
    #         vals.get('type') in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale']:
    #         raise osv.except_osv(_('Warning!'), _('You must enter one or more column headings for question "%s" of page %s.') % (vals['question'], page.title))

    #     if 'is_require_answer' in vals and vals.get('type') in ['multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', \
    #         'matrix_of_choices_only_multi_ans', 'rating_scale', 'multiple_textboxes', 'numerical_textboxes', 'date', 'date_and_time']:
    #         if vals.get('required_type') in ['at least', 'at most', 'exactly']:
    #             if 'answer_choice_ids' in vals and 'answer_choice_ids' in vals and vals.get('req_ans') > len(vals.get('answer_choice_ids', [])):
    #                 raise osv.except_osv(_('Warning!'), _("#Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
    #         if vals.get('required_type') == 'a range':
    #             if 'answer_choice_ids' in vals:
    #                 if not vals.get('minimum_req_ans') or vals['minimum_req_ans'] > len(vals['answer_choice_ids']):
    #                     raise osv.except_osv(_('Warning!'), _("Minimum Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
    #                 if not vals.get('maximum_req_ans') or vals['maximum_req_ans'] > len(vals['answer_choice_ids']):
    #                     raise osv.except_osv(_('Warning!'), _("Maximum Required Answer you entered for your maximum is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
    #             if vals.get('maximum_req_ans', 0) <= vals.get('minimum_req_ans', 0):
    #                 raise osv.except_osv(_('Warning!'), _("Maximum Required Answer is greater than Minimum Required Answer."))

    #     return super(survey_question, self).create(cr, uid, vals, context)

    def survey_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        surv_name_wiz = self.pool.get('survey.question.wiz')
        surv_name_wiz.write(cr, uid, [context.get('wizard_id', False)],
            {'transfer': True, 'page_no': context.get('page_number', False)})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    # Validation methods

    def validate_question(self, cr, uid, question, post, answer_tag, context=None):
        ''' Validate question, depending on question type and parameters '''
        try:
            checker = getattr(self, 'validate_' + question.type)
        except AttributeError:
            _logger.warning(question.type + ": This type of question has no validation method")
            return {}
        else:
            return checker(cr, uid, question, post, answer_tag, context=context)

    def validate_free_text(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_textbox(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Answer validation (if properly defined)
        if answer and question.validation_required and question.validation_type:
            # Length of the answer must be in a range
            if question.validation_type == "has_length":
                if not (question.validation_length_min <= len(answer) <= question.validation_length_max):
                    errors.update({answer_tag: question.validation_error_msg})

            # Answer must be an integer in a particular range
            elif question.validation_type == "is_integer":
                try:
                    intanswer = int(answer)
                # Answer is not an integer
                except ValueError:
                    errors.update({answer_tag: question.validation_error_msg})
                else:
                    # Answer is not in the right range
                    if not (question.validation_min_int_value <= intanswer <= question.validation_max_int_value):
                        errors.update({answer_tag: question.validation_error_msg})
            # Answer must be a float in a particular range
            elif question.validation_type == "is_decimal":
                try:
                    floatanswer = float(answer)
                # Answer is not an integer
                except ValueError:
                    errors.update({answer_tag: question.validation_error_msg})
                else:
                    # Answer is not in the right range
                    if not (question.validation_min_float_value <= floatanswer <= question.validation_max_float_value):
                        errors.update({answer_tag: question.validation_error_msg})

            # Answer must be a date in a particular range
            elif question.validation_type == "is_date":
                raise Exception("Not implemented")
            # Answer must be an email address
            # Note: this validation is very basic:
            #       all the strings of the form
            #       <something>@<anything>.<extension>
            #       will be accepted
            elif question.validation_type == "is_email":
                if not re.match(r"[^@]+@[^@]+\.[^@]+", answer):
                    errors.update({answer_tag: question.validation_error_msg})
            else:
                pass
        return errors

    def validate_numerical_box(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Checks if user input is a number
        if answer:
            try:
                float(answer)
            except ValueError:
                errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_datetime(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Checks if user input is a datetime
        # TODO when datepicker will be available
        return errors

    def validate_simple_choice(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        if question.comments_allowed:
            comment_tag = "%s_%s" % (answer_tag, question.comment_children_ids[0].id)
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer_tag in post:
            errors.update({answer_tag: question.constr_error_msg})
        if question.constr_mandatory and answer_tag in post and post[answer_tag].strip() == '':
            errors.update({answer_tag: question.constr_error_msg})
        # Answer is a comment and is empty
        if question.constr_mandatory and answer_tag in post and post[answer_tag] == "-1" and question.comment_count_as_answer and comment_tag in post and not post[comment_tag].strip():
            errors.update({answer_tag: question.constr_error_msg})
        # There is a comment and it should be validated
        # if question.comment_children_ids[0].validation_required:
        #     _logger.warning("No validation of the comments was implemented")
        return errors

    # def validate_multiple_choice(self, cr, uid, question, post, answer_tag, context=None):
    #     problems = []
    #     return problems

    # def validate_matrix(self, cr, uid, question, post, answer_tag, context=None):
    #     problems = []
    #     return problems


class survey_label(osv.osv):
    ''' A suggested answer for a question '''
    _name = 'survey.label'
    _rec_name = 'value'
    _order = 'sequence'
    _description = 'Survey Label'

    _columns = {
        'question_id': fields.many2one('survey.question', 'Question',
            ondelete='cascade'),
        'question_id_2': fields.many2one('survey.question', 'Question',
            ondelete='cascade'),
        'sequence': fields.integer('Label Sequence order'),
        'value': fields.char("Suggested value", translate=True,
            required=True)
    }


class survey_user_input(osv.osv):
    ''' Metadata for a set of one user's answers to a particular survey '''
    _name = "survey.user_input"
    _rec_name = 'date_create'
    _description = 'Survey User Input'

    _columns = {
        'survey_id': fields.many2one('survey.survey', 'Survey', required=True,
                                     readonly=1, ondelete='restrict'),
        'date_create': fields.datetime('Creation Date', required=True,
                                       readonly=1),
        'deadline': fields.date("Deadline",
                                help="Date by which the person can take part to the survey",
                                oldname="date_deadline"),
        'type': fields.selection([('manually', 'Manually'), ('link', 'Link')],
                                 'Answer Type', required=1, readonly=1,
                                 oldname="response_type"),
        'state': fields.selection([('new', 'Not started yet'),
                                   ('skip', 'Partially completed'),
                                   ('done', 'Completed')],
                                  'Status',
                                  readonly=True),
        'test_entry': fields.boolean('Test entry', readonly=1),
        'token': fields.char("Identification token", readonly=1, required=1),

        # Optional Identification data
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=1),
        'email': fields.char("E-mail", readonly=1),

        # The answers !
        'user_input_line_ids': fields.one2many('survey.user_input_line',
                                               'user_input_id', 'Answers'),
    }
    _defaults = {
        'date_create': fields.datetime.now,
        'type': 'manually',
        'state': 'new',
        'token': lambda s, cr, uid, c: uuid.uuid4().__str__(),
    }

    _sql_constraints = [
        ('unique_token', 'UNIQUE (token)', 'A token must be unique!')
    ]

    def create(self, cr, uid, vals, context=None):
        #if not vals['test_entry']:
        # if survey_obj.exists(cr, uid, survey.id, context=context) == []:
        #     return werkzeug.utils.redirect("/survey/")

        # # In case of auth required, block public user
        # if survey.auth_required and uid == request.registry['website'].get_public_user(request.cr, SUPERUSER_ID, request.context).id:
        #     return request.website.render("website.401")

        # # In case of non open surveys
        # if survey.state != 'open':
        #     return request.website.render("survey.notopen")

        # # If enough surveys completed
        # if survey.user_input_limit > 0:
        #     completed = user_input_obj.search(cr, uid, [('state', '=', 'done')], count=True)
        #     if completed >= survey.user_input_limit:
        #         return request.website.render("survey.notopen")

        # # Manual surveying
        # if not token:
        #     if survey.visible_to_user:
        #         user_input_id = user_input_obj.create(cr, uid, {'survey_id': survey.id})
        #         user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]
        #     else:  # An user cannot open hidden surveys without token
        #         return request.website.render("website.403")
        # else:
        #     try:
        #         user_input_id = user_input_obj.search(cr, uid, [('token', '=', token)])[0]
        #     except IndexError:  # Invalid token
        #         return request.website.render("website.403")
        #     else:
        #         user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]

        return super(survey_user_input, self).create(cr, uid, vals, context)

    #         raise osv.except_osv(_('Warning!'), _('You must enter one or more answers for question "%s" of page %s .') % (vals['question'], page.title))

    def do_clean_emptys(self, cr, uid, automatic=False, context=None):
        ''' Remove empty user inputs that have been created manually

        .. note:
            This function does not remove
        '''
        empty_user_input_ids = self.search(cr, uid, [('type', '=', 'manually'),
                                                     ('state', '=', 'new'),
                                                     ('date_create', '<', (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime(DF))],
                                           context=context)
        if empty_user_input_ids:
            self.unlink(cr, uid, empty_user_input_ids, context=context)

    def action_survey_resent(self, cr, uid, ids, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        context = context or {}
        context.update({
            'survey_resent_token': True,
            'default_partner_ids': record.partner_id and [record.partner_id.id] or [],
            'default_multi_email': record.email or "",
            'default_public': 'email_private',
        })
        return self.pool.get('survey.survey').action_survey_sent(cr, uid,
            [record.survey_id.id], context=context)

    def action_print_response(self, cr, uid, ids, context=None):
        """
        Print Survey Answer in pdf format.
        @return : Dictionary value for created survey answer report
        """
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.browse.response',
            'datas': {
                'model': 'survey.print.statistics',
                'form': {
                    'response_ids': ids,
                    'orientation': 'vertical',
                    'paper_size': 'letter',
                    'page_number': 0,
                    'without_pagebreak': 0
                    }
                },
            }

    def action_preview(self, cr, uid, ids, context=None):
        """
        Get preview response
        """
        context = context or {}
        self.pool.get('survey.survey').check_access_rights(cr, uid, 'write')

        record = self.browse(cr, uid, ids[0], context=context)
        context.update({
            'ir_actions_act_window_target': 'new',
            'survey_id': record.survey_id.id,
            'response_id': ids[0],
            'readonly': True,
        })
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning!'), _('You cannot duplicate this \
            element!'))


class survey_user_input_line(osv.osv):
    _name = 'survey.user_input_line'
    _description = 'Survey User Input Line'
    _rec_name = 'date_create'
    _columns = {
        'user_input_id': fields.many2one('survey.user_input', 'User Input',
                                         ondelete='cascade', required=1),
        'question_id': fields.many2one('survey.question', 'Question',
                                       ondelete='restrict'),
        'page_id': fields.related('question_id', 'page_id', type='many2one',
                                  relation='survey.page', string="Page"),
        'survey_id': fields.related('user_input_id', 'survey_id',
                                    type="many2one", relation="survey.survey",
                                    string='Survey'),
        'date_create': fields.datetime('Create Date', required=1),  # drop
        'skipped': fields.boolean('Skipped'),
        'answer_type': fields.selection([('text', 'Text'),
                                         ('number', 'Number'),
                                         ('date', 'Date'),
                                         ('free_text', 'Free Text'),
                                         ('suggestion', 'Suggestion')],
                                        'Answer Type'),
        'value_text': fields.char("Text answer"),
        'value_number': fields.float("Numerical answer"),
        'value_date': fields.datetime("Date answer"),
        'value_free_text': fields.text("Free Text answer"),
        'value_suggested': fields.many2one('survey.label'),
    }
    _defaults = {
        'skipped': False,
        'date_create': fields.datetime.now
    }

    def save_lines(self, cr, uid, user_input_id, question, post, answer_tag,
                   context=None):
        ''' Save answers to questions, depending on question type

        If an answer already exists for question and user_input_id, it will be
        overwritten (in order to maintain data consistency). '''
        try:
            saver = getattr(self, 'save_line_' + question.type)
        except AttributeError:
            _logger.error(question.type + ": This type of question has no saving function")
            return False
        else:
            saver(cr, uid, user_input_id, question, post, answer_tag, context=context)

    def save_line_free_text(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
        }
        if answer_tag in post:
            vals.update({'answer_type': 'free_text', 'value_free_text': post[answer_tag]})
        else:
            vals.update({'skipped': True})
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.write(cr, uid, old_uil[0], vals, context=context)
        else:
            self.create(cr, uid, vals, context=context)
        return True

    def save_line_textbox(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
        }
        if answer_tag in post:
            vals.update({'answer_type': 'text', 'value_text': post[answer_tag]})
        else:
            vals.update({'skipped': True})
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.write(cr, uid, old_uil[0], vals, context=context)
        else:
            self.create(cr, uid, vals, context=context)
        return True

    def save_line_numerical_box(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
        }
        if answer_tag in post:
            vals.update({'answer_type': 'number', 'value_number': float(post[answer_tag])})
        else:
            vals.update({'skipped': True})
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.write(cr, uid, old_uil[0], vals, context=context)
        else:
            self.create(cr, uid, vals, context=context)
        return True

    def save_line_datetime(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
        }
        if answer_tag in post:
            vals.update({'answer_type': 'date', 'value_date': post[answer_tag]})
        else:
            vals.update({'skipped': True})
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.write(cr, uid, old_uil[0], vals, context=context)
        else:
            self.create(cr, uid, vals, context=context)
        return True


def dict_keys_startswith(dictionary, string):
    '''Returns a dictionary containing the elements of <dict> whose keys start
    with <string>.

    .. note::
        This function uses dictionary comprehensions (Python >= 2.7)'''
    return {k: dictionary[k] for k in filter(lambda key: key.startswith(string), dictionary.keys())}

# vim: exp and tab: smartindent: tabstop=4: softtabstop=4: shiftwidth=4:
