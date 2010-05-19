# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import tools
from osv import fields,osv
from hr_recruitment import hr_recruitment

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class hr_recruitment_report(osv.osv):
    _name = "hr.recruitment.report"
    _description = "Recruitments Statistics"
    _auto = False
    _rec_name = 'date'
    
    def _get_data(self, cr, uid, ids, field_name, arg, context={}):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of case and section Data’s IDs
            @param context: A standard dictionary for contextual values """

        res = {}
        state_perc = 0.0
        avg_ans = 0.0

        for case in self.browse(cr, uid, ids, context):
            if field_name != 'avg_answers':
                state = field_name[5:]
                cr.execute("select count(*) from crm_opportunity where \
                    section_id =%s and state='%s'"%(case.section_id.id, state))
                state_cases = cr.fetchone()[0]
                perc_state = (state_cases / float(case.nbr)) * 100

                res[case.id] = perc_state
            else:
                model_name = self._name.split('report.')
                if len(model_name) < 2:
                    res[case.id] = 0.0
                else:
                    model_name = model_name[1]

                    cr.execute("select count(*) from crm_case_log l, ir_model m \
                         where l.model_id=m.id and m.model = '%s'" , model_name)
                    logs = cr.fetchone()[0]

                    avg_ans = logs / case.nbr
                    res[case.id] = avg_ans

        return res

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'avg_answers': fields.function(_get_data, string='Avg. Answers', method=True, type="integer"),
        'perc_done': fields.function(_get_data, string='%Done', method=True, type="float"),
        'perc_cancel': fields.function(_get_data, string='%Cancel', method=True, type="float"),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'day': fields.char('Day', size=128, readonly=True), 
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'date': fields.date('Date', readonly=True),
        'date_closed': fields.date('Closed', readonly=True),
        'job_id': fields.many2one('hr.job', 'Applied Job',readonly=True),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage'),
#        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]",readonly=True),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]"),
        'department_id':fields.many2one('hr.department','Department',readonly=True),
        'priority': fields.selection(hr_recruitment.AVAILABLE_PRIORITIES, 'Appreciation'),
        'salary_prop' : fields.float("Salary Proposed"),
        'salary_exp' : fields.float("Salary Expected"),
        'partner_id': fields.many2one('res.partner', 'Partner',readonly=True),
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact Name',readonly=True),
        'available' : fields.float("Availability")

    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_recruitment_report')
        cr.execute("""
            create or replace view hr_recruitment_report as (
                 select
                     min(s.id) as id,
                     date_trunc('day',s.create_date) as date,
                     date_trunc('day',s.date_closed) as date_closed,
                     to_char(s.create_date, 'YYYY') as year,
                     to_char(s.create_date, 'MM') as month,
                     to_char(s.create_date, 'YYYY-MM-DD') as day,
                     s.state,
                     s.partner_id,
                     s.company_id,
                     s.partner_address_id,
                     s.user_id,
                     s.job_id,
                     s.type_id,
                     sum(s.availability) as available,
                     s.department_id,
                     s.priority,
                     s.stage_id,
                     sum(salary_proposed) as salary_prop,
                     sum(salary_expected) as salary_exp,
                     count(*) as nbr
                 from hr_applicant s
                 group by
                     to_char(s.create_date, 'YYYY'),
                     to_char(s.create_date, 'MM'),
                     to_char(s.create_date, 'YYYY-MM-DD') ,
                     date_trunc('day',s.create_date),
                     date_trunc('day',s.date_closed),
                     s.state,
                     s.partner_id,
                     s.partner_address_id,
                     s.company_id,
                     s.user_id,
                     s.stage_id,
                     s.type_id,
                     s.priority,
                     s.job_id,
                     s.department_id
            )
        """)
hr_recruitment_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: