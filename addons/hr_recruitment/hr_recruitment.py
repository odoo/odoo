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
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]"),
        'department_id':fields.many2one('hr.department','Department'),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'survey' : fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response' : fields.integer("Response"),
    }
    
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
        record = self.read(cr, uid, ids, ['survey', 'response'])
        page_setting = {'orientation': 'vertical', 'without_pagebreak': 0, 'paper_size': 'letter', 'page_number': 1, 'survey_title': 1}
        report = {}
        if record:
            datas['ids'] = [record[0]['survey'][0]]
            response_id = record[0]['response']
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