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
from hr_recruitment import hr_hr

class hr_recruitment_report(osv.osv):
    _name = "hr.recruitment.report"
    _description = "Recruitments Statistics"
    _inherit = "crm.case.report"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.datetime('Date', readonly=True),
        'job_id': fields.many2one('hr.job', 'Applied Job',readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]",readonly=True),
        'type_id': fields.many2one('crm.case.resource.type', 'Degree', domain="[('section_id','=',section_id),('object_id.model', '=', 'hr.applicant')]"),
        'department_id':fields.many2one('hr.department','Department',readonly=True),
        'priority': fields.selection(hr_hr.AVAILABLE_PRIORITIES, 'Appreciation'),

    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_recruitment_report')
        cr.execute("""
            create or replace view hr_recruitment_report as (
                 select
                     min(s.id) as id,
                     s.date as date,
                     to_char(s.date, 'YYYY') as name,
                     to_char(s.date, 'MM') as month,
                     s.state,
                     s.company_id,
                     s.user_id,
                     s.job_id,
                     s.type_id,
                     s.department_id,
                     s.priority,
                     s.stage_id,
                     count(*) as nbr
                 from hr_applicant s
                 group by
                     s.date,s.state,s.company_id,s.user_id,s.stage_id,s.type_id,s.priority,
                     s.job_id,s.department_id
            )
        """)
hr_recruitment_report()

