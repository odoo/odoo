# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
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

from osv import osv
from osv import fields
import tools
import netsvc
from tools.translate import _

from time import strftime
from datetime import datetime
from dateutil.relativedelta import relativedelta
import copy
import os

class survey_type(osv.osv):
    _name = 'survey.type'
    _description = 'Survey Type'
    _columns = {
        'name': fields.char("Name", size=128, required=1),
        'code': fields.char("Code", size=64),
    }
survey_type()

class survey(osv.osv):
    _name = 'survey'
    _description = 'Survey'
    _rec_name = 'title'

    def default_get(self, cr, uid, fields, context=None):
        data = super(survey, self).default_get(cr, uid, fields, context)
        return data

    _columns = {
        'title': fields.char('Survey Title', size=128, required=1),
        'page_ids': fields.one2many('survey.page', 'survey_id', 'Page'),
        'date_open': fields.datetime('Survey Open Date', readonly=1),
        'date_close': fields.datetime('Survey Close Date', readonly=1),
        'max_response_limit': fields.integer('Maximum Answer Limit',
                     help="Set to one if survey is answerable only once"),
        'response_user': fields.integer('Maximum Answer per User',
                     help="Set to one if  you require only one Answer per user"),
        'state': fields.selection([('draft', 'Draft'), ('open', 'Open'), ('close', 'Closed'), ('cancel', 'Cancelled')], 'Status', readonly=True),
        'responsible_id': fields.many2one('res.users', 'Responsible', help="User responsible for survey"),
        'tot_start_survey': fields.integer("Total Started Survey", readonly=1),
        'tot_comp_survey': fields.integer("Total Completed Survey", readonly=1),
        'note': fields.text('Description', size=128),
        'history': fields.one2many('survey.history', 'survey_id', 'History Lines', readonly=True),
        'users': fields.many2many('res.users', 'survey_users_rel', 'sid', 'uid', 'Users'),
        'send_response': fields.boolean('E-mail Notification on Answer'),
        'type': fields.many2one('survey.type', 'Type'),
        'invited_user_ids': fields.many2many('res.users', 'survey_invited_user_rel', 'sid', 'uid', 'Invited User'),
    }
    _defaults = {
        'state': lambda * a: "draft",
        'tot_start_survey': lambda * a: 0,
        'tot_comp_survey': lambda * a: 0,
        'send_response': lambda * a: 1,
        'response_user': lambda * a:1,
    }

    def survey_draft(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, {'state': 'draft'})
        return True

    def survey_open(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, {'state': 'open', 'date_open': strftime("%Y-%m-%d %H:%M:%S")})
        return True

    def survey_close(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, {'state': 'close', 'date_close': strftime("%Y-%m-%d %H:%M:%S") })
        return True

    def survey_cancel(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, {'state': 'cancel' })
        return True

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = current_rec.get('title') + ' (Copy)'
        vals.update({'title':title})
        vals.update({'history':[],'tot_start_survey':0,'tot_comp_survey':0})
        return super(survey, self).copy(cr, uid, ids, vals, context=context)

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return : Dictionary value for print survey form.
        """
        if context is None:
            context = {}
        datas = {}
        if 'response_id' in context:
            response_id = context.get('response_id', 0)
            datas['ids'] = [context.get('survey_id', 0)]
        else:
            response_id = self.pool.get('survey.response').search(cr, uid, [('survey_id','=', ids)], context=context)
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
                'context' : context,
                'nodestroy':True,
            }
        else:

            datas['form'] = page_setting
            datas['model'] = 'survey.print'
            report = {
                'type': 'ir.actions.report.xml',
                'report_name': 'survey.form',
                'datas': datas,
                'context' : context,
                'nodestroy':True,
            }
        return report
survey()

class survey_history(osv.osv):
    _name = 'survey.history'
    _description = 'Survey History'
    _rec_name = 'date'
    _columns = {
        'survey_id': fields.many2one('survey', 'Survey'),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'date': fields.datetime('Date started', readonly=1),
    }
    _defaults = {
         'date': lambda * a: datetime.datetime.now()
    }
survey_history()

class survey_page(osv.osv):
    _name = 'survey.page'
    _description = 'Survey Pages'
    _rec_name = 'title'
    _order = 'sequence'
    _columns = {
        'title': fields.char('Page Title', size=128, required=1),
        'survey_id': fields.many2one('survey', 'Survey', ondelete='cascade'),
        'question_ids': fields.one2many('survey.question', 'page_id', 'Question'),
        'sequence': fields.integer('Page Nr'),
        'note': fields.text('Description'),
    }
    _defaults = {
        'sequence': lambda * a: 1
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_page, self).default_get(cr, uid, fields, context)
        self.pool.get('survey.question').data_get(cr,uid,data,context)
        if context.has_key('survey_id'):
            data['survey_id'] = context.get('survey_id', False)
        return data

    def survey_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        search_obj = self.pool.get('ir.ui.view')
        search_id = search_obj.search(cr,uid,[('model','=','survey.question.wiz'),('name','=','Survey Search')])
        surv_name_wiz = self.pool.get('survey.name.wiz')
        surv_name_wiz.write(cr, uid, [context.get('sur_name_id',False)], {'transfer':True, 'page_no' : context.get('page_number',0) })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'search_view_id': search_id[0],
            'context': context
        }

    def copy(self, cr, uid, ids, default=None, context=None):
        vals = {}
        current_rec = self.read(cr, uid, ids, context=context)
        title = current_rec.get('title') + ' (Copy)'
        vals.update({'title':title})
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
                 group by question_id" ,(tuple(ids),))
        ids1 = copy.deepcopy(ids)
        for rec in  cr.fetchall():
            ids1.remove(rec[0])
            val[rec[0]] = int(rec[1])
        for id in ids1:
            val[id] = 0
        return val

    _columns = {
        'page_id': fields.many2one('survey.page', 'Survey Page', ondelete='cascade', required=1),
        'question':  fields.char('Question', size=128, required=1),
        'answer_choice_ids': fields.one2many('survey.answer', 'question_id', 'Answer'),
        'is_require_answer': fields.boolean('Require Answer to Question'),
        'required_type': fields.selection([('all','All'), ('at least','At Least'), ('at most','At Most'), ('exactly','Exactly'), ('a range','A Range')], 'Respondent must answer'),
        'req_ans': fields.integer('#Required Answer'),
        'maximum_req_ans': fields.integer('Maximum Required Answer'),
        'minimum_req_ans': fields.integer('Minimum Required Answer'),
        'req_error_msg': fields.text('Error Message'),
        'allow_comment': fields.boolean('Allow Comment Field'),
        'sequence': fields.integer('Sequence'),
        'tot_resp': fields.function(_calc_response, string="Total Answer"),
        'survey': fields.related('page_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'descriptive_text': fields.text('Descriptive Text', size=255),
        'column_heading_ids': fields.one2many('survey.question.column.heading', 'question_id',' Column heading'),
        'type': fields.selection([('multiple_choice_only_one_ans','Multiple Choice (Only One Answer)'),
             ('multiple_choice_multiple_ans','Multiple Choice (Multiple Answer)'),
             ('matrix_of_choices_only_one_ans','Matrix of Choices (Only One Answers Per Row)'),
             ('matrix_of_choices_only_multi_ans','Matrix of Choices (Multiple Answers Per Row)'),
             ('matrix_of_drop_down_menus','Matrix of Drop-down Menus'),
             ('rating_scale','Rating Scale'),('single_textbox','Single Textbox'),
             ('multiple_textboxes','Multiple Textboxes'),
             ('multiple_textboxes_diff_type','Multiple Textboxes With Different Type'),
             ('comment','Comment/Essay Box'),
             ('numerical_textboxes','Numerical Textboxes'),('date','Date'),
             ('date_and_time','Date and Time'),('descriptive_text','Descriptive Text'),
             ('table','Table'),
            ], 'Question Type',  required=1,),
        'is_comment_require': fields.boolean('Add Comment Field'),
        'comment_label': fields.char('Field Label', size = 255),
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
        'comment_valid_err_msg': fields.text('Error message'),
        'make_comment_field': fields.boolean('Make Comment Field an Answer Choice'),
        'make_comment_field_err_msg': fields.text('Error message'),
        'is_validation_require': fields.boolean('Validate Text'),
        'validation_type': fields.selection([('do_not_validate', '''Don't Validate Comment Text.'''),\
             ('must_be_specific_length', 'Must Be Specific Length'),\
             ('must_be_whole_number', 'Must Be A Whole Number'),\
             ('must_be_decimal_number', 'Must Be A Decimal Number'),\
             ('must_be_date', 'Must Be A Date'),\
             ('must_be_email_address', 'Must Be An Email Address')\
             ], 'Text Validation'),
        'validation_minimum_no': fields.integer('Minimum number'),
        'validation_maximum_no': fields.integer('Maximum number'),
        'validation_minimum_float': fields.float('Minimum decimal number'),
        'validation_maximum_float': fields.float('Maximum decimal number'),
        'validation_minimum_date': fields.date('Minimum date'),
        'validation_maximum_date': fields.date('Maximum date'),
        'validation_valid_err_msg': fields.text('Error message'),
        'numeric_required_sum': fields.integer('Sum of all choices'),
        'numeric_required_sum_err_msg': fields.text('Error message'),
        'rating_allow_one_column_require': fields.boolean('Allow Only One Answer per Column (Forced Ranking)'),
        'in_visible_rating_weight': fields.boolean('Is Rating Scale Invisible?'),
        'in_visible_menu_choice': fields.boolean('Is Menu Choice Invisible?'),
        'in_visible_answer_type': fields.boolean('Is Answer Type Invisible?'),
        'comment_column': fields.boolean('Add comment column in matrix'),
        'column_name': fields.char('Column Name',size=256),
        'no_of_rows': fields.integer('No of Rows'),
    }
    _defaults = {
         'sequence': lambda * a: 1,
         'type': lambda * a: 'multiple_choice_multiple_ans',
         'req_error_msg': lambda * a: 'This question requires an answer.',
         'required_type': lambda * a: 'at least',
         'req_ans': lambda * a: 1,
         'comment_field_type': lambda * a: 'char',
         'comment_label': lambda * a: 'Other (please specify)',
         'comment_valid_type': lambda * a: 'do_not_validate',
         'comment_valid_err_msg': lambda * a : 'The comment you entered is in an invalid format.',
         'validation_type': lambda * a: 'do_not_validate',
         'validation_valid_err_msg': lambda * a : 'The comment you entered is in an invalid format.',
         'numeric_required_sum_err_msg': lambda * a :'The choices need to add up to [enter sum here].',
         'make_comment_field_err_msg': lambda * a : 'Please enter a comment.',
         'in_visible_answer_type': lambda * a: 1
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
            val.update({'in_visible_rating_weight':False, 'in_visible_menu_choice':True})
            return {'value': val}

        elif type in ['matrix_of_drop_down_menus']:
            val.update({'in_visible_rating_weight':True, 'in_visible_menu_choice':False})
            return {'value': val}

        elif type in ['single_textbox']:
            val.update({'in_visible_rating_weight':True, 'in_visible_menu_choice':True})
            return {'value': val}

        else:
            val.update({'in_visible_rating_weight':True, 'in_visible_menu_choice':True,\
                         'in_visible_answer_type':True})
            return {'value': val}

    def write(self, cr, uid, ids, vals, context=None):
        questions = self.read(cr,uid, ids, ['answer_choice_ids', 'type', 'required_type',\
                        'req_ans', 'minimum_req_ans', 'maximum_req_ans', 'column_heading_ids'])
        for question in questions:
            col_len = len(question['column_heading_ids'])
            if vals.has_key('column_heading_ids'):
                for col in vals['column_heading_ids']:
                    if type(col[2]) == type({}):
                        col_len += 1
                    else:
                        col_len -= 1

            if vals.has_key('type'):
                que_type = vals['type']
            else:
                que_type = question['type']

            if que_type in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans',\
                             'matrix_of_drop_down_menus', 'rating_scale']:
                if not col_len:
                    raise osv.except_osv(_('Warning !'),_("You must enter one or more column heading."))
            ans_len = len(question['answer_choice_ids'])

            if vals.has_key('answer_choice_ids'):
                for ans in vals['answer_choice_ids']:
                    if type(ans[2]) == type({}):
                        ans_len += 1
                    else:
                        ans_len -= 1

            if que_type not in ['descriptive_text', 'single_textbox', 'comment','table']:
                if not ans_len:
                    raise osv.except_osv(_('Warning !'),_("You must enter one or more Answer."))
            req_type = ""

            if vals.has_key('required_type'):
                req_type = vals['required_type']
            else:
                req_type = question['required_type']

            if que_type in ['multiple_choice_multiple_ans','matrix_of_choices_only_one_ans', \
                        'matrix_of_choices_only_multi_ans', 'matrix_of_drop_down_menus',\
                         'rating_scale','multiple_textboxes','numerical_textboxes','date','date_and_time']:
                if req_type in ['at least', 'at most', 'exactly']:
                    if vals.has_key('req_ans'):
                        if not vals['req_ans'] or  vals['req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("#Required Answer you entered \
                                    is greater than the number of answer. \
                                    Please use a number that is smaller than %d.") % (ans_len + 1))
                    else:
                        if not question['req_ans'] or  question['req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("#Required Answer you entered is \
                                    greater than the number of answer.\
                                    Please use a number that is smaller than %d.") % (ans_len + 1))

                if req_type == 'a range':
                    minimum_ans = 0
                    maximum_ans = 0
                    if vals.has_key('minimum_req_ans'):
                        minimum_ans = vals['minimum_req_ans']
                        if not vals['minimum_req_ans'] or  vals['minimum_req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("Minimum Required Answer\
                                     you entered is greater than the number of answer.\
                                    Please use a number that is smaller than %d.") % (ans_len + 1))
                    else:
                        minimum_ans = question['minimum_req_ans']
                        if not question['minimum_req_ans'] or  question['minimum_req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("Minimum Required Answer you\
                                     entered is greater than the number of answer. \
                                     Please use a number that is smaller than %d.") % (ans_len + 1))
                    if vals.has_key('maximum_req_ans'):
                        maximum_ans = vals['maximum_req_ans']
                        if not vals['maximum_req_ans'] or vals['maximum_req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("Maximum Required Answer you \
                                    entered for your maximum is greater than the number of answer.\
                                     Please use a number that is smaller than %d.") % (ans_len + 1))
                    else:
                        maximum_ans = question['maximum_req_ans']
                        if not question['maximum_req_ans'] or question['maximum_req_ans'] > ans_len:
                            raise osv.except_osv(_('Warning !'),_("Maximum Required Answer you\
                                     entered for your maximum is greater than the number of answer.\
                                      Please use a number that is smaller than %d.") % (ans_len + 1))
                    if maximum_ans <= minimum_ans:
                        raise osv.except_osv(_('Warning !'),_("Maximum Required Answer is greater \
                                    than Minimum Required Answer"))

            if question['type'] ==  'matrix_of_drop_down_menus' and vals.has_key('column_heading_ids'):
                for col in vals['column_heading_ids']:
                    if not col[2] or not col[2].has_key('menu_choice') or not col[2]['menu_choice']:
                        raise osv.except_osv(_('Warning !'),_("You must enter one or more menu choices\
                                 in column heading"))
                    elif not col[2] or not col[2].has_key('menu_choice') or\
                             col[2]['menu_choice'].strip() == '':
                        raise osv.except_osv(_('Warning !'),_("You must enter one or more menu \
                                choices in column heading (white spaces not allowed)"))

        return super(survey_question, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        minimum_ans = 0
        maximum_ans = 0
        if vals.has_key('answer_choice_ids') and  not len(vals['answer_choice_ids']):
            if vals.has_key('type') and vals['type'] not in ['descriptive_text', 'single_textbox', 'comment','table']:
                raise osv.except_osv(_('Warning !'),_("You must enter one or more answer."))

        if vals.has_key('column_heading_ids') and  not len(vals['column_heading_ids']):
            if vals.has_key('type') and vals['type'] in ['matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'matrix_of_drop_down_menus', 'rating_scale']:
                raise osv.except_osv(_('Warning !'),_("You must enter one or more column heading."))

        if vals['type'] in ['multiple_choice_multiple_ans','matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'matrix_of_drop_down_menus', 'rating_scale','multiple_textboxes','numerical_textboxes','date','date_and_time']:
            if vals.has_key('is_require_answer') and vals.has_key('required_type') and vals['required_type'] in ['at least', 'at most', 'exactly']:
                if vals.has_key('answer_choice_ids') and vals['req_ans'] > len(vals['answer_choice_ids']) or not vals['req_ans']:
                    raise osv.except_osv(_('Warning !'),_("#Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids'])+1))

            if vals.has_key('is_require_answer') and vals.has_key('required_type') and vals['required_type'] == 'a range':
                minimum_ans = vals['minimum_req_ans']
                maximum_ans = vals['maximum_req_ans']
                if vals.has_key('answer_choice_ids') or vals['minimum_req_ans'] > len(vals['answer_choice_ids']) or not vals['minimum_req_ans']:
                    raise osv.except_osv(_('Warning !'),_("Minimum Required Answer you entered is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids'])+1))
                if vals.has_key('answer_choice_ids') or vals['maximum_req_ans'] > len(vals['answer_choice_ids']) or not vals['maximum_req_ans']:
                    raise osv.except_osv(_('Warning !'),_("Maximum Required Answer you entered for your maximum is greater than the number of answer. Please use a number that is smaller than %d.") % (len(vals['answer_choice_ids'])+1))
                if maximum_ans <= minimum_ans:
                    raise osv.except_osv(_('Warning !'),_("Maximum Required Answer is greater than Minimum Required Answer"))

        if vals['type'] ==  'matrix_of_drop_down_menus':
            for col in vals['column_heading_ids']:
                if not col[2] or not col[2].has_key('menu_choice') or not col[2]['menu_choice']:
                    raise osv.except_osv(_('Warning !'),_("You must enter one or more menu choices in column heading"))
                elif not col[2] or not col[2].has_key('menu_choice') or col[2]['menu_choice'].strip() == '':
                    raise osv.except_osv(_('Warning !'),_("You must enter one or more menu choices in column heading (white spaces not allowed)"))

        res = super(survey_question, self).create(cr, uid, vals, context)
        return res

    def survey_save(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        search_obj = self.pool.get('ir.ui.view')
        search_id = search_obj.search(cr,uid,[('model','=','survey.question.wiz'),('name','=','Survey Search')])
        surv_name_wiz = self.pool.get('survey.name.wiz')
        surv_name_wiz.write(cr, uid, [context.get('sur_name_id',False)], {'transfer':True, 'page_no' : context.get('page_number',False) })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'search_view_id': search_id[0],
            'context': context
        }

    def data_get(self, cr, uid, data, context):
        if data and context:
            if context.get('line_order',False) and data.get('sequence',0):
                lines =  context.get('line_order')
                seq = data['sequence']
                for line in  lines:
                    seq = seq + 1
                data.update({'sequence': str(seq)})
        return data

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_question, self).default_get(cr, uid, fields, context)
        self.data_get(cr,uid,data,context)
        if context.has_key('page_id'):
            data['page_id']= context.get('page_id', False)
        return data

survey_question()


class survey_question_column_heading(osv.osv):
    _name = 'survey.question.column.heading'
    _description = 'Survey Question Column Heading'
    _rec_name = 'title'

    def _get_in_visible_rating_weight(self,cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('in_visible_rating_weight', False):
            return context['in_visible_rating_weight']
        return False
    def _get_in_visible_menu_choice(self,cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('in_visible_menu_choice', False):
            return context['in_visible_menu_choice']
        return False

    _columns = {
        'title': fields.char('Column Heading', size=128, required=1),
        'menu_choice': fields.text('Menu Choice'),
        'rating_weight': fields.integer('Weight'),
        'question_id': fields.many2one('survey.question', 'Question', ondelete='cascade'),
        'in_visible_rating_weight': fields.boolean('Is Rating Scale Invisible ??'),
        'in_visible_menu_choice': fields.boolean('Is Menu Choice Invisible??')
    }
    _defaults={
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
            cr.execute("select count(question_id) ,(select count(answer_id) \
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

    def _get_in_visible_answer_type(self,cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('in_visible_answer_type', False)

    _columns = {
        'question_id': fields.many2one('survey.question', 'Question', ondelete='cascade'),
        'answer': fields.char('Answer', size=128, required=1),
        'sequence': fields.integer('Sequence'),
        'response': fields.function(_calc_response_avg, string="#Answer", multi='sums'),
        'average': fields.function(_calc_response_avg, string="#Avg", multi='sums'),
        'type': fields.selection([('char','Character'),('date','Date'),('datetime','Date & Time'),\
            ('integer','Integer'),('float','Float'),('selection','Selection'),\
            ('email','Email')], "Type of Answer",required=1),
        'menu_choice': fields.text('Menu Choices'),
        'in_visible_answer_type': fields.boolean('Is Answer Type Invisible??')
    }
    _defaults = {
#         'sequence' : lambda * a: 1,
         'type' : lambda * a: 'char',
         'in_visible_answer_type':_get_in_visible_answer_type,
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        data = super(survey_answer, self).default_get(cr, uid, fields, context)
        self.pool.get('survey.question').data_get(cr,uid,data,context)
        return data

survey_answer()

class survey_response(osv.osv):
    _name = "survey.response"
    _rec_name = 'date_create'
    _columns = {
        'survey_id' : fields.many2one('survey', 'Survey', required=1, ondelete='cascade'),
        'date_create' : fields.datetime('Create Date', required=1),
        'user_id' : fields.many2one('res.users', 'User'),
        'response_type' : fields.selection([('manually', 'Manually'), ('link', 'Link')], \
                                    'Answer Type', required=1, readonly=1),
        'question_ids' : fields.one2many('survey.response.line', 'response_id', 'Answer'),
        'state' : fields.selection([('done', 'Finished '),('skip', 'Not Finished')], \
                            'Status', readonly=True),
    }
    _defaults = {
        'state' : lambda * a: "skip",
        'response_type' : lambda * a: "manually",
    }

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['user_id','date_create'], context=context)
        res = []
        for record in reads:
            name = (record['user_id'] and record['user_id'][1] or '' )+ ' (' + record['date_create'].split('.')[0] + ')'
            res.append((record['id'], name))
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_('Warning !'),_('You cannot duplicate the resource!'))

survey_response()

class survey_response_line(osv.osv):
    _name = 'survey.response.line'
    _description = 'Survey Response Line'
    _rec_name = 'date_create'
    _columns = {
        'response_id': fields.many2one('survey.response', 'Answer', ondelete='cascade'),
        'date_create': fields.datetime('Create Date', required=1),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Answered'),('skip', 'Skiped')],\
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
        'state' : lambda * a: "draft",
    }

survey_response_line()

class survey_tbl_column_heading(osv.osv):
    _name = 'survey.tbl.column.heading'
    _order = 'name'
    _columns = {
        'name': fields.integer('Row Number'),
        'column_id': fields.many2one('survey.question.column.heading', 'Column'),
        'value': fields.char('Value', size = 255),
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
        'column_id': fields.many2one('survey.question.column.heading','Column'),
        'answer': fields.char('Value', size =255),
        'value_choice': fields.char('Value Choice', size =255),
        'comment': fields.text('Notes'),
        'comment_field': fields.char('Comment', size = 255)
    }

survey_response_answer()

class res_users(osv.osv):
    _inherit = "res.users"
    _name = "res.users"
    _columns = {
        'survey_id': fields.many2many('survey', 'survey_users_rel', 'uid', 'sid', 'Groups'),
    }

res_users()

class survey_request(osv.osv):
    _name = "survey.request"
    _order = 'date_deadline'
    _rec_name = 'date_deadline'
    _columns = {
        'date_deadline': fields.date("Deadline date"),
        'user_id': fields.many2one("res.users", "User"),
        'email': fields.char("E-mail", size=64),
        'survey_id': fields.many2one("survey", "Survey", required=1, ondelete='cascade'),
        'response': fields.many2one('survey.response', 'Answer'),
        'state': fields.selection([('draft','Draft'),('waiting_answer', 'Waiting Answer'),('done', 'Done'),('cancel', 'Cancelled')], 'State', readonly=1)
    }
    _defaults = {
        'state': lambda * a: 'draft',
#        'date_deadline': lambda * a :  (datetime.now() + relativedelta(months=+1)).strftime("%Y-%m-%d %H:%M:%S")
    }
    def survey_req_waiting_answer(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, { 'state' : 'waiting_answer'})
        return True

    def survey_req_draft(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, { 'state' : 'draft'})
        return True

    def survey_req_done(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, { 'state' : 'done'})
        return True

    def survey_req_cancel(self, cr, uid, ids, arg):
        self.write(cr, uid, ids, { 'state' : 'cancel'})
        return True

    def on_change_user(self, cr, uid, ids, user_id, context=None):
        if user_id:
            user_obj = self.pool.get('res.users')
            user = user_obj.browse(cr, uid, user_id, context=context)
            return {'value': {'email': user.address_id.email}}
        return {}

survey_request()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
