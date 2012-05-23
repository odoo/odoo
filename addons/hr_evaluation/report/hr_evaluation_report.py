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

class hr_evaluation_report(osv.osv):
    _name = "hr.evaluation.report"
    _description = "Evaluations Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'create_date': fields.date('Create Date', readonly=True),
        'delay_date':fields.float('Delay to Start', digits=(16,2),readonly=True),
        'overpass_delay':fields.float('Overpassed Deadline', digits=(16,2), readonly=True),
        'progress_bar' : fields.float("Progress"),
        'day': fields.char('Day', size=128, readonly=True),
        'deadline': fields.date("Deadline", readonly=True),
        'request_id': fields.many2one('survey.request', 'Request_id', readonly=True),
        'closed': fields.date("closed", readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'plan_id': fields.many2one('hr_evaluation.plan', 'Plan', readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee", readonly=True),
        'rating': fields.selection([
            ('0','Significantly bellow expectations'),
            ('1','Did not meet expectations'),
            ('2','Meet expectations'),
            ('3','Exceeds expectations'),
            ('4','Significantly exceeds expectations'),
        ], "Overall Rating", readonly=True),
        'nbr':fields.integer('# of Requests', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('wait','Plan In Progress'),
            ('progress','Final Validation'),
            ('done','Done'),
            ('cancel','Cancelled'),
        ], 'Status',readonly=True),
    }
    _order = 'create_date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_evaluation_report')
        cr.execute("""
            create or replace view hr_evaluation_report as (
                 select
                     min(l.id) as id,
                     date_trunc('day',s.create_date) as create_date,
                     to_char(s.create_date, 'YYYY-MM-DD') as day,
                     s.employee_id,
                     l.request_id,
                     s.plan_id,
                     s.rating,
                     s.date as deadline,
                     s.date_close as closed,
                     to_char(s.create_date, 'YYYY') as year,
                     to_char(s.create_date, 'MM') as month,
                     count(l.*) as nbr,
                     s.state,
                     s.progress as progress_bar,
                     avg(extract('epoch' from age(s.create_date,CURRENT_DATE)))/(3600*24) as  delay_date,
                     avg(extract('epoch' from age(s.date,CURRENT_DATE)))/(3600*24) as overpass_delay
                     from
                 hr_evaluation_interview l
                LEFT JOIN
                     hr_evaluation_evaluation s on (s.id=l.evaluation_id)
                 GROUP BY
                     s.create_date,
                     date_trunc('day',s.create_date),
                     to_char(s.create_date, 'YYYY-MM-DD'),
                     to_char(s.create_date, 'YYYY'),
                     to_char(s.create_date, 'MM'),
                     s.state,
                     s.employee_id,
                     s.date,
                     s.date_close,
                     l.request_id,
                     s.rating,
                     s.progress,
                     s.plan_id
            )
        """)

hr_evaluation_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

