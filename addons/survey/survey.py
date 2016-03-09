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
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from openerp.addons.website.models.website import slug
from urlparse import urljoin
from itertools import product
from collections import Counter
from collections import OrderedDict

import datetime
import logging
import re
import uuid

_logger = logging.getLogger(__name__)

class survey_stage(osv.Model):
    """Stages for Kanban view of surveys"""

    _name = 'survey.stage'
    _description = 'Survey Stage'
    _order = 'sequence,id'

    _columns = {
        'name': fields.char(string="Name", required=True, translate=True),
        'sequence': fields.integer(string="Sequence"),
        'closed': fields.boolean(string="Closed", help="If closed, people won't be able to answer to surveys in this column."),
        'fold': fields.boolean(string="Folded in kanban view")
    }
    _defaults = {
        'sequence': 1,
        'closed': False
    }
    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]


class survey_survey(osv.Model):
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

    def _is_designed(self, cr, uid, ids, name, arg, context=None):
        res = dict()
        for survey in self.browse(cr, uid, ids, context=context):
            if not survey.page_ids or not [page.question_ids
                            for page in survey.page_ids if page.question_ids]:
                res[survey.id] = False
            else:
                res[survey.id] = True
        return res

    def _get_tot_sent_survey(self, cr, uid, ids, name, arg, context=None):
        """ Returns the number of invitations sent for this survey, be they
        (partially) completed or not """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.user_input')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid,  # SUPERUSER_ID,
                [('survey_id', '=', id), ('type', '=', 'link')],
                context=context, count=True)
        return res

    def _get_tot_start_survey(self, cr, uid, ids, name, arg, context=None):
        """ Returns the number of started instances of this survey, be they
        completed or not """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.user_input')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid,  # SUPERUSER_ID,
                ['&', ('survey_id', '=', id), '|', ('state', '=', 'skip'), ('state', '=', 'done')],
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
        if context and context.get('relative_url'):
            base_url = '/'
        else:
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        res = {}
        for survey in self.browse(cr, uid, ids, context=context):
            res[survey.id] = urljoin(base_url, "survey/start/%s" % slug(survey))
        return res

    def _get_public_url_html(self, cr, uid, ids, name, arg, context=None):
        """ Computes a public URL for the survey (html-embeddable version)"""
        urls = self._get_public_url(cr, uid, ids, name, arg, context=context)
        for id, url in urls.iteritems():
            urls[id] = '<a href="%s">%s</a>' % (url, _("Click here to start survey"))
        return urls

    def _get_print_url(self, cr, uid, ids, name, arg, context=None):
        """ Computes a printing URL for the survey """
        if context and context.get('relative_url'):
            base_url = '/'
        else:
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        res = {}
        for survey in self.browse(cr, uid, ids, context=context):
            res[survey.id] = urljoin(base_url, "survey/print/%s" % slug(survey))
        return res

    def _get_result_url(self, cr, uid, ids, name, arg, context=None):
        """ Computes an URL for the survey results """
        if context and context.get('relative_url'):
            base_url = '/'
        else:
            base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        res = {}
        for survey in self.browse(cr, uid, ids, context=context):
            res[survey.id] = urljoin(base_url, "survey/results/%s" % slug(survey))
        return res

    # Model fields #

    _columns = {
        'title': fields.char('Title', required=1, translate=True),
        'res_model': fields.char('Category'),
        'page_ids': fields.one2many('survey.page', 'survey_id', 'Pages', copy=True),
        'stage_id': fields.many2one('survey.stage', string="Stage", ondelete="set null", copy=False),
        'auth_required': fields.boolean('Login required',
            help="Users with a public link will be requested to login before taking part to the survey",
            oldname="authenticate"),
        'users_can_go_back': fields.boolean('Users can go back',
            help="If checked, users can go back to previous pages."),
        'tot_sent_survey': fields.function(_get_tot_sent_survey,
            string="Number of sent surveys", type="integer"),
        'tot_start_survey': fields.function(_get_tot_start_survey,
            string="Number of started surveys", type="integer"),
        'tot_comp_survey': fields.function(_get_tot_comp_survey,
            string="Number of completed surveys", type="integer"),
        'description': fields.html('Description', translate=True,
            oldname="description", help="A long description of the purpose of the survey"),
        'color': fields.integer('Color Index'),
        'user_input_ids': fields.one2many('survey.user_input', 'survey_id',
            'User responses', readonly=1),
        'designed': fields.function(_is_designed, string="Is designed?",
            type="boolean"),
        'public_url': fields.function(_get_public_url,
            string="Public link", type="char"),
        'public_url_html': fields.function(_get_public_url_html,
            string="Public link (html version)", type="char"),
        'print_url': fields.function(_get_print_url,
            string="Print link", type="char"),
        'result_url': fields.function(_get_result_url,
            string="Results link", type="char"),
        'email_template_id': fields.many2one('email.template',
            'Email Template', ondelete='set null'),
        'thank_you_message': fields.html('Thank you message', translate=True,
            help="This message will be displayed when survey is completed"),
        'quizz_mode': fields.boolean(string='Quiz mode')
    }

    def _default_stage(self, cr, uid, context=None):
        ids = self.pool['survey.stage'].search(cr, uid, [], limit=1, context=context)
        if ids:
            return ids[0]
        return False

    _defaults = {
        'color': 0,
        'stage_id': lambda self, *a, **kw: self._default_stage(*a, **kw)
    }

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        """ Read group customization in order to display all the stages in the
        kanban view, even if they are empty """
        stage_obj = self.pool.get('survey.stage')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = stage_obj._search(cr, uid, [], order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    # Public methods #

    def copy_data(self, cr, uid, id, default=None, context=None):
        current_rec = self.read(cr, uid, id, fields=['title'], context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        default = dict(default or {}, title=title)
        return super(survey_survey, self).copy_data(cr, uid, id, default,
            context=context)

    def next_page(self, cr, uid, user_input, page_id, go_back=False, context=None):
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

    def filter_input_ids(self, cr, uid, survey, filters, finished=False, context=None):
        '''If user applies any filters, then this function returns list of
           filtered user_input_id and label's strings for display data in web.
           :param filters: list of dictionary (having: row_id, ansewr_id)
           :param finished: True for completely filled survey,Falser otherwise.
           :returns list of filtered user_input_ids.
        '''
        context = context if context else {}
        if filters:
            input_line_obj = self.pool.get('survey.user_input_line')
            domain_filter, choice, filter_display_data = [], [], []
            for filter in filters:
                row_id, answer_id = filter['row_id'], filter['answer_id']
                if row_id == 0:
                    choice.append(answer_id)
                else:
                    domain_filter.extend(['|', ('value_suggested_row.id', '=', row_id), ('value_suggested.id', '=', answer_id)])
            if choice:
                domain_filter.insert(0, ('value_suggested.id', 'in', choice))
            else:
                domain_filter = domain_filter[1:]
            line_ids = input_line_obj.search(cr, uid, domain_filter, context=context)
            filtered_input_ids = [input.user_input_id.id for input in input_line_obj.browse(cr, uid, line_ids, context=context)]
        else:
            filtered_input_ids, filter_display_data = [], []
        if finished:
            user_input = self.pool.get('survey.user_input')
            if not filtered_input_ids:
                current_filters = user_input.search(cr, uid, [('survey_id', '=', survey.id)], context=context)
                user_input_objs = user_input.browse(cr, uid, current_filters, context=context)
            else:
                user_input_objs = user_input.browse(cr, uid, filtered_input_ids, context=context)
            return [input.id for input in user_input_objs if input.state == 'done']
        return filtered_input_ids

    def get_filter_display_data(self, cr, uid, filters, context):
        '''Returns data to display current filters
        :param filters: list of dictionary (having: row_id, answer_id)
        :param finished: True for completely filled survey, False otherwise.
        :returns list of dict having data to display filters.
        '''
        filter_display_data = []
        if filters:
            question_obj = self.pool.get('survey.question')
            label_obj = self.pool.get('survey.label')
            for filter in filters:
                row_id, answer_id = filter['row_id'], filter['answer_id']
                question_id = label_obj.browse(cr, uid, answer_id, context=context).question_id.id
                question = question_obj.browse(cr, uid, question_id, context=context)
                if row_id == 0:
                    labels = label_obj.browse(cr, uid, [answer_id], context=context)
                else:
                    labels = label_obj.browse(cr, uid, [row_id, answer_id], context=context)
                filter_display_data.append({'question_text': question.question, 'labels': [label.value for label in labels]})
        return filter_display_data

    def prepare_result(self, cr, uid, question, current_filters=None, context=None):
        ''' Compute statistical data for questions by counting number of vote per choice on basis of filter '''
        current_filters = current_filters if current_filters else []
        context = context if context else {}
        result_summary = {}

        #Calculate and return statistics for choice
        if question.type in ['simple_choice', 'multiple_choice']:
            answers = {}
            comments = []
            [answers.update({label.id: {'text': label.value, 'count': 0, 'answer_id': label.id}}) for label in question.labels_ids]
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and answers.get(input_line.value_suggested.id) and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    answers[input_line.value_suggested.id]['count'] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': answers.values(), 'comments': comments}

        #Calculate and return statistics for matrix
        if question.type == 'matrix':
            rows = OrderedDict()
            answers = OrderedDict()
            res = dict()
            comments = []
            [rows.update({label.id: label.value}) for label in question.labels_ids_2]
            [answers.update({label.id: label.value}) for label in question.labels_ids]
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
                                       'most_comman': Counter(all_inputs).most_common(5)})
        return result_summary

    def get_input_summary(self, cr, uid, question, current_filters=None, context=None):
        ''' Returns overall summary of question e.g. answered, skipped, total_inputs on basis of filter '''
        current_filters = current_filters if current_filters else []
        context = context if context else {}
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

    # Actions

    def action_start_survey(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey form '''
        trail = ""
        context = dict(context or {}, relative_url=True)
        if 'survey_token' in context:
            trail = "/" + context['survey_token']
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': self.read(cr, uid, ids, ['public_url'], context=context)[0]['public_url'] + trail
        }

    def action_send_survey(self, cr, uid, ids, context=None):
        ''' Open a window to compose an email, pre-filled with the survey
        message '''
        if not self._has_questions(cr, uid, ids, context=None):
            raise osv.except_osv(_('Error!'), _('You cannot send an invitation for a survey that has no questions.'))

        survey_browse = self.pool.get('survey.survey').browse(cr, uid, ids,
            context=context)[0]
        if survey_browse.stage_id.closed:
            raise osv.except_osv(_('Warning!'),
                _("You cannot send invitations for closed surveys."))

        assert len(ids) == 1, 'This option should only be used for a single \
                                survey at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        templates = ir_model_data.get_object_reference(cr, uid,
                                'survey', 'email_template_survey')
        template_id = templates[1] if len(templates) > 0 else False
        ctx = dict(context)

        ctx.update({'default_model': 'survey.survey',
                    'default_res_id': ids[0],
                    'default_survey_id': ids[0],
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id,
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

    def action_print_survey(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey printable view '''
        trail = ""
        context = dict(context or {}, relative_url=True)
        if 'survey_token' in context:
            trail = "/" + context['survey_token']
        return {
            'type': 'ir.actions.act_url',
            'name': "Print Survey",
            'target': 'self',
            'url': self.read(cr, uid, ids, ['print_url'], context=context)[0]['print_url'] + trail
        }

    def action_result_survey(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey results view '''
        context = dict(context or {}, relative_url=True)
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': self.read(cr, uid, ids, ['result_url'], context=context)[0]['result_url']
        }

    def action_test_survey(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey form into test mode'''
        context = dict(context or {}, relative_url=True)
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': self.read(cr, uid, ids, ['public_url'], context=context)[0]['public_url'] + "/phantom"
        }




class survey_page(osv.Model):
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

    _columns = {
        'title': fields.char('Page Title', required=1,
            translate=True),
        'survey_id': fields.many2one('survey.survey', 'Survey',
            ondelete='cascade', required=True),
        'question_ids': fields.one2many('survey.question', 'page_id',
            'Questions', copy=True),
        'sequence': fields.integer('Page number'),
        'description': fields.html('Description',
            help="An introductory text to your page", translate=True,
            oldname="note"),
    }
    _defaults = {
        'sequence': 10
    }

    # Public methods #

    def copy_data(self, cr, uid, ids, default=None, context=None):
        current_rec = self.read(cr, uid, ids, fields=['title'], context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        default = dict(default or {}, title=title)
        return super(survey_page, self).copy_data(cr, uid, ids, default,
            context=context)


class survey_question(osv.Model):
    ''' Questions that will be asked in a survey.

    Each question can have one of more suggested answers (eg. in case of
    dropdown choices, multi-answer checkboxes, radio buttons...).'''
    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence,id'

    # Model fields #

    _columns = {
        # Question metadata
        'page_id': fields.many2one('survey.page', 'Survey page',
            ondelete='cascade', required=1),
        'survey_id': fields.related('page_id', 'survey_id', type='many2one',
            relation='survey.survey', string='Survey'),
        'sequence': fields.integer(string='Sequence'),

        # Question
        'question': fields.char('Question Name', required=1, translate=True),
        'description': fields.html('Description', help="Use this field to add \
            additional explanations about your question", translate=True,
            oldname='descriptive_text'),

        # Answer
        'type': fields.selection([('free_text', 'Long Text Zone'),
                ('textbox', 'Text Input'),
                ('numerical_box', 'Numerical Value'),
                ('datetime', 'Date and Time'),
                ('simple_choice', 'Multiple choice: only one answer'),
                ('multiple_choice', 'Multiple choice: multiple answers allowed'),
                ('matrix', 'Matrix')], 'Type of Question', size=15, required=1),
        'matrix_subtype': fields.selection([('simple', 'One choice per row'),
            ('multiple', 'Multiple choices per row')], 'Matrix Type'),
        'labels_ids': fields.one2many('survey.label',
            'question_id', 'Types of answers', oldname='answer_choice_ids', copy=True),
        'labels_ids_2': fields.one2many('survey.label',
            'question_id_2', 'Rows of the Matrix', copy=True),
        # labels are used for proposed choices
        # if question.type == simple choice | multiple choice
        #                    -> only labels_ids is used
        # if question.type == matrix
        #                    -> labels_ids are the columns of the matrix
        #                    -> labels_ids_2 are the rows of the matrix

        # Display options
        'column_nb': fields.selection([('12', '1'),
                                       ('6', '2'),
                                       ('4', '3'),
                                       ('3', '4'),
                                       ('2', '6')],
            'Number of columns'),
            # These options refer to col-xx-[12|6|4|3|2] classes in Bootstrap
        'display_mode': fields.selection([('columns', 'Radio Buttons/Checkboxes'),
                                          ('dropdown', 'Selection Box')],
                                         'Display mode'),

        # Comments
        'comments_allowed': fields.boolean('Show Comments Field',
            oldname="allow_comment"),
        'comments_message': fields.char('Comment Message', translate=True),
        'comment_count_as_answer': fields.boolean('Comment Field is an Answer Choice',
            oldname='make_comment_field'),

        # Validation
        'validation_required': fields.boolean('Validate entry',
            oldname='is_validation_require'),
        'validation_email': fields.boolean('Input must be an email'),
        'validation_length_min': fields.integer('Minimum Text Length'),
        'validation_length_max': fields.integer('Maximum Text Length'),
        'validation_min_float_value': fields.float('Minimum value'),
        'validation_max_float_value': fields.float('Maximum value'),
        'validation_min_date': fields.datetime('Minimum Date'),
        'validation_max_date': fields.datetime('Maximum Date'),
        'validation_error_msg': fields.char('Error message',
                                            oldname='validation_valid_err_msg',
                                            translate=True),

        # Constraints on number of answers (matrices)
        'constr_mandatory': fields.boolean('Mandatory Answer',
            oldname="is_require_answer"),
        'constr_error_msg': fields.char("Error message",
            oldname='req_error_msg', translate=True),
        'user_input_line_ids': fields.one2many('survey.user_input_line',
                                               'question_id', 'Answers',
                                               domain=[('skipped', '=', False)]),
    }

    _defaults = {
        'page_id': lambda self, cr, uid, context: context.get('page_id'),
        'sequence': 10,
        'type': 'free_text',
        'matrix_subtype': 'simple',
        'column_nb': '12',
        'display_mode': 'columns',
        'constr_error_msg': lambda s, cr, uid, c: _('This question requires an answer.'),
        'validation_error_msg': lambda s, cr, uid, c: _('The answer you entered has an invalid format.'),
        'validation_required': False,
        'comments_message': lambda s, cr, uid, c: _('If other, precise:'),
    }

    _sql_constraints = [
        ('positive_len_min', 'CHECK (validation_length_min >= 0)', 'A length must be positive!'),
        ('positive_len_max', 'CHECK (validation_length_max >= 0)', 'A length must be positive!'),
        ('validation_length', 'CHECK (validation_length_min <= validation_length_max)', 'Max length cannot be smaller than min length!'),
        ('validation_float', 'CHECK (validation_min_float_value <= validation_max_float_value)', 'Max value cannot be smaller than min value!'),
        ('validation_date', 'CHECK (validation_min_date <= validation_max_date)', 'Max date cannot be smaller than min date!')
    ]

    def copy_data(self, cr, uid, ids, default=None, context=None):
        current_rec = self.read(cr, uid, ids, context=context)
        question = _("%s (copy)") % (current_rec.get('question'))
        default = dict(default or {}, question=question)
        return super(survey_question, self).copy_data(cr, uid, ids, default,
            context=context)

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
        # Email format validation
        # Note: this validation is very basic:
        #     all the strings of the form
        #     <something>@<anything>.<extension>
        #     will be accepted
        if answer and question.validation_email:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", answer):
                errors.update({answer_tag: _('This answer must be an email address')})
        # Answer validation (if properly defined)
        # Length of the answer must be in a range
        if answer and question.validation_required:
            if not (question.validation_length_min <= len(answer) <= question.validation_length_max):
                errors.update({answer_tag: question.validation_error_msg})
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
                floatanswer = float(answer)
            except ValueError:
                errors.update({answer_tag: _('This is not a number')})
        # Answer validation (if properly defined)
        if answer and question.validation_required:
            # Answer is not in the right range
            try:
                floatanswer = float(answer)  # check that it is a float has been done hereunder
                if not (question.validation_min_float_value <= floatanswer <= question.validation_max_float_value):
                    errors.update({answer_tag: question.validation_error_msg})
            except ValueError:
                pass
        return errors

    def validate_datetime(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Checks if user input is a datetime
        if answer:
            try:
                dateanswer = datetime.datetime.strptime(answer, DF)
            except ValueError:
                errors.update({answer_tag: _('This is not a date/time')})
                return errors
        # Answer validation (if properly defined)
        if answer and question.validation_required:
            # Answer is not in the right range
            try:
                dateanswer = datetime.datetime.strptime(answer, DF)
                if not (datetime.datetime.strptime(question.validation_min_date, DF) <= dateanswer <= datetime.datetime.strptime(question.validation_max_date, DF)):
                    errors.update({answer_tag: question.validation_error_msg})
            except ValueError:  # check that it is a datetime has been done hereunder
                pass
        return errors

    def validate_simple_choice(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        if question.comments_allowed:
            comment_tag = "%s_%s" % (answer_tag, 'comment')
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer_tag in post:
            errors.update({answer_tag: question.constr_error_msg})
        if question.constr_mandatory and answer_tag in post and post[answer_tag].strip() == '':
            errors.update({answer_tag: question.constr_error_msg})
        # Answer is a comment and is empty
        if question.constr_mandatory and answer_tag in post and post[answer_tag] == "-1" and question.comment_count_as_answer and comment_tag in post and not post[comment_tag].strip():
            errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_multiple_choice(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        if question.constr_mandatory:
            answer_candidates = dict_keys_startswith(post, answer_tag)
            comment_flag = answer_candidates.pop(("%s_%s" % (answer_tag, -1)), None)
            if question.comments_allowed:
                comment_answer = answer_candidates.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
            # There is no answer neither comments (if comments count as answer)
            if not answer_candidates and question.comment_count_as_answer and (not comment_flag or not comment_answer):
                errors.update({answer_tag: question.constr_error_msg})
            # There is no answer at all
            if not answer_candidates and not question.comment_count_as_answer:
                errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_matrix(self, cr, uid, question, post, answer_tag, context=None):
        errors = {}
        if question.constr_mandatory:
            lines_number = len(question.labels_ids_2)
            answer_candidates = dict_keys_startswith(post, answer_tag)
            comment_answer = answer_candidates.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
            # Number of lines that have been answered
            if question.matrix_subtype == 'simple':
                answer_number = len(answer_candidates)
            elif question.matrix_subtype == 'multiple':
                answer_number = len(set([sk.rsplit('_', 1)[0] for sk in answer_candidates.keys()]))
            else:
                raise RuntimeError("Invalid matrix subtype")
            # Validate that each line has been answered
            if answer_number != lines_number:
                errors.update({answer_tag: question.constr_error_msg})
        return errors


class survey_label(osv.Model):
    ''' A suggested answer for a question '''
    _name = 'survey.label'
    _rec_name = 'value'
    _order = 'sequence,id'
    _description = 'Survey Label'

    def _check_question_not_empty(self, cr, uid, ids, context=None):
        '''Ensure that field question_id XOR field question_id_2 is not null'''
        for label in self.browse(cr, uid, ids, context=context):
            # 'bool()' is required in order to make '!=' act as XOR with objects
            return bool(label.question_id) != bool(label.question_id_2)

    _columns = {
        'question_id': fields.many2one('survey.question', 'Question',
            ondelete='cascade'),
        'question_id_2': fields.many2one('survey.question', 'Question',
            ondelete='cascade'),
        'sequence': fields.integer('Label Sequence order'),
        'value': fields.char("Suggested value", translate=True,
            required=True),
        'quizz_mark': fields.float('Score for this answer', help="A positive score indicates a correct answer; a negative or null score indicates a wrong answer"),
    }
    _defaults = {
        'sequence': 10,
    }
    _constraints = [
        (_check_question_not_empty, "A label must be attached to one and only one question", ['question_id', 'question_id_2'])
    ]


class survey_user_input(osv.Model):
    ''' Metadata for a set of one user's answers to a particular survey '''
    _name = "survey.user_input"
    _rec_name = 'date_create'
    _description = 'Survey User Input'

    def _quizz_get_score(self, cr, uid, ids, name, args, context=None):
        ret = dict()
        for user_input in self.browse(cr, uid, ids, context=context):
            ret[user_input.id] = sum([uil.quizz_mark for uil in user_input.user_input_line_ids] or [0.0])
        return ret

    _columns = {
        'survey_id': fields.many2one('survey.survey', 'Survey', required=True,
                                     readonly=1, ondelete='restrict'),
        'date_create': fields.datetime('Creation Date', required=True,
                                       readonly=1, copy=False),
        'deadline': fields.datetime("Deadline",
                                help="Date by which the person can open the survey and submit answers",
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
        'token': fields.char("Identification token", readonly=1, required=1, copy=False),

        # Optional Identification data
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=1),
        'email': fields.char("E-mail", readonly=1),

        # Displaying data
        'last_displayed_page_id': fields.many2one('survey.page',
                                              'Last displayed page'),
        # The answers !
        'user_input_line_ids': fields.one2many('survey.user_input_line',
                                               'user_input_id', 'Answers', copy=True),

        # URLs used to display the answers
        'result_url': fields.related('survey_id', 'result_url', type='char',
                                     string="Public link to the survey results"),
        'print_url': fields.related('survey_id', 'print_url', type='char',
                                    string="Public link to the empty survey"),

        'quizz_score': fields.function(_quizz_get_score, type="float", string="Score for the quiz")
    }
    _defaults = {
        'date_create': fields.datetime.now,
        'type': 'manually',
        'state': 'new',
        'token': lambda s, cr, uid, c: uuid.uuid4().__str__(),
        'quizz_score': 0.0,
    }

    _sql_constraints = [
        ('unique_token', 'UNIQUE (token)', 'A token must be unique!'),
        ('deadline_in_the_past', 'CHECK (deadline >= date_create)', 'The deadline cannot be in the past')
    ]

    def do_clean_emptys(self, cr, uid, automatic=False, context=None):
        ''' Remove empty user inputs that have been created manually
            (used as a cronjob declared in data/survey_cron.xml) '''
        empty_user_input_ids = self.search(cr, uid, [('type', '=', 'manually'),
                                                     ('state', '=', 'new'),
                                                     ('date_create', '<', (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime(DF))],
                                           context=context)
        if empty_user_input_ids:
            self.unlink(cr, uid, empty_user_input_ids, context=context)

    def action_survey_resent(self, cr, uid, ids, context=None):
        ''' Sent again the invitation '''
        record = self.browse(cr, uid, ids[0], context=context)
        context = dict(context or {})
        context.update({
            'survey_resent_token': True,
            'default_partner_ids': record.partner_id and [record.partner_id.id] or [],
            'default_multi_email': record.email or "",
            'default_public': 'email_private',
        })
        return self.pool.get('survey.survey').action_send_survey(cr, uid,
            [record.survey_id.id], context=context)

    def action_view_answers(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey form '''
        user_input = self.read(cr, uid, ids, ['print_url', 'token'], context=context)[0]
        return {
            'type': 'ir.actions.act_url',
            'name': "View Answers",
            'target': 'self',
            'url': '%s/%s' % (user_input['print_url'], user_input['token'])
        }

    def action_survey_results(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey results '''
        return {
            'type': 'ir.actions.act_url',
            'name': "Survey Results",
            'target': 'self',
            'url': self.read(cr, uid, ids, ['result_url'], context=context)[0]['result_url']
        }


class survey_user_input_line(osv.Model):
    _name = 'survey.user_input_line'
    _description = 'Survey User Input Line'
    _rec_name = 'date_create'

    def _answered_or_skipped(self, cr, uid, ids, context=None):
        for uil in self.browse(cr, uid, ids, context=context):
            # 'bool()' is required in order to make '!=' act as XOR with objects
            return uil.skipped != bool(uil.answer_type)

    def _check_answer_type(self, cr, uid, ids, context=None):
        for uil in self.browse(cr, uid, ids, context=None):
            if uil.answer_type:
                if uil.answer_type == 'text':
                    # 'bool()' is required in order to make '!=' act as XOR with objects
                    return bool(uil.value_text)
                elif uil.answer_type == 'number':
                    return (uil.value_number == 0) or (uil.value_number != False)
                elif uil.answer_type == 'date':
                    return bool(uil.value_date)
                elif uil.answer_type == 'free_text':
                    return bool(uil.value_free_text)
                elif uil.answer_type == 'suggestion':
                    return bool(uil.value_suggested)
            return True

    _columns = {
        'user_input_id': fields.many2one('survey.user_input', 'User Input',
                                         ondelete='cascade', required=1),
        'question_id': fields.many2one('survey.question', 'Question',
                                       ondelete='restrict', required=1),
        'page_id': fields.related('question_id', 'page_id', type='many2one',
                                  relation='survey.page', string="Page"),
        'survey_id': fields.related('user_input_id', 'survey_id',
                                    type="many2one", relation="survey.survey",
                                    string='Survey', store=True),
        'date_create': fields.datetime('Create Date', required=1),
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
        'value_suggested': fields.many2one('survey.label', "Suggested answer"),
        'value_suggested_row': fields.many2one('survey.label', "Row answer"),
        'quizz_mark': fields.float("Score given for this answer")
    }

    _defaults = {
        'skipped': False,
        'date_create': fields.datetime.now()
    }
    _constraints = [
        (_answered_or_skipped, "A question cannot be unanswered and skipped", ['skipped', 'answer_type']),
        (_check_answer_type, "The answer must be in the right type", ['answer_type', 'text', 'number', 'date', 'free_text', 'suggestion'])
    ]

    def __get_mark(self, cr, uid, value_suggested, context=None):
        try:
            mark = self.pool.get('survey.label').browse(cr, uid, int(value_suggested), context=context).quizz_mark
        except AttributeError:
            mark = 0.0
        except KeyError:
            mark = 0.0
        except ValueError:
            mark = 0.0
        return mark

    def create(self, cr, uid, vals, context=None):
        value_suggested = vals.get('value_suggested')
        if value_suggested:
            vals.update({'quizz_mark': self.__get_mark(cr, uid, value_suggested)})
        return super(survey_user_input_line, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        value_suggested = vals.get('value_suggested')
        if value_suggested:
            vals.update({'quizz_mark': self.__get_mark(cr, uid, value_suggested)})
        return super(survey_user_input_line, self).write(cr, uid, ids, vals, context=context)

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
            'skipped': False,
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'free_text', 'value_free_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
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
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'text', 'value_text': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
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
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'number', 'value_number': float(post[answer_tag])})
        else:
            vals.update({'answer_type': None, 'skipped': True})
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
            'skipped': False
        }
        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'date', 'value_date': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.write(cr, uid, old_uil[0], vals, context=context)
        else:
            self.create(cr, uid, vals, context=context)
        return True

    def save_line_simple_choice(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.unlink(cr, SUPERUSER_ID, old_uil, context=context)

        if answer_tag in post and post[answer_tag].strip() != '':
            vals.update({'answer_type': 'suggestion', 'value_suggested': post[answer_tag]})
        else:
            vals.update({'answer_type': None, 'skipped': True})

        # '-1' indicates 'comment count as an answer' so do not need to record it
        if post.get(answer_tag) and post.get(answer_tag) != '-1':
            self.create(cr, uid, vals, context=context)

        comment_answer = post.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer, 'skipped': False, 'value_suggested': False})
            self.create(cr, uid, vals, context=context)

        return True

    def save_line_multiple_choice(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.unlink(cr, SUPERUSER_ID, old_uil, context=context)

        ca = dict_keys_startswith(post, answer_tag)
        comment_answer = ca.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if len(ca) > 0:
            for a in ca:
                # '-1' indicates 'comment count as an answer' so do not need to record it
                if a != ('%s_%s' % (answer_tag, '-1')):
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca[a]})
                    self.create(cr, uid, vals, context=context)
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer, 'value_suggested': False})
            self.create(cr, uid, vals, context=context)
        if not ca and not comment_answer:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(cr, uid, vals, context=context)
        return True

    def save_line_matrix(self, cr, uid, user_input_id, question, post, answer_tag, context=None):
        vals = {
            'user_input_id': user_input_id,
            'question_id': question.id,
            'page_id': question.page_id.id,
            'survey_id': question.survey_id.id,
            'skipped': False
        }
        old_uil = self.search(cr, uid, [('user_input_id', '=', user_input_id),
                                        ('survey_id', '=', question.survey_id.id),
                                        ('question_id', '=', question.id)],
                              context=context)
        if old_uil:
            self.unlink(cr, SUPERUSER_ID, old_uil, context=context)

        no_answers = True
        ca = dict_keys_startswith(post, answer_tag)

        comment_answer = ca.pop(("%s_%s" % (answer_tag, 'comment')), '').strip()
        if comment_answer:
            vals.update({'answer_type': 'text', 'value_text': comment_answer})
            self.create(cr, uid, vals, context=context)
            no_answers = False

        if question.matrix_subtype == 'simple':
            for row in question.labels_ids_2:
                a_tag = "%s_%s" % (answer_tag, row.id)
                if a_tag in ca:
                    no_answers = False
                    vals.update({'answer_type': 'suggestion', 'value_suggested': ca[a_tag], 'value_suggested_row': row.id})
                    self.create(cr, uid, vals, context=context)

        elif question.matrix_subtype == 'multiple':
            for col in question.labels_ids:
                for row in question.labels_ids_2:
                    a_tag = "%s_%s_%s" % (answer_tag, row.id, col.id)
                    if a_tag in ca:
                        no_answers = False
                        vals.update({'answer_type': 'suggestion', 'value_suggested': col.id, 'value_suggested_row': row.id})
                        self.create(cr, uid, vals, context=context)
        if no_answers:
            vals.update({'answer_type': None, 'skipped': True})
            self.create(cr, uid, vals, context=context)
        return True


def dict_keys_startswith(dictionary, string):
    '''Returns a dictionary containing the elements of <dict> whose keys start
    with <string>.

    .. note::
        This function uses dictionary comprehensions (Python >= 2.7)'''
    return {k: dictionary[k] for k in filter(lambda key: key.startswith(string), dictionary.keys())}
