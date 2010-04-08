# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields,osv,orm
from tools.translate import _

AVAILABLE_STATES = [
    ('draft','New'),
    ('open','In Progress'),
    ('cancel', 'Refused'),
    ('done', 'Hired'),
    ('pending','Pending')
]

AVAILABLE_PRIORITIES = [
    ('5','Not Good'),
    ('4','On Average'),
    ('3','Good'),
    ('2','Very Good'),
    ('1','Excellent')
]


class hr_applicant(osv.osv):
    _name = "hr.applicant"
    _description = "Applicant Cases"
    _order = "id desc"
    _inherit ='crm.case'
    _columns = {
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed': fields.float('Proposed Salary'),
        'salary_expected': fields.float('Expected Salary'),
        'availability': fields.integer('Availability (Days)'),
        'partner_name': fields.char("Applicant's Name", size=64),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('object_id.model', '=', 'hr.applicant')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('object_id.model', '=', 'hr.applicant')]"),
        'department_id':fields.many2one('hr.department','Department'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'survey' : fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response' : fields.integer("Response"),
    }

    def stage_previous(self, cr, uid, ids, context=None):
        """This function computes previous stage for case from its current stage
             using available stage for that case type 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [])
            if st and stage_ids.index(st):
                self.write(cr, uid, [case.id], {'stage_id': stage_ids[stage_ids.index(st)-1]})
        return True

    def stage_next(self, cr, uid, ids, context=None):
        """This function computes next stage for case from its current stage
             using available stage for that case type 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param context: A standard dictionary for contextual values"""
        if not context:
            context = {}
        for case in self.browse(cr, uid, ids, context):
            section = (case.section_id.id or False)
            st = case.stage_id.id  or False
            stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [])
            if st and len(stage_ids) != stage_ids.index(st)+1:
                self.write(cr, uid, [case.id], {'stage_id': stage_ids[stage_ids.index(st)+1]})
        return True

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Opportunity to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Meeting view
        """
        value = {}
        for opp in self.browse(cr, uid, ids):
            data_obj = self.pool.get('ir.model.data')

            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            context = {
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',
                'default_name': opp.name
            }
            value = {
                'name': _('Meetings'),
                'domain': "[('user_id','=',%s)]" % (uid),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1, 'calendar'), (id2, 'form'), (id3, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id'],
                'nodestroy': True
            }
        return value

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
        if not context:
            context = {}
        datas = {}
        record = self.browse(cr, uid, ids, context)
        record = record and record[0]
        page_setting = {'orientation': 'vertical', 'without_pagebreak': 0, 'paper_size': 'letter', 'page_number': 1, 'survey_title': 1}
        report = {}
        if record:
            datas['ids'] = [record.survey.id]
            response_id = record.response
            if response_id:
                context.update({'survey_id': datas['ids'], 'response_id' : [response_id], 'response_no':0,})
                datas['form'] = page_setting
                datas['model'] = 'survey.print.answer'
                report = {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'survey.browse.response',
                    'datas': datas,
                    'nodestroy': True,
                    'context' : context
                }
            else:
                datas['form'] = page_setting
                datas['model'] = 'survey.print'
                report = {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'survey.form',
                    'datas': datas,
                    'nodestroy':True,
                    'context' : context
                }
        return report
    
hr_applicant()

class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _columns = {
        'survey_id': fields.many2one('survey', 'Survey'),
    }

hr_job()