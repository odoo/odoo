## -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http: //tiny.be>).
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
#    along with this program.  If not, see <http: //www.gnu.org/licenses/>.
#
##############################################################################

from urllib import urlencode
import lxml
from lxml import etree

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools import to_xml
from datetime import datetime
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from openerp import SUPERUSER_ID
import uuid

DATETIME_FORMAT = "%Y-%m-%d"


class survey_question_wiz(osv.osv_memory):
    _name = 'survey.question.wiz'

    _columns = {
        'name': fields.integer('Number'),

        'survey_id': fields.many2one('survey', 'Survey', required=True, ondelete='cascade', domain=[('state', 'in', ['draft', 'open'])]),
        'page_no': fields.integer('Page Number'),
        'page': fields.char('Page Position'),
        'transfer': fields.boolean('Page Transfer'),
        'response_id': fields.many2one('survey.response', 'Answer'),
    }
    _defaults = {
        'page_no': -1,
        'page': 'next',
        'transfer': True,
        'survey_id': lambda self, cr, uid, context: context.get('survey_id', False),
    }

    def _view_field_multiple_choice_only_one_ans(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        selection = []
        for ans in que_rec.answer_choice_ids:
            selection.append((tools.ustr(ans.id), ans.answer))
        xml_group = etree.SubElement(xml_group, 'group', {'col': '2', 'colspan': '2'})
        etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_selection"})
        fields[tools.ustr(que.id) + "_selection"] = {'type': 'selection', 'selection': selection, 'string': "Answer"}

    def _view_field_multiple_choice_multiple_ans(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        # TODO convert selection field into radio input
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        for ans in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id)})
            fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id)] = {'type': 'boolean', 'string': ans.answer}

    def _view_field_matrix_of_choices_only_multi_ans(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        que_col_head = self.pool.get('survey.question.column.heading')

        xml_group = etree.SubElement(xml_group, 'group', {'col': str(len(que_rec.column_heading_ids) + 1), 'colspan': '4'})
        etree.SubElement(xml_group, 'separator', {'string': '.', 'colspan': '1'})
        for col in que_rec.column_heading_ids:
            etree.SubElement(xml_group, 'separator', {'string': tools.ustr(col.title), 'colspan': '1'})
        for row in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'label', {'string': to_xml(tools.ustr(row.answer)) + ': -', 'align': '0.0'})
            for col in que_col_head.browse(cr, SUPERUSER_ID, [head.id for head in que_rec.column_heading_ids], context=context):
                etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(row.id) + "_" + tools.ustr(col.id), 'nolabel': "1"})
                fields[tools.ustr(que.id) + "_" + tools.ustr(row.id) + "_" + tools.ustr(col.id)] = {'type': 'boolean', 'string': col.title}

    def _view_field_multiple_textboxes(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        type = "char"
        if que_rec.is_validation_require:
            if que_rec.validation_type in ['must_be_whole_number']:
                type = "integer"
            elif que_rec.validation_type in ['must_be_decimal_number']:
                type = "float"
            elif que_rec.validation_type in ['must_be_date']:
                type = "date"
        for ans in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"})
            fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"] = {'type': str(type), 'string': ans.answer}

    def _view_field_numerical_textboxes(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        for ans in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_numeric"})
            fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_numeric"] = {'type': 'integer', 'string': ans.answer}

    def _view_field_date(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        for ans in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id)})
            fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id)] = {'type': 'date', 'string': ans.answer}

    def _view_field_date_and_time(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        for ans in que_rec.answer_choice_ids:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id)})
            fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id)] = {'type': 'datetime', 'string': ans.answer}

    def _view_field_descriptive_text(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        if que_rec.descriptive_text:
            html = lxml.html.fromstring('<div>%s</div>' % "<br/>".join(que_rec.descriptive_text.split('\n')))
            xml_group.insert(0, html)

    def _view_field_single_textbox(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_single", 'nolabel': "1", 'colspan': "4"})
        fields[tools.ustr(que.id) + "_single"] = {'type': 'char', 'size': 255, 'string': "single_textbox", 'views': {}}

    def _view_field_comment(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_comment", 'nolabel': "1", 'colspan': "4"})
        fields[tools.ustr(que.id) + "_comment"] = {'type': 'text', 'string': "Comment/Eassy Box", 'views': {}}

    def _view_field_table(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': str(len(que_rec.column_heading_ids)), 'colspan': '4'})
        for col in que_rec.column_heading_ids:
            etree.SubElement(xml_group, 'label', {'string': tools.ustr(col.title)})
        for row in range(0, que_rec.no_of_rows):
            for col in que_rec.column_heading_ids:
                etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_table_" + tools.ustr(col.id) + "_" + tools.ustr(row), 'nolabel': "1"})
                fields[tools.ustr(que.id) + "_table_" + tools.ustr(col.id) + "_" + tools.ustr(row)] = {'type': 'char', 'size': 255, 'views': {}}

    def _view_field_multiple_textboxes_diff_type(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        xml_group = etree.SubElement(xml_group, 'group', {'col': '4', 'colspan': '4'})
        for ans in que_rec.answer_choice_ids:
            if ans.type == "email":
                fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"] = {'type': 'char', 'string': ans.answer}
                etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'widget': 'email', 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"})
            else:
                etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"})
                if ans.type == "char":
                    fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"] = {'type': 'char', 'string': ans.answer}
                elif ans.type in ['integer', 'float', 'date', 'datetime']:
                    fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"] = {'type': str(ans.type), 'string': ans.answer}
                else:
                    selection = []
                    if ans.menu_choice:
                        for item in ans.menu_choice.split('\n'):
                            if item and not item.strip() == '':
                                selection.append((item, item))
                    fields[tools.ustr(que.id) + "_" + tools.ustr(ans.id) + "_multi"] = {'type': 'selection', 'selection': selection, 'string': ans.answer}

    def _view_field_matrix_of_choices_only_one_ans(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        col = que_rec.comment_column and "3" or "2"
        xml_group = etree.SubElement(xml_group, 'group', {'col': tools.ustr(col), 'colspan': "4"})
        first = True
        for row in que_rec.answer_choice_ids:
            name_select = tools.ustr(que.id) + "_selection_" + tools.ustr(row.id)
            etree.SubElement(xml_group, 'newline')
            etree.SubElement(xml_group, 'label', {'for': name_select, 'string': tools.ustr(row.answer)})
            etree.SubElement(xml_group, 'field', {'widget': 'radio', 'horizontal': '1', 'no_radiolabel': not first and '1' or '0', 'modifiers': readonly, 'name': name_select, 'nolabel': "1"})
            selection = []
            for col in que_rec.column_heading_ids:
                selection.append((str(col.id), col.title))
            if que_rec.comment_column:
                name_comment = tools.ustr(que.id) + "_commentcolumn_" + tools.ustr(row.id) + "_field"
                if first:
                    div_group = etree.SubElement(xml_group, 'div', {'class': 'oe_survey_matrix_of_choices_comment'})
                    etree.SubElement(div_group, 'label', {'string': tools.ustr(que.column_name)})
                    etree.SubElement(div_group, 'newline')
                    etree.SubElement(div_group, 'field', {'modifiers': readonly, 'name': name_comment, 'nolabel': "1"})
                else:
                    etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': name_comment, 'nolabel': "1"})
                fields[name_comment] = {'type': 'char', 'string': tools.ustr(que_rec.column_name), 'views': {}}
            fields[name_select] = {'type': 'selection', 'selection': selection, 'string': "Answer"}
            first = False

    def _view_field_rating_scale(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        self._view_field_matrix_of_choices_only_one_ans(xml_group, fields, readonly, que, que_rec)

    def _view_field_postprocessing(self, cr, uid, xml_group, fields, readonly, que, que_rec, context=None):
        # after matrix of choices
        if que_rec.type in ['multiple_choice_only_one_ans', 'multiple_choice_multiple_ans'] and que_rec.comment_field_type in ['char', 'text'] and que_rec.make_comment_field:
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_otherfield", 'colspan': "4"})
            fields[tools.ustr(que.id) + "_otherfield"] = {'type': 'boolean', 'string': que_rec.comment_label, 'views': {}}
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_other", 'nolabel': "1", 'colspan': "4"})
            fields[tools.ustr(que.id) + "_other"] = {'type': que_rec.comment_field_type, 'string': '', 'views': {}}
        else:
            etree.SubElement(xml_group, 'label', {'string': to_xml(tools.ustr(que_rec.comment_label)), 'colspan': "4"})
            etree.SubElement(xml_group, 'field', {'modifiers': readonly, 'name': tools.ustr(que.id) + "_other", 'nolabel': "1", 'colspan': "4"})
            fields[tools.ustr(que.id) + "_other"] = {'type': que_rec.comment_field_type, 'string': '', 'views': {}}

    def _survey_complete(self, cr, uid, survey_id, context):
        """ list of action to do when the survey is completed
        """
        user_browse = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        val = {
            'type': 'notification',
            'model': 'survey',
            'res_id': survey_id,
            'record_name': _("Survey N° %s") % survey_id,
            'body': _("%s have post a new response on this survey.") % user_browse.name,
        }
        self.pool.get('survey').message_post(cr, SUPERUSER_ID, survey_id, context=context, **val)

    def get_response_info_from_token(self, cr, uid, survey_id, survey_token, context=None):
        """
        Get the response informations and return a dictionnary
        * response_id
        * state
        * readonly
        If it's a public token or survey_id = False, return the dictionnary with response_id = False
        If no response and the token doesn't match with the survey public token,
        This function raise an exception

        """
        context = context or {}
        res = {'response_id': False, 'state': None, 'readonly': context.get('readonly', False)}

        if not survey_id:
            return res

        survey_obj = self.pool.get('survey')
        survey_browse = survey_obj.browse(cr, SUPERUSER_ID, survey_id, context=context)
        user_browse = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        pid = user_browse.partner_id.id
        anonymous = self.check_anonymous(cr, uid, [uid], context=context)

        # to do: check if context.get('edit') is allow
        if context.get('edit') or context.get('survey_test'):
            try:
                survey_obj.check_access_rights(cr, uid, 'write')
                survey_obj.check_access_rule(cr, uid, [survey_id], 'write', context=context)
            except except_orm, e:
                context['edit'] = False
                context['survey_test'] = False

        # check open and sign in
        if not context.get('edit') and not context.get('survey_test') and survey_browse.state != "open":
            raise osv.except_osv(_('Access Denied!'), _("You cannot answer because the survey is not open."))
        if anonymous and survey_browse.authenticate:
            raise osv.except_osv(_('Access Denied!'), _("Please Login to complete this survey."))

        # get opening response
        response_ids = None
        sur_response_obj = self.pool.get('survey.response')
        dom = [('survey_id', '=', survey_id),
            "|", ('state', '=', 'test'),
            "&", ('state', 'in', ['new', 'skip']), "|", ('date_deadline', '=', None), ('date_deadline', '>', datetime.now())]

        # check for private token
        if survey_token:
            response_ids = sur_response_obj.search(cr, SUPERUSER_ID, dom + [("token", "=", survey_token)], context=context, limit=1, order="id DESC")
        # check for admin preview responses
        if not response_ids and context.get("response_id"):
            try:
                survey_obj.check_access_rights(cr, uid, 'write')
                survey_obj.check_access_rule(cr, uid, [survey_id], 'write', context=context)
                response_ids = [context.get("response_id")]
            except except_orm, e:
                response_ids = None
        # check sign in user
        if not response_ids and not anonymous:
            response_ids = sur_response_obj.search(cr, SUPERUSER_ID, dom + [('partner_id', '=', pid)], context=context, limit=1, order="date_deadline DESC")

        # user have a specific token or a specific partner access (for state open or restricted)
        if response_ids:
            response = sur_response_obj.browse(cr, SUPERUSER_ID, response_ids[0], context=context)
            res['response_id'] = response_ids[0]
            res['state'] = response.state

        # errors
        if not res['response_id'] and not context.get('edit') and not context.get('survey_test') and (survey_browse.state != 'open' or str(survey_browse.token) != str(survey_token)):

            response_ids = sur_response_obj.search(cr, SUPERUSER_ID, [('survey_id', '=', survey_id), ("token", "=", context.get("survey_token", None))], context=context, limit=1)
            if not response_ids:
                response_ids = sur_response_obj.search(cr, SUPERUSER_ID, [('survey_id', '=', survey_id), ('partner_id', '=', pid)], context=context, limit=1)

            if not response_ids:
                raise osv.except_osv(_('Access Denied!'), _("You do not have access to this survey."))
            else:
                response = sur_response_obj.browse(cr, SUPERUSER_ID, response_ids[0], context=context)
                if response.state == 'cancel':
                    raise osv.except_osv(_('Access Denied!'), _("You do not have access to this survey because, your survey access is canceled."))
                elif response.state == 'done':
                    res['response_id'] = context.get('response_id') and int(context['response_id'][0])
                    res['state'] = 'done'
                    res['readonly'] = True
                elif response.date_deadline and datetime.strptime(response.date_deadline, DATETIME_FORMAT) < datetime.now():
                    raise osv.except_osv(_('Access Denied!'), _("The deadline for responding to this survey is exceeded since %s") % response.date_deadline)
                else:
                    raise osv.except_osv(_('Access Denied!'), _("You do not have access to this survey."))

        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Fields View Get method: - generate the new view and display the survey pages of selected survey.
        """
        if context is None:
            context = {}

        result = super(survey_question_wiz, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)

        survey_obj = self.pool.get('survey')
        page_obj = self.pool.get('survey.page')
        que_obj = self.pool.get('survey.question')

        if view_type in ['form']:
            wiz_id = 0
            survey_id = None
            sur_name_rec = None
            if 'wizard_id' in context:
                sur_name_rec = self.browse(cr, uid, context['wizard_id'], context=context)
                survey_id = sur_name_rec.survey_id.id
            elif context.get('survey_id'):
                survey_id = context.get('survey_id')
                res_data = {
                    'survey_id': survey_id,
                    'page_no': -1,
                    'page': 'next',
                    'transfer': 1,
                    'response_id': None,
                }
                wiz_id = self.create(cr, uid, res_data, context=context)
                sur_name_rec = self.browse(cr, uid, wiz_id, context=context)
                context.update({'wizard_id': wiz_id})

            if context.get('active_id'):
                context.pop('active_id')

            if not survey_id:
                return result

            # get if the token of the partner or anonymous user is valid
            response_info = self.get_response_info_from_token(cr, uid, survey_id, context.get("survey_token"), context)

            survey_browse = survey_obj.browse(cr, SUPERUSER_ID, survey_id, context=context)
            p_id = [page.id for page in survey_browse.page_ids]
            total_pages = len(p_id)
            pre_button = False

            if not sur_name_rec.page_no + 1:
                self.write(cr, uid, [wiz_id], {'store_ans': {}})

            sur_name_read = self.browse(cr, uid, context['wizard_id'], context=context)
            page_number = int(sur_name_rec.page_no)

            if sur_name_read.transfer or not sur_name_rec.page_no + 1:
                self.write(cr, uid, [context['wizard_id']], {'transfer': False})
                flag = False
                fields = {}

                # have acces to this survey
                edit_mode = context.get('edit', False)

                if sur_name_read.page == "next" or sur_name_rec.page_no == -1:
                    if total_pages > sur_name_rec.page_no + 1:
                        if response_info['state'] != 'test' and survey_browse.max_response_limit and \
                                survey_browse.max_response_limit <= survey_browse.tot_start_survey and not sur_name_rec.page_no + 1:
                            survey_obj.write(cr, SUPERUSER_ID, survey_id, {'state': 'close', 'date_close': datetime.now()}, context=context)

                        p_id = p_id[sur_name_rec.page_no + 1]
                        self.write(cr, uid, [context['wizard_id'], ], {'page_no': sur_name_rec.page_no + 1})
                        flag = True
                        page_number += 1
                    if sur_name_rec.page_no > - 1:
                        pre_button = True
                    else:
                        flag = True
                else:
                    if sur_name_rec.page_no != 0:
                        p_id = p_id[sur_name_rec.page_no - 1]
                        self.write(cr, uid, [context['wizard_id'], ], {'page_no': sur_name_rec.page_no - 1})
                        flag = True
                        page_number -= 1

                    if sur_name_rec.page_no > 1:
                        pre_button = True

                # survey in progress (not complete)
                if flag:
                    pag_rec = page_obj.browse(cr, SUPERUSER_ID, p_id, context=context)
                    xml_form = etree.Element('form', {'version': "7.0", 'class': 'oe_survey_answer', 'string': tools.ustr(pag_rec and pag_rec.title or survey_browse.title)})
                    xml_form = etree.SubElement(xml_form, 'sheet')

                    if edit_mode:
                        context.update({'page_id': tools.ustr(p_id), 'page_number': sur_name_rec.page_no, 'transfer': sur_name_read.transfer})
                        xml_group3 = etree.SubElement(xml_form, 'group', {'col': '4', 'colspan': '4'})
                        etree.SubElement(xml_group3, 'button', {'string': _('Add Page'), 'icon': "gtk-new", 'type': 'object', 'name': "action_new_page", 'context': tools.ustr(context)})
                        if total_pages:
                            etree.SubElement(xml_group3, 'button', {'string': _('Edit Page'), 'icon': "gtk-edit", 'type': 'object', 'name': "action_edit_page", 'context': tools.ustr(context)})
                            etree.SubElement(xml_group3, 'button', {'string': _('Delete Page'), 'icon': "gtk-delete", 'type': 'object', 'name': "action_delete_page", 'context': tools.ustr(context)})
                            etree.SubElement(xml_group3, 'button', {'string': _('Add Question'), 'icon': "gtk-new", 'type': 'object', 'name': "action_new_question", 'context': tools.ustr(context)})

                    # FP Note
                    xml_group = xml_form

                    if pag_rec and pag_rec.note:
                        xml_group_note = etree.SubElement(xml_form, 'group', {'col': '1', 'colspan': '4'})
                        for que_test in pag_rec.note.split('\n'):
                            etree.SubElement(xml_group_note, 'label', {'string': to_xml(tools.ustr(que_test)), 'align': "0.0"})

                    qu_no = 0
                    for que in (pag_rec and pag_rec.question_ids or []):
                        qu_no += 1
                        que_rec = que_obj.browse(cr, SUPERUSER_ID, que.id, context=context)
                        separator_string = tools.ustr(qu_no) + ". " + tools.ustr(que_rec.question)
                        star = que_rec.is_require_answer and '*' or ''
                        # display title
                        etree.SubElement(xml_form, 'separator', {'string': star + to_xml(separator_string)})
                        if edit_mode:
                            xml_group1 = etree.SubElement(xml_form, 'group', {'col': '2', 'colspan': '2'})
                            context.update({'question_id': tools.ustr(que.id), 'page_number': sur_name_rec.page_no, 'transfer': sur_name_read.transfer, 'page_id': p_id})
                            etree.SubElement(xml_group1, 'button', {'string': '', 'icon': "gtk-edit", 'type': 'object', 'name': "action_edit_question", 'context': tools.ustr(context)})
                            etree.SubElement(xml_group1, 'button', {'string': '', 'icon': "gtk-delete", 'type': 'object', 'name': "action_delete_question", 'context': tools.ustr(context)})

                        xml_group = etree.SubElement(xml_form, 'group', {'col': '1', 'colspan': '4', 'class': 'oe_survey_%s' % que_rec.type})

                        readonly = response_info['readonly'] and '{"readonly": 1}' or '{}'
                        # display description
                        if que_rec.type not in ['descriptive_text']:
                            self._view_field_descriptive_text(cr, uid, xml_group, fields, readonly, que, que_rec, context=context)
                            etree.SubElement(xml_group, 'newline')
                        # rendering different views
                        getattr(self, "_view_field_%s" % que_rec.type)(cr, uid, xml_group, fields, readonly, que, que_rec, context=context)
                        if que_rec.type in ['multiple_choice_only_one_ans', 'multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale'] and que_rec.is_comment_require:
                            self._view_field_postprocessing(cr, uid, xml_group, fields, readonly, que, que_rec, context=context)

                    xml_footer = etree.SubElement(xml_form, 'footer', {'col': '8', 'width': "100%"})

                    if pre_button:
                        etree.SubElement(xml_footer, 'label', {'string': ""})
                        etree.SubElement(xml_footer, 'button', {'name': "action_previous", 'string': _("Previous"), 'type': "object"})
                    if int(page_number) + 1 == total_pages:
                        if not response_info['readonly']:
                            etree.SubElement(xml_footer, 'label', {'string': ""})
                            etree.SubElement(xml_footer, 'button', {'name': "action_done", 'string': _('Done'), 'type': "object", 'context': tools.ustr(context), 'class': "oe_highlight"})
                    else:
                        etree.SubElement(xml_footer, 'label', {'string': ""})
                        etree.SubElement(xml_footer, 'button', {'name': "action_next", 'string': _("Next"), 'type': "object", 'context': tools.ustr(context), 'class': not response_info['readonly'] and "oe_highlight" or ""})
                    if context.get('ir_actions_act_window_target') != 'inline':
                        etree.SubElement(xml_footer, 'label', {'string': _("or")})
                        etree.SubElement(xml_footer, 'button', {'special': "cancel", 'string': _("Exit"), 'class': "oe_link"})
                    etree.SubElement(xml_footer, 'label', {'string': tools.ustr(page_number + 1) + "/" + tools.ustr(total_pages), 'class': "oe_survey_title_page oe_right"})

                    root = xml_form.getroottree()
                    result['arch'] = etree.tostring(root)
                    result['fields'] = fields
                    result['context'] = context

        return result

    def default_get(self, cr, uid, fields_list, context=None):
        """
        Assign Default value in particular field. If Browse Answers wizard run then read the value into database and Assigne to a particular fields.
        """
        value = {}
        if context is None:
            context = {}

        for field in fields_list:
            if field.split('_')[0] == 'progress':
                tot_page_id = self.pool.get('survey').browse(cr, SUPERUSER_ID, context.get('survey_id', False), context=context)
                tot_per = (float(100) * (int(field.split('_')[2]) + 1) / len(tot_page_id.page_ids))
                value[field] = tot_per

        response_info = self.get_response_info_from_token(cr, uid, context.get('survey_id'), context.get("survey_token"), context)

        sur_response_obj = self.pool.get('survey.response')
        if not context.get('edit') and response_info.get('response_id'):
            response_ans = sur_response_obj.browse(cr, SUPERUSER_ID, response_info['response_id'], context=context)

            fields_list.sort()
            for que in response_ans.question_ids:
                for field in fields_list:
                    split_field = field.split('_')
                    _id = split_field[0]
                    if _id == str(que.question_id.id):
                        _type = split_field[1]
                        if que.response_answer_ids and len(split_field) == 4 and _type == "commentcolumn" and split_field[3] == "field":
                            for ans in que.response_answer_ids:
                                if str(split_field[2]) == str(ans.answer_id.id):
                                    value[field] = ans.comment_field

                        if que.response_answer_ids and len(split_field) == 4 and _type == "table":
                            for ans in que.response_answer_ids:
                                if str(split_field[2]) == str(ans.column_id.id) and str(split_field[3]) == str(ans.name):
                                    value[field] = ans.value

                        if que.comment and (_type == "comment" or _type == "other"):
                            value[field] = tools.ustr(que.comment)

                        elif que.single_text and _type == "single":
                            value[field] = tools.ustr(que.single_text)

                        elif que.response_answer_ids and len(split_field) == 3 and _type == "selection":
                            for ans in que.response_answer_ids:
                                if str(split_field[2]) == str(ans.answer_id.id):
                                    value[field] = str(ans.column_id.id)

                        elif que.response_answer_ids and len(split_field) == 2 and _type == "selection":
                            value[field] = str(que.response_answer_ids[0].answer_id.id)

                        elif que.response_answer_ids and len(split_field) == 3 and split_field[2] != "multi" and split_field[2] != "numeric":
                            for ans in que.response_answer_ids:
                                if str(_type) == str(ans.answer_id.id) and str(split_field[2]) == str(ans.column_id.id):
                                    if ans.value_choice:
                                        value[field] = ans.value_choice
                                    else:
                                        value[field] = True

                        else:
                            for ans in que.response_answer_ids:
                                if str(_type) == str(ans.answer_id.id):
                                    value[field] = ans.answer

        return value

    def _create_value_table(self, cr, uid, question_id, response_line_id, values, context=None):
        res_ans_obj = self.pool.get('survey.response.answer')
        for key1 in values:
            for key2 in values[key1]:
                if values[key1][key2]:
                    res_ans_obj.create(cr, SUPERUSER_ID, {
                        'response_table_id': response_line_id,
                        'column_id': key1,
                        'name': key2,
                        'value': values[key1][key2]
                    })

    def _create_value_selection(self, cr, uid, question_id, response_line_id, values, context=None):
        res_ans_obj = self.pool.get('survey.response.answer')
        for key1 in values:
            if values[key1]:
                res_ans_obj.create(cr, SUPERUSER_ID, {
                    'response_line_id': response_line_id,
                    'answer_id': key1,
                    'column_id': values[key1]
                })

    def _create_value_commentcolumn(self, cr, uid, question_id, response_line_id, values, context=None):
        res_ans_obj = self.pool.get('survey.response.answer')
        for key1 in values:
            if values[key1]:
                res_ans_obj.write(cr, SUPERUSER_ID, [response_line_id], {'comment_field': values[key1]})

    def create(self, cr, uid, vals, context=None):
        """
        Create the Answer of survey and store in survey.response object, and if set validation of question then check the value of question if value is wrong then raise the exception.
        """
        context = context or {}
        response_info = self.get_response_info_from_token(cr, uid, context['survey_id'], context.get("survey_token"), context)
        vals['survey_id'] = context['survey_id']

        sur_response_obj = self.pool.get('survey.response')
        resp_line_obj = self.pool.get('survey.response.line')
        que_obj = self.pool.get('survey.question')

        if context.get('edit', False) or response_info['readonly']:
            return super(survey_question_wiz, self).create(cr, uid, vals, context=context)

        # set response_id
        if response_info['response_id']:
            response_id = response_info['response_id']
        elif vals['response_id'] and vals['response_id'][0]:
            response_id = vals['response_id'][0]
        else:
            user_browse = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
            pid = user_browse.partner_id.id
            response_id = sur_response_obj.create(cr, SUPERUSER_ID, {
                'state': context.get('survey_test') and 'test' or 'new',
                'response_type': 'manually',
                'partner_id': pid,
                'date_create': datetime.now(),
                'survey_id': context['survey_id'],
                'token': uuid.uuid4(),
            })
            vals.update({'response_id': response_id})
        if sur_response_obj.browse(cr, SUPERUSER_ID, response_id).state != 'test':
            sur_response_obj.write(cr, SUPERUSER_ID, [response_id], {'state': 'skip'})

        # compilation of responses
        self_columns = [temp[0] for temp in self._columns.items()]
        list_response = {}
        for key, val in vals.items():
            if key in self_columns:
                continue
            split_key = key.split('_')
            que_id = int(split_key[0])
            _type = split_key[1]

            if que_id not in list_response:
                list_response[que_id] = {}
            if _type not in list_response[que_id]:
                list_response[que_id][_type] = {}

            rows = split_key[2:]
            rows.reverse()

            if rows:
                values = list_response[que_id][_type]
                row = rows.pop()
                while row:
                    if rows:
                        if row not in values:
                            values[row] = {}
                        values = values[row]
                        row = rows.pop()
                    else:
                        values[row] = val
                        break
            else:
                list_response[que_id][_type] = val

        # remove recorded responses
        ids = resp_line_obj.search(cr, SUPERUSER_ID, [('question_id', 'in', [que_id for que_id in list_response]), ('response_id', '=', response_id)], context=context)
        resp_line_obj.unlink(cr, SUPERUSER_ID, ids, context=context)

        resp_id_list = []
        for que_id in list_response:
            que_rec = que_obj.read(cr, SUPERUSER_ID, [que_id], context=context)[0]
            res_data = {
                'question_id': que_id,
                'date_create': datetime.now(),
                'state': 'done',
                'response_id': response_id
            }
            resp_id = resp_line_obj.create(cr, SUPERUSER_ID, res_data)
            resp_id_list.append(resp_id)
            for _type in list_response[que_id]:
                que_value = list_response[que_id][_type]
                if _type == 'table':
                        self._create_value_table(cr, uid, que_id, resp_id, que_value, context=None)
                if _type == 'selection':
                        self._create_value_selection(cr, uid, que_id, resp_id, que_value, context=None)
                # if _type == 'commentcolumn':
                #         self._create_value_commentcolumn(cr, uid, que_id, resp_id, que_value, context=None)

            # record different values
            #getattr(self, "_create_value_%s" % response_data['type'])(cr, uid, que_id, resp_id, que_value, context=None)


            # for key1, val1 in vals.items():
            #     if val1 and key1.split('_')[1] == "otherfield" and key1.split('_')[0] == que_id:
            #         comment_field = True
            #         select_count += 1
            #         continue

            #     elif key1.split('_')[1] == "other" and key1.split('_')[0] == que_id:
            #         if not val1:
            #             comment_value = True
            #         else:
            #             error = False
            #             if que_rec['is_comment_require'] and que_rec['comment_valid_type'] == 'must_be_specific_length':
            #                 if (not val1 and que_rec['comment_minimum_no']) or len(val1) < que_rec['comment_minimum_no'] or len(val1) > que_rec['comment_maximum_no']:
            #                     error = True
            #             elif que_rec['is_comment_require'] and que_rec['comment_valid_type'] in ['must_be_whole_number', 'must_be_decimal_number', 'must_be_date']:
            #                 error = False
            #                 try:
            #                     if que_rec['comment_valid_type'] == 'must_be_whole_number':
            #                         value = int(val1)
            #                         if value < que_rec['comment_minimum_no'] or value > que_rec['comment_maximum_no']:
            #                             error = True
            #                     elif que_rec['comment_valid_type'] == 'must_be_decimal_number':
            #                         value = float(val1)
            #                         if value < que_rec['comment_minimum_float'] or value > que_rec['comment_maximum_float']:
            #                             error = True
            #                     elif que_rec['comment_valid_type'] == 'must_be_date':
            #                         value = datetime.datetime.strptime(val1, "%Y-%m-%d")
            #                         if value < datetime.datetime.strptime(que_rec['comment_minimum_date'], "%Y-%m-%d") or value > datetime.datetime.strptime(que_rec['comment_maximum_date'], "%Y-%m-%d"):
            #                             error = True
            #                 except:
            #                     error = True
            #             elif que_rec['is_comment_require'] and que_rec['comment_valid_type'] == 'must_be_email_address':
            #                 import re
            #                 if not re.match("^[a-zA-Z0-9._%- + ] + @[a-zA-Z0-9._%-] + .[a-zA-Z]{2, 6}$", val1):
            #                         error = True
            #             if error:
            #                 raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "'  \n" + tools.ustr(que_rec['comment_valid_err_msg']))

            #             resp_line_obj.write(cr, SUPERUSER_ID, resp_id, {'comment': val1})

            #     elif val1 and key1.split('_')[1] == "comment" and key1.split('_')[0] == que_id:
            #         resp_line_obj.write(cr, SUPERUSER_ID, resp_id, {'comment': val1})
            #         select_count += 1

            #     elif val1 and key1.split('_')[0] == que_id and (key1.split('_')[1] == "single" or (len(key1.split('_')) > 2 and key1.split('_')[2] == 'multi')):
            #         error = False
            #         if que_rec['is_validation_require'] and que_rec['validation_type'] == 'must_be_specific_length':
            #             if (not val1 and que_rec['validation_minimum_no']) or len(val1) < que_rec['validation_minimum_no'] or len(val1) > que_rec['validation_maximum_no']:
            #                 error = True
            #         elif que_rec['is_validation_require'] and que_rec['validation_type'] in ['must_be_whole_number', 'must_be_decimal_number', 'must_be_date']:
            #             error = False
            #             try:
            #                 if que_rec['validation_type'] == 'must_be_whole_number':
            #                     value = int(val1)
            #                     if value < que_rec['validation_minimum_no'] or value > que_rec['validation_maximum_no']:
            #                         error = True
            #                 elif que_rec['validation_type'] == 'must_be_decimal_number':
            #                     value = float(val1)
            #                     if value < que_rec['validation_minimum_float'] or value > que_rec['validation_maximum_float']:
            #                         error = True
            #                 elif que_rec['validation_type'] == 'must_be_date':
            #                     value = datetime.datetime.strptime(val1, "%Y-%m-%d")
            #                     if value < datetime.datetime.strptime(que_rec['validation_minimum_date'], "%Y-%m-%d") or value > datetime.datetime.strptime(que_rec['validation_maximum_date'], "%Y-%m-%d"):
            #                         error = True
            #             except:
            #                 error = True
            #         elif que_rec['is_validation_require'] and que_rec['validation_type'] == 'must_be_email_address':
            #             import re
            #             if not re.match("^[a-zA-Z0-9._%- + ] + @[a-zA-Z0-9._%-] + .[a-zA-Z]{2, 6}$", val1):
            #                     error = True
            #         if error:
            #             raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "'  \n" + tools.ustr(que_rec['validation_valid_err_msg']))

            #         if key1.split('_')[1] == "single":
            #             resp_line_obj.write(cr, SUPERUSER_ID, resp_id, {'single_text': val1})
            #         else:
            #             ans_create_id = res_ans_obj.create(cr, SUPERUSER_ID, {'response_id': resp_id, 'answer_id': key1.split('_')[1], 'answer': val1})

            #         select_count += 1

            #     elif val1 and que_id == key1.split('_')[0] and len(key1.split('_')) > 2 and key1.split('_')[2] == 'numeric':
            #         if not val1 == "0":
            #             try:
            #                 numeric_sum += int(val1)
            #                 ans_create_id = res_ans_obj.create(cr, SUPERUSER_ID, {'response_id': resp_id, 'answer_id': key1.split('_')[1], 'answer': val1})
            #                 select_count += 1
            #             except:
            #                 raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "' \n" + _("Please enter an integer value."))

            #     elif val1 and que_id == key1.split('_')[0] and len(key1.split('_')) == 3:
            #         if type(val1) == type('') or type(val1) == type(u''):
            #             ans_create_id = res_ans_obj.create(cr, SUPERUSER_ID, {'response_id': resp_id, 'answer_id': key1.split('_')[1], 'column_id': key1.split('_')[2], 'value_choice': val1})
            #         else:
            #             ans_create_id = res_ans_obj.create(cr, SUPERUSER_ID, {'response_id': resp_id, 'answer_id': key1.split('_')[1], 'column_id': key1.split('_')[2]})
            #         select_count += 1

            #     elif val1 and que_id == key1.split('_')[0] and len(key1.split('_')) == 2:
            #         ans_create_id = res_ans_obj.create(cr, SUPERUSER_ID, {'response_id': resp_id, 'answer_id': key1.split('_')[-1], 'answer': val1})
            #         select_count += 1

            # for key, val in vals.items():
            #     if val and key.split('_')[1] == "commentcolumn" and key.split('_')[0] == que_id:
            #         for res_id in response_list:
            #             if key.split('_')[2] in res_id.split('_')[1]:
            #                 res_ans_obj.write(cr, SUPERUSER_ID, [res_id.split('_')[0]], {'comment_field': val})

            # if comment_field and comment_value:
            #     raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "' " + tools.ustr(que_rec['make_comment_field_err_msg']))

            # if que_rec['type'] == "rating_scale" and que_rec['rating_allow_one_column_require'] and len(selected_value) > len(list(set(selected_value))):
            #     raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "'\n" + _("You cannot select the same answer more than one time."))

            # if not select_count:
            #     resp_line_obj.write(cr, SUPERUSER_ID, resp_id, {'state': 'skip'})

            # if que_rec['numeric_required_sum'] and numeric_sum > que_rec['numeric_required_sum']:
            #     raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "' " + tools.ustr(que_rec['numeric_required_sum_err_msg']))

            # if que_rec['type'] in ['multiple_textboxes_diff_type', 'multiple_choice_multiple_ans', 'matrix_of_choices_only_one_ans', 'matrix_of_choices_only_multi_ans', 'rating_scale', 'multiple_textboxes', 'numerical_textboxes', 'date', 'date_and_time'] and que_rec['is_require_answer']:
            #     if (que_rec['required_type'] == 'all' and select_count < len(que_rec['answer_choice_ids'])) or \
            #         (que_rec['required_type'] == 'at least' and select_count < que_rec['req_ans']) or \
            #         (que_rec['required_type'] == 'at most' and select_count > que_rec['req_ans']) or \
            #         (que_rec['required_type'] == 'exactly' and select_count != que_rec['req_ans']) or \
            #         (que_rec['required_type'] == 'a range' and (select_count < que_rec['minimum_req_ans'] or select_count > que_rec['maximum_req_ans'])):
            #         raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "' " + tools.ustr(que_rec['req_error_msg']))

            # if que_rec['type'] in ['multiple_choice_only_one_ans', 'single_textbox', 'comment'] and que_rec['is_require_answer'] and select_count <= 0:
            #     raise osv.except_osv(_('Warning!'), "'" + que_rec['question'] + "' " + tools.ustr(que_rec['req_error_msg']))



        # (6, 0, resp_id_list)

        return super(survey_question_wiz, self).create(cr, uid, vals, context=context)

    def action_new_question(self, cr, uid, ids, context=None):
        """
        New survey.Question form.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if isinstance(key, bool):
                context.pop(key)
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.question'), ('name', '=', 'survey_question_wizard_test')], context=context)
        context.update({'show_button_ok': True})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': view_id,
            'context': context
        }

    def action_new_page(self, cr, uid, ids, context=None):
        """
        New survey.Page form.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if type(key) == type(True):
                context.pop(key)
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.page'), ('name', '=', 'survey_page_wizard_test')], context=context)
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.page',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': view_id,
            'context': context
        }

    def action_edit_page(self, cr, uid, ids, context=None):
        """
        Edit survey.page.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if type(key) == type(True):
                context.pop(key)
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.page'), ('name', '=', 'survey_page_wizard_test')], context=context)
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.page',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': int(context.get('page_id', 0)),
            'view_id': view_id,
            'context': context
        }

    def action_delete_page(self, cr, uid, ids, context=None):
        """
        Delete survey.page.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if type(key) == type(True):
                context.pop(key)

        self.pool.get('survey.page').unlink(cr, uid, [context.get('page_id', False)])
        for survey in self.pool.get('survey').browse(cr, uid, [context.get('survey_id', False)], context=context):
            if not survey.page_ids:
                return {'type': 'ir.actions.act_window_close'}

        search_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.question.wiz'), ('name', '=', 'Survey Search')], context=context)
        self.write(cr, uid, [context.get('wizard_id', False)], {'transfer': True, 'page_no': context.get('page_number', False)})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'search_view_id': search_id[0],
            'context': context
        }

    def action_edit_question(self, cr, uid, ids, context=None):
        """
        Edit survey.question.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if isinstance(key, bool):
                context.pop(key)
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.question'), ('name', '=', 'survey_question_wizard_test')], context=context)
        context.update({'show_button_ok': True})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': int(context.get('question_id', 0)),
            'view_id': view_id,
            'context': context
        }

    def action_delete_question(self, cr, uid, ids, context=None):
        """
        Delete survey.question.
        """
        if context is None:
            context = {}
        for key, val in context.items():
            if type(key) == type(True):
                context.pop(key)

        que_obj = self.pool.get('survey.question')
        que_obj.unlink(cr, uid, [context.get('question_id', False)])
        search_id = self.pool.get('ir.ui.view').search(cr, uid, [('model', '=', 'survey.question.wiz'), ('name', '=', 'Survey Search')], context=context)
        self.write(cr, uid, [context.get('wizard_id', False)], \
                     {'transfer': True, 'page_no': context.get('page_number', 0)})
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'survey.question.wiz',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'search_view_id': search_id[0],
                'context': context
                }

    def _action_next_previous(self, cr, uid, ids, next, context=None):
        """ Goes to nex page or previous page.
        """
        if context is None:
            context = {}
        self.write(cr, uid, [context.get('wizard_id', False)], {'transfer': True, 'page': next and 'next' or 'previous'})
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': context.get('ir_actions_act_window_target', 'new'),
            'context': context
        }

    def action_next(self, cr, uid, ids, context=None):
        """ Goes to Next page.
        """
        return self._action_next_previous(cr, uid, ids, True, context=context)

    def action_previous(self, cr, uid, ids, context=None):
        """ Goes to previous page.
        """
        return self._action_next_previous(cr, uid, ids, False, context=context)

    def action_done(self, cr, uid, ids, context=None):
        """ Goes to previous page.
        """
        response_id = None
        response_info = self.get_response_info_from_token(cr, uid, context['survey_id'], context.get("survey_token"), context)
        if response_info['response_id']:
            response_id = response_info['response_id']
        else:
            # public access
            sur_name_read = self.pool.get('survey.name.wiz').read(cr, uid, context.get('wizard_id', False), context=context)
            if sur_name_read['response_id'] and sur_name_read['response_id'][0]:
                response_id = sur_name_read['response_id'][0]

        if response_id:
            sur_response_obj = self.pool.get('survey.response')
            response = sur_response_obj.browse(cr, SUPERUSER_ID, response_id)
            if response.state != 'test':
                sur_response_obj.write(cr, SUPERUSER_ID, [response_id], {'state': 'done'})
            else:
                sur_response_obj.unlink(cr, SUPERUSER_ID, [response_id])
        else:
            return {'type': 'ir.actions.act_window_close'}

        self._survey_complete(cr, uid, context['survey_id'], context)

        ir_model_data = self.pool.get('ir.model.data')
        user_browse = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        model_id = ir_model_data.get_object_reference(cr, uid, 'base', 'group_user')
        employee = model_id and model_id[1] in [x.id for x in user_browse.groups_id]

        if employee:
            model, view_id = ir_model_data.get_object_reference(cr, uid, 'survey', 'view_survey_complete_survey')
        else:
            model, view_id = ir_model_data.get_object_reference(cr, uid, 'survey', 'view_survey_complete_survey_external')

        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.name.wiz',
            'type': 'ir.actions.act_window',
            'target': context.get('ir_actions_act_window_target', 'new'),
            'view_id': view_id,
        }

    def check_anonymous(self, cr, uid, ids, context=None):
        user_browse = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        try:
            model, anonymous_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_anonymous')
        except ValueError:
            return False
        return anonymous_id in [x.id for x in user_browse.groups_id]

    def _action_filling(self, cr, uid, ids, context=None):
        """ Check if the user have access to the survey and open survey
        """
        context.update({
            'survey_id': context.get('active_id'),
            'survey_token': context.get('params', True),
            'ir_actions_act_window_target': 'inline'})

        # check if the user must be authenticate
        survey_browse = self.pool.get('survey').browse(cr, SUPERUSER_ID, context['survey_id'], context=context)
        anonymous = self.check_anonymous(cr, uid, [uid], context=context)

        if anonymous and survey_browse.state == "open" and survey_browse.authenticate:
            return {
                'type': 'ir.actions.client',
                'tag': 'login',
                'context': context,
                'params': {
                    'login_successful': '#%s' % urlencode({
                        'active_id': context['survey_id'],
                        'action': 'survey.action_filling',
                        'params': context['survey_token'],
                    })
                },
            }

        # TODO : Add "force_login" in context act_window

        self.get_response_info_from_token(cr, uid, context['survey_id'], context['survey_token'], context=context)
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'survey.question.wiz',
            'type': 'ir.actions.act_window',
            'target': 'inline',
            'context': context,
        }

survey_question_wiz()

# vim: expandtab: smartindent: tabstop=4: softtabstop=4: shiftwidth=4:
