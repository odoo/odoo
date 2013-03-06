# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http: //www.openerp.com>
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
#    along with this program.  If not, see <http: //www.gnu.org/licenses/>.
#
##############################################################################

import copy
from urllib import urlencode
from urlparse import urljoin
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
import uuid


class survey_type(osv.osv):
    _name = 'survey.type'
    _description = 'Survey Type'
    _columns = {
        'name': fields.char("Name", size=128, required=1, translate=True),
    }
survey_type()


class survey(osv.osv):
    _name = 'survey'
    _description = 'Survey'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _needaction_domain_get(self, cr, uid, context=None):
        return ['&', ('response_ids.state', 'in', ['new', 'skip']), ('response_ids.partner_id.user_id', '=', uid)]

    def default_get(self, cr, uid, fields, context=None):
        data = super(survey, self).default_get(cr, uid, fields, context)
        return data

    def _get_tot_start_survey(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.response')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid, [('survey_id', '=', id), ('state', '=', 'skip')], context=context, count=True)
        return res

    def _get_tot_comp_survey(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, 0) for id in ids)
        sur_res_obj = self.pool.get('survey.response')
        for id in ids:
            res[id] = sur_res_obj.search(cr, uid, [('survey_id', '=', id), ('state', '=', 'done')], context=context, count=True)
        return res

    def _get_public_url(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user. """
        res = dict((id, 0) for id in ids)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        survey_obj = self.pool.get('survey')
        for survey_browse in survey_obj.browse(cr, uid, ids, context=context):
            query = {
                'db': cr.dbname
            }
            fragment = {
                'active_id': survey_browse.id,
                'action': 'survey.action_filling',
                'params': survey_browse.token,
            }
            res[survey_browse.id] = urljoin(base_url, "?%s#%s" % (urlencode(query), urlencode(fragment)))
        return res

    _columns = {
        'title': fields.char('Survey Title', size=128, required=1, translate=True),
        'page_ids': fields.one2many('survey.page', 'survey_id', 'Page'),
        'date_open': fields.datetime('Survey Open Date', readonly=1),
        'date_close': fields.datetime('Survey Close Date', readonly=1),
        'max_response_limit': fields.integer('Maximum Answer Limit', help="Set to one if survey is answerable only once"),
        'state': fields.selection([('draft', 'Draft'), ('open', 'Open'), ('close', 'Close'), ('cancel', 'Cancelled')], 'Status', required=1),
        'authenticate': fields.boolean('User must be authentified'),
        'tot_start_survey': fields.function(_get_tot_start_survey, string="Total Started Survey", type="integer"),
        'tot_comp_survey': fields.function(_get_tot_comp_survey, string="Total Completed Survey", type="integer"),
        'note': fields.text('Description', size=128, translate=True),
        'type': fields.many2one('survey.type', 'Type'),
        'color': fields.integer('Color Index'),
        'response_ids': fields.one2many('survey.response', 'survey_id', 'Responses', readonly=1),
        'public_url': fields.function(_get_public_url, string="Public web link", type="char"),
        'token': fields.char('Public token', size=8, required=1),
    }
    _defaults = {
        'state': "draft",
        'authenticate': False,
        'date_open': fields.datetime.now,
        'token': lambda s, cr, uid, c: uuid.uuid4(),
    }

    def survey_draft(self, cr, uid, ids, arg):
        return self.write(cr, uid, ids, {'state': 'draft', 'date_open': None})

    def survey_open(self, cr, uid, ids, arg):
        return self.write(cr, uid, ids, {'state': 'open', 'date_open': datetime.now()})

    def survey_close(self, cr, uid, ids, arg):
        return self.write(cr, uid, ids, {'state': 'close', 'date_close': datetime.now()})

    def survey_cancel(self, cr, uid, ids, arg):
        return self.write(cr, uid, ids, {'state': 'cancel', 'date_close': datetime.now()})

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        vals.update({'title': title})
        return super(survey, self).copy(cr, uid, ids, vals, context=context)

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID forsecurity checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary forcontextual values
        @return: Dictionary value forprint survey form.
        """
        if context is None:
            context = {}
        datas = {}
        if 'response_id' in context:
            response_id = context.get('response_id', 0)
            datas['ids'] = [context.get('survey_id', 0)]
        else:
            response_id = self.pool.get('survey.response').search(cr, uid, [('survey_id', '=', ids)], context=context)
            datas['ids'] = ids
        page_setting = {'orientation': 'vertical', 'without_pagebreak': 0, 'paper_size': 'letter', 'page_number': 1, 'survey_title': 1}
        report = {}
        if response_id and response_id[0]:
            context.update({'survey_id': datas['ids']})
            datas['form'] = page_setting
            datas['model'] = 'survey.print.answer'
            report = {
                'type': 'ir.actions.report.xml',
                'report_name': 'survey.browse.response',
                'datas': datas,
                'context': context,
                'nodestroy': True,
            }
        else:

            datas['form'] = page_setting
            datas['model'] = 'survey.print'
            report = {
                'type': 'ir.actions.report.xml',
                'report_name': 'survey.form',
                'datas': datas,
                'context': context,
                'nodestroy': True,
            }
        return report

    def print_statistics(self, cr, uid, ids, context=None):
        """
        Print Survey Statistics in pdf format.
        """
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.analysis',
            'datas': {
                'model': 'survey.print.statistics',
                'ids': [],
                'form': {
                    'id': None,
                    'survey_ids': ids
                },
            },
        }

    def _check_valid(self, cr, uid, ids, context=None):
        sur_browse = self.browse(cr, uid, ids[0], context=context)
        if not sur_browse.page_ids:
            raise osv.except_osv(_('Warning!'), _('This survey has no question defined or has no pages defined. Please define the questions and answers first.'))

    def fill_survey(self, cr, uid, ids, context=None):
        self._check_valid(cr, uid, ids, context=context)

        id = ids[0]
        survey = self.browse(cr, uid, id, context=context)
        context.update({'edit': False, 'survey_id': id, 'survey_token': survey.token, 'ir_actions_act_window_target': 'inline'})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'inline',
            'name': survey.title,
            'context': context
        }

    def edit_survey(self, cr, uid, ids, context=None):
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

    def action_survey_sent(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the survey template message loaded by default
        '''
        self._check_valid(cr, uid, ids, context=context)

        survey_browse = self.pool.get('survey').browse(cr, uid, ids, context=context)[0]
        if survey_browse.state != "open":
            raise osv.except_osv(_('Warning!'), _("You cannot send invitations because the survey is not open."))

        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'survey', 'email_template_survey')[1]
        except ValueError:
            template_id = False
        ctx = dict(context)

        ctx.update({
            'default_model': 'survey',
            'default_res_id': ids[0],
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

survey()


class survey_page(osv.osv):
    _name = 'survey.page'
    _description = 'Survey Pages'
    _rec_name = 'title'
    _order = 'sequence'
    _columns = {
        'title': fields.char('Page Title', size=128, required=1, translate=True),
        'survey_id': fields.many2one('survey', 'Survey', ondelete='cascade'),
        'question_ids': fields.one2many('survey.question', 'page_id', 'Questions'),
        'sequence': fields.integer('Page Nr'),
        'note': fields.text('Description', translate=True),
    }
    _defaults = {
        'sequence': 1
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_page, self).default_get(cr, uid, fields, context)
        if context.get('survey_id'):
            data['survey_id'] = context.get('survey_id', False)
        return data

    def survey_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        surv_name_wiz = self.pool.get('survey.name.wiz')
        surv_name_wiz.write(cr, uid, [context.get('sur_name_id', False)], {'transfer': True, 'page_no': context.get('page_number', 0)})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = _("%s (copy)") % (current_rec.get('title'))
        vals.update({'title': title})
        return super(survey_page, self).copy(cr, uid, ids, vals, context=context)

survey_page()


class survey_question(osv.osv):
    _name = 'survey.question'
    _description = 'Survey Question'
    _rec_name = 'question'
    _order = 'sequence'

    def _calc_response(self, cr, uid, ids, field_name, arg, context=None):
        if len(ids) == 0:
            return {}
        val = {}
        cr.execute("select question_id, count(id) as Total_response from \
                survey_response_line where state='done' and question_id IN %s\
                 group by question_id", (tuple(ids), ))
        ids1 = copy.deepcopy(ids)
        for rec in cr.fetchall():
            ids1.remove(rec[0])
            val[rec[0]] = int(rec[1])
        for id in ids1:
            val[id] = 0
        return val

    _columns = {
        'page_id': fields.many2one('survey.page', 'Survey Page', ondelete='cascade', required=1),
        'question': fields.char('Question', required=1, translate=True),
        'answer_choice_ids': fields.one2many('survey.answer', 'question_id', 'Answer'),
        'is_require_answer': fields.boolean('Require Answer to Question'),
        'required_type': fields.selection([('all', 'All'), ('at least', 'At Least'), ('at most', 'At Most'), ('exactly', 'Exactly'), ('a range', 'A Range')], 'Respondent must answer'),
        'req_ans': fields.integer('#Required Answer'),
        'maximum_req_ans': fields.integer('Maximum Required Answer'),
        'minimum_req_ans': fields.integer('Minimum Required Answer'),
        'req_error_msg': fields.text('Error Message', translate=True),
        'allow_comment': fields.boolean('Allow Comment Field'),
        'sequence': fields.integer('Sequence'),
        'tot_resp': fields.function(_calc_response, string="Total Answer"),
        'survey': fields.related('page_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'descriptive_text': fields.html('Descriptive Text', translate=True),
        'column_heading_ids': fields.one2many('survey.question.column.heading', 'question_id', ' Column heading'),
        'type': fields.selection([('multiple_choice_only_one_ans', 'Multiple Choice (Only One Answer)'),
                ('multiple_choice_multiple_ans', 'Multiple Choice (Multiple Answer)'),
                ('matrix_of_choices_only_one_ans', 'Matrix of Choices (Only One Answers Per Row)'),
                ('matrix_of_choices_only_multi_ans', 'Matrix of Choices (Multiple Answers Per Row)'),
                ('rating_scale', 'Rating Scale'),
                ('single_textbox', 'Single Textbox'),
                ('multiple_textboxes', 'Multiple Textboxes'),
                ('multiple_textboxes_diff_type', 'Multiple Textboxes With Different Type'),
                ('comment', 'Comment/Essay Box'),
                ('numerical_textboxes', 'Numerical Textboxes'),
                ('date', 'Date'),
                ('date_and_time', 'Date and Time'),
                ('descriptive_text', 'Descriptive Text'),
                ('table', 'Table'),
            ], 'Question Type', required=1, ),
        'is_comment_require': fields.boolean('Add Comment Field'),
        'comment_label': fields.char('Field Label', translate=True),
        'comment_field_type': fields.selection([('char', 'Single Line Of Text'), ('text', 'Paragraph of Text')], 'Comment Field Type'),
        'comment_valid_type': fields.selection([('do_not_validate', '''Don't Validate Comment Text.'''),
             ('must_be_specific_length', 'Must Be Specific Length'),
             ('must_be_whole_number', 'Must Be A Whole Number'),
             ('must_be_decimal_number', 'Must Be A Decimal Number'),
             ('must_be_date', 'Must Be A Date'),
             ('must_be_email_address', 'Must Be An Email Address'),
             ], 'Text Validation'),
        'comment_minimum_no': fields.integer('Minimum number'),
        'comment_maximum_no': fields.integer('Maximum number'),
        'comment_minimum_float': fields.float('Minimum decimal number'),
        'comment_maximum_float': fields.float('Maximum decimal number'),
        'comment_minimum_date': fields.date('Minimum date'),
        'comment_maximum_date': fields.date('Maximum date'),
        'comment_valid_err_msg': fields.text('Error message', translate=True),
        'make_comment_field': fields.boolean('Make Comment Field an Answer Choice'),
        'make_comment_field_err_msg': fields.text('Error message', translate=True),
        'is_validation_require': fields.boolean('Validate Text'),
        'validation_type': fields.selection([('do_not_validate', '''Don't Validate Comment Text.'''), \
             ('must_be_specific_length', 'Must Be Specific Length'), \
             ('must_be_whole_number', 'Must Be A Whole Number'), \
             ('must_be_decimal_number', 'Must Be A Decimal Number'), \
             ('must_be_date', 'Must Be A Date'), \
             ('must_be_email_address', 'Must Be An Email Address')\
             ], 'Text Validation'),
        'validation_minimum_no': fields.integer('Minimum number'),
        'validation_maximum_no': fields.integer('Maximum number'),
        'validation_minimum_float': fields.float('Minimum decimal number'),
        'validation_maximum_float': fields.float('Maximum decimal number'),
        'validation_minimum_date': fields.date('Minimum date'),
        'validation_maximum_date': fields.date('Maximum date'),
        'validation_valid_err_msg': fields.text('Error message', translate=True),
        'numeric_required_sum': fields.integer('Sum of all choices'),
        'numeric_required_sum_err_msg': fields.text('Error message', translate=True),
        'rating_allow_one_column_require': fields.boolean('Allow Only One Answer per Column (Forced Ranking)'),
        'in_visible_rating_weight': fields.boolean('Is Rating Scale Invisible?'),
        'in_visible_menu_choice': fields.boolean('Is Menu Choice Invisible?'),
        'in_visible_answer_type': fields.boolean('Is Answer Type Invisible?'),
        'comment_column': fields.boolean('Add comment column in matrix'),
        'column_name': fields.char('Column Name', translate=True),
        'no_of_rows': fields.integer('No of Rows'),
    }
    _defaults = {
        'sequence': 1,
        'type': lambda s, cr, uid, c: _('multiple_choice_multiple_ans'),
        'req_error_msg': lambda s, cr, uid, c: _('This question requires an answer.'),
        'required_type': 'at least',
        'req_ans': 1,
        'comment_field_type': 'char',
        'comment_label': lambda s, cr, uid, c: _('Other (please specify)'),
        'comment_valid_type': 'do_not_validate',
        'comment_valid_err_msg': lambda s, cr, uid, c: _('The comment you entered is in an invalid format.'),
        'validation_type': 'do_not_validate',
        'validation_valid_err_msg': lambda s, cr, uid, c: _('The comment you entered is in an invalid format.'),
        'numeric_required_sum_err_msg': lambda s, cr, uid, c: _('The choices need to add up to [enter sum here].'),
        'make_comment_field_err_msg': lambda s, cr, uid, c: _('Please enter a comment.'),
        'in_visible_answer_type': 1
    }

    def on_change_type(self, cr, uid, ids, type, context=None):
        val = {}
        val['is_require_answer'] = False
        val['is_comment_require'] = False
        val['is_validation_require'] = False
        val['comment_column'] = False

        if type in ['multiple_textboxes_diff_type']:
            val['in_visible_answer_type'] = False
            return {'value': val}

        if type in ['rating_scale']:
            val.update({'in_visible_rating_weight': False, 'in_visible_menu_choice': True})
            return {'value': val}

        elif type in ['single_textbox']:
            val.update({'in_visible_rating_weight': True, 'in_visible_menu_choice': True})
            return {'value': val}

        else:
            val.update({'in_visible_rating_weight': True, 'in_visible_menu_choice': True, \
                         'in_visible_answer_type': True})
            return {'value': val}

    def write(self, cr, uid, ids, vals, context=None):
        questions = self.read(cr, uid, ids, ['answer_choice_ids', 'type', 'required_type', \
                        'req_ans', 'minimum_req_ans', 'maximum_req_ans', 'column_heading_ids', 'page_id', 'question'])
        for question in questions:
            col_len = len(question['column_heading_ids'])
            for col in vals.get('column_heading_ids', []):
                if type(col[2]) == type({}):
                    col_len += 1
                else:
                    col_len -= 1

            que_type = vals.get('type', question['type'])

            if que_type in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale']:
                if not col_len:
                    raise osv.except_osv(_('Warning!'), _('You must enter one or more column headings for question "%s" of page %s.') % (question['question'], question['page_id'][1]))
            ans_len = len(question['answer_choice_ids'])

            for ans in vals.get('answer_choice_ids', []):
                if type(ans[2]) == type({}):
                    ans_len += 1
                else:
                    ans_len -= 1

            if que_type not in ['descriptive_text', 'single_textbox', 'comment', 'table']:
                if not ans_len:
                    raise osv.except_osv(_('Warning!'), _('You must enter one or more Answers for question "%s" of page %s.') % (question['question'], question['page_id'][1]))

            req_type = vals.get('required_type', question['required_type'])

            if que_type in ['multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', \
                        'matrix_of_choices_only_multi_ans', 'rating_scale', 'multiple_textboxes', \
                        'numerical_textboxes', 'date', 'date_and_time']:
                if req_type in ['at least', 'at most', 'exactly']:
                    if 'req_ans' in vals:
                        if not vals['req_ans'] or vals['req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning!'), _("#Required Answer you entered \
                                    is greater than the number of answer. \
                                    Please use a number that is smaller than %d.") % (ans_len + 1))
                    else:
                        if not question['req_ans'] or question['req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning!'), _("#Required Answer you entered is \
                                    greater than the number of answer.\
                                    Please use a number that is smaller than %d.") % (ans_len + 1))

                if req_type == 'a range':
                    minimum_ans = 0
                    maximum_ans = 0
                    minimum_ans = 'minimum_req_ans' in vals and vals['minimum_req_ans'] or question['minimum_req_ans']
                    maximum_ans = 'maximum_req_ans' in vals and vals['maximum_req_ans'] or question['maximum_req_ans']

                    if not minimum_ans or minimum_ans > ans_len or not maximum_ans or maximum_ans > ans_len:
                        raise osv.except_osv(_('Warning!'), _("Minimum Required Answer you\
                                 entered is greater than the number of answer. \
                                 Please use a number that is smaller than %d.") % (ans_len + 1))
                    if maximum_ans <= minimum_ans:
                        raise osv.except_osv(_('Warning!'), _("Maximum Required Answer is greater \
                                    than Minimum Required Answer"))

        return super(survey_question, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        page = self.pool.get('survey.page').browse(cr, uid, 'page_id' in vals and vals['page_id'] or context['page_id'], context=context).title
        if 'answer_choice_ids' in vals and not len(vals.get('answer_choice_ids', [])) and \
            vals.get('type') not in ['descriptive_text', 'single_textbox', 'comment', 'table']:
            raise osv.except_osv(_('Warning!'), _('You must enter one or more answers for question "%s" of page %s .') % (vals['question'], page))

        if 'column_heading_ids' in vals and not len(vals.get('column_heading_ids', [])) and \
            vals.get('type') in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale']:
            raise osv.except_osv(_('Warning!'), _('You must enter one or more column headings for question "%s" of page %s.') % (vals['question'], page))

        if 'is_require_answer' in vals and vals.get('type') in ['multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', \
            'matrix_of_choices_only_multi_ans', 'rating_scale', 'multiple_textboxes', 'numerical_textboxes', 'date', 'date_and_time']:
            if vals.get('required_type') in ['at least', 'at most', 'exactly']:
                if 'answer_choice_ids' in vals and 'answer_choice_ids' in vals and vals.get('req_ans') > len(vals.get('answer_choice_ids', [])):
                    raise osv.except_osv(_('Warning!'), _("#Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
            if vals.get('required_type') == 'a range':
                if 'answer_choice_ids' in vals:
                    if not vals.get('minimum_req_ans') or vals['minimum_req_ans'] > len(vals['answer_choice_ids']):
                        raise osv.except_osv(_('Warning!'), _("Minimum Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
                    if not vals.get('maximum_req_ans') or vals['maximum_req_ans'] > len(vals['answer_choice_ids']):
                        raise osv.except_osv(_('Warning!'), _("Maximum Required Answer you entered for your maximum is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids']) + 1))
                if vals.get('maximum_req_ans', 0) <= vals.get('minimum_req_ans', 0):
                    raise osv.except_osv(_('Warning!'), _("Maximum Required Answer is greater than Minimum Required Answer."))

        return super(survey_question, self).create(cr, uid, vals, context)

    def survey_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        surv_name_wiz = self.pool.get('survey.name.wiz')
        surv_name_wiz.write(cr, uid, [context.get('sur_name_id', False)], {'transfer': True, 'page_no': context.get('page_number', False)})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_question, self).default_get(cr, uid, fields, context)
        if context.get('page_id'):
            data['page_id'] = context.get('page_id', False)
        return data

survey_question()


class survey_question_column_heading(osv.osv):
    _name = 'survey.question.column.heading'
    _description = 'Survey Question Column Heading'
    _rec_name = 'title'

    def _get_in_visible_rating_weight(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('in_visible_rating_weight', False):
            return context['in_visible_rating_weight']
        return False

    def _get_in_visible_menu_choice(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('in_visible_menu_choice', False):
            return context['in_visible_menu_choice']
        return False

    _columns = {
        'title': fields.char('Column Heading', size=128, required=1, translate=True),
        'menu_choice': fields.text('Menu Choice'),
        'rating_weight': fields.integer('Weight'),
        'question_id': fields.many2one('survey.question', 'Question', ondelete='cascade'),
        'in_visible_rating_weight': fields.boolean('Is Rating Scale Invisible ??'),
        'in_visible_menu_choice': fields.boolean('Is Menu Choice Invisible??')
    }
    _defaults = {
       'in_visible_rating_weight': _get_in_visible_rating_weight,
       'in_visible_menu_choice': _get_in_visible_menu_choice,
    }
survey_question_column_heading()


class survey_answer(osv.osv):
    _name = 'survey.answer'
    _description = 'Survey Answer'
    _rec_name = 'answer'
    _order = 'sequence'

    def _calc_response_avg(self, cr, uid, ids, field_name, arg, context=None):
        val = {}
        for rec in self.browse(cr, uid, ids, context=context):
            cr.execute("select count(question_id), (select count(answer_id) \
                from survey_response_answer sra, survey_response_line sa \
                where sra.response_id = sa.id and sra.answer_id = %d \
                and sa.state='done') as tot_ans from survey_response_line \
                where question_id = %d and state = 'done'"\
                     % (rec.id, rec.question_id.id))
            res = cr.fetchone()
            if res[0]:
                avg = float(res[1]) * 100 / res[0]
            else:
                avg = 0.0
            val[rec.id] = {
                'response': res[1],
                'average': round(avg, 2),
            }
        return val

    def _get_in_visible_answer_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('in_visible_answer_type', False)

    _columns = {
        'question_id': fields.many2one('survey.question', 'Question', ondelete='cascade'),
        'answer': fields.char('Answer', size=128, required=1, translate=True),
        'sequence': fields.integer('Sequence'),
        'response': fields.function(_calc_response_avg, string="#Answer", multi='sums'),
        'average': fields.function(_calc_response_avg, string="#Avg", multi='sums'),
        'type': fields.selection([('char', 'Character'), ('date', 'Date'), ('datetime', 'Date & Time'), \
            ('integer', 'Integer'), ('float', 'Float'), ('selection', 'Selection'), \
            ('email', 'Email')], "Type of Answer", required=1),
        'menu_choice': fields.text('Menu Choices', translate=True),
        'in_visible_answer_type': fields.boolean('Is Answer Type Invisible??')
    }
    _defaults = {
        'type': 'char',
        'in_visible_answer_type': _get_in_visible_answer_type,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_answer, self).default_get(cr, uid, fields, context)
        return data

survey_answer()


class survey_response(osv.osv):
    _name = "survey.response"
    _rec_name = 'date_create'

    _columns = {
        'date_deadline': fields.date("Deadline date", help="Date by which the person can respond to the survey"),
        'survey_id': fields.many2one('survey', 'Survey', required=1, readonly=1, ondelete='restrict'),
        'date_create': fields.datetime('Create Date', required=1),
        'response_type': fields.selection([('manually', 'Manually'), ('link', 'Link')], 'Answer Type', required=1),
        'question_ids': fields.one2many('survey.response.line', 'response_id', 'Answer'),
        'state': fields.selection([('new', 'Not Started'), ('skip', 'Not Finished'), ('done', 'Finished'), ('cancel', 'Canceled')], 'Status', readonly=True),
        'token': fields.char("Indentification token", readonly=1),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=1),
        'email': fields.char("Email", size=64, readonly=1),
    }
    _defaults = {
        'date_create': datetime.now(),
        'state': "new",
        'response_type': "manually",
        'token': lambda s, cr, uid, c: uuid.uuid4(),
    }

    def action_survey_resent(self, cr, uid, ids, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        context = context or {}
        context.update({
            'survey_resent_token': True,
            'default_partner_ids': record.partner_id and [record.partner_id.id] or [],
            'default_multi_email': record.email or "",
            'default_public': 'email',
        })
        return self.pool.get('survey').action_survey_sent(cr, uid, [record.survey_id.id], context=context)

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
        self.pool.get('survey').check_access_rights(cr, uid, 'write')

        record = self.browse(cr, uid, ids[0], context=context)
        context.update({
            'ir_actions_act_window_target': 'new',
            'survey_id': record.survey_id.id,
            'response_id': ids,
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

    def action_cancel(self, cr, uid, ids, context=None):
        self.pool.get('survey').check_access_rights(cr, uid, 'write')
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['partner_id', 'date_create'], context=context)
        res = []
        for record in reads:
            name = (record['partner_id'] and record['partner_id'][1] or '') + ' (' + record['date_create'].split('.')[0] + ')'
            res.append((record['id'], name))
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning!'), _('You cannot duplicate the resource!'))

survey_response()


class survey_response_line(osv.osv):
    _name = 'survey.response.line'
    _description = 'Survey Response Line'
    _rec_name = 'date_create'
    _columns = {
        'response_id': fields.many2one('survey.response', 'Answer', ondelete='cascade'),
        'date_create': fields.datetime('Create Date', required=1),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Answered'), ('skip', 'Skiped')], \
                                   'Status', readonly=True),
        'question_id': fields.many2one('survey.question', 'Question'),
        'page_id': fields.related('question_id', 'page_id', type='many2one', \
                                  relation='survey.page', string='Page'),
        'response_answer_ids': fields.one2many('survey.response.answer', 'response_id', 'Answer'),
        'response_table_ids': fields.one2many('survey.tbl.column.heading', \
                                    'response_table_id', 'Answer'),
        'comment': fields.text('Notes'),
        'single_text': fields.char('Text', size=255),
    }
    _defaults = {
        'state': "draft",
    }

survey_response_line()


class survey_tbl_column_heading(osv.osv):
    _name = 'survey.tbl.column.heading'
    _order = 'name'
    _columns = {
        'name': fields.integer('Row Number'),
        'column_id': fields.many2one('survey.question.column.heading', 'Column'),
        'value': fields.char('Value', size=255),
        'response_table_id': fields.many2one('survey.response.line', 'Answer', ondelete='cascade'),
    }

survey_tbl_column_heading()


class survey_response_answer(osv.osv):
    _name = 'survey.response.answer'
    _description = 'Survey Answer'
    _rec_name = 'response_id'
    _columns = {
        'response_id': fields.many2one('survey.response.line', 'Answer', ondelete='cascade'),
        'answer_id': fields.many2one('survey.answer', 'Answer', required=1, ondelete='cascade'),
        'column_id': fields.many2one('survey.question.column.heading', 'Column'),
        'answer': fields.char('Value', size=255),
        'value_choice': fields.char('Value Choice', size=255),
        'comment': fields.text('Notes'),
        'comment_field': fields.char('Comment', size=255)
    }

survey_response_answer()


# vim: exp and tab: smartindent: tabstop=4: softtabstop=4: shiftwidth=4:
