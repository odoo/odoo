# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.osv.orm import except_orm
from openerp.tools import mute_logger
from time import time


class test_survey_answer():

    def setUp(self):
        cr, uid = self.cr, self.uid
        # Usefull models
        self.ir_model = self.registry('ir.model')
        self.ir_model_data = self.registry('ir.model.data')
        self.obj_survey = self.registry('survey')
        self.obj_survey_response = self.registry('survey.response')
        self.obj_survey_question_wiz = self.registry('survey.question.wiz')
        self.obj_survey_name_wiz = self.registry('survey.name.wiz')
        self.obj_survey_print = self.registry('survey.print')

        self.survey_id = self.obj_survey.create(cr, uid, {
            'title': 'Initial Partner Feedback',
            'max_response_limit': 20,
            'type': ref("survey_type2"),
            'state': 'draft',
            'authenticate': 0,
            'date_open': time.strftime('%Y-%m-%d %H:%M:%S')
          })

        self.survey_browse = self.obj_survey.browse(cr, uid, self.survey_id, context)

    #@mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def test_00_survey_public(self):
        cr, uid = self.cr, self.uid
        # In order to check the survey module in OpenERP I use the survey "Initial Partner Feedback".

        # I set the survey in Open state.
        self.obj_survey.survey_open(cr, uid, [self.survey_id], context)

        # I check state of survey is open or not.
        self.assertEqual(self.survey_browse.state, 'open', 'Survey should be in open state')

        # I check that the survey is reopened or not.
        self.obj_survey.survey_cancel(cr, uid, [self.survey_id], context)
        self.obj_survey.survey_open(cr, uid, [self.survey_id], context)
        self.assertEqual(self.survey_browse.state, 'open', 'Survey should be in open state again')

        # I set the state of the survey open.
        self.obj_survey.survey_open(cr, uid, [self.survey_id], context)

        # In order to print the survey I click on Print.
        id = self.obj_survey_print.create(cr, uid, {'survey_ids': [(6, 0, [self.survey_id])]})
        self.obj_survey_print.action_next(cr, uid, [id], context)

        # In order to answer the survey I click on "Answer a Survey" with a public token.
        ctx = {}
        ctx.update({'survey_id': self.survey_id, 'survey_token': self.survey_browse.token})
        fields_view = self.obj_survey_question_wiz.fields_view_get(self, cr, uid, view_id=None, view_type='form', context=ctx)
        id = self.obj_survey_question_wiz.create(cr, uid, {}, ctx)
        self.obj_survey_question_wiz.action_next(cr, uid, [id], ctx)

        # I give the answer of the first and second page of the survey.
        #ctx = {'active_model':'survey', 'active_id': self.survey_id, 'active_ids': [self.survey_id]}
        self.obj_survey_question_wiz.fields_view_get(cr, uid, ref("survey.view_survey_question_message"),"form", context=ctx)
        values = self.obj_survey_question_wiz.default_get(cr, uid, ['name'], ctx)
        id = self.obj_survey_question_wiz.create(cr, uid, {str(ref("survey_initial_question_company_name")) +"_single" :'Tiny' , str(ref("survey_initial_question_company_size")) + "_selection" : int(ref("survey.survey_initial_question_company_size_51")), }, context)
        self.obj_survey_question_wiz.action_next(cr, uid, [id], context)
        id = self.obj_survey_question_wiz.create(cr, uid, {str(ref("survey_initial_question_contract_customers")) + "_selection" : int(ref("survey_initial_answer_sometimes")), str(ref("survey_initial_question_sell_to_your_customers")) + "_selection" : int(ref("survey_initial_answer_maintenance_contract")), }, context)
        self.obj_survey_question_wiz.action_next(cr, uid, [id], context)

        # I edit questions of the survey as per requirement.
        id = self.obj_survey_name_wiz.create(cr, uid, {'survey_id': self.survey_id})
        ctx.update({'question_id': ref('survey_initial_question_company_name'), 'page_number': -1, 'sur_name_id': id})
        self.obj_survey_question_wiz.action_edit_question(cr, uid, [ref('survey_initial_question_company_name')], context=ctx)
        self.obj_survey_question_wiz.action_delete_question(cr, uid, [ref('survey_initial_question_company_name')], context=ctx)
        self.obj_survey_question_wiz.action_new_question(cr, uid, [], context=ctx)

        # I edit Page of the survey as per requirement.
        id = self.obj_survey_name_wiz.create(cr, uid, {'survey_id': self.survey_id})
        ctx.update({'page_id': ref('survey_initial_page_Contracts'), 'sur_name_id': id})
        self.obj_survey_question_wiz.action_edit_page(cr, uid, [ref('survey_initial_page_Contracts')], context=ctx)
        self.obj_survey_question_wiz.action_delete_page(cr, uid, [ref('survey_initial_page_Contracts')], context=ctx)
        self.obj_survey_question_wiz.action_new_page(cr, uid, [], context=ctx)

        # In order to send invitation to the users I click on "Send Invitation" wizard.

        # I set the survey in Cancel state.
        self.obj_survey.survey_cancel(cr, uid, [self.survey_id], context)

        # I check state of survey is cancel or not.
        self.assertEqual(self.survey_browse.state, 'cancel', 'Survey should be in cancel state')

        # I set the survey in close state.
        self.obj_survey.survey_close(cr, uid, [self.survey_id], context)

        # I check state of Survey is close or not.
        self.assertEqual(self.survey_browse.state, 'close', 'Survey should be in cancel state')

        # sur_question = self.on_change_type(cr, uid, [ref("survey_Initial_partner_feedback")], 'multiple_textboxes_diff_type')
