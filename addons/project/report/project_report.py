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

from osv import fields,osv
import tools

class report_project_task_user(osv.osv):
    _name = "report.project.task.user"
    _description = "Tasks by user and project"
    _auto = False
    _columns = {
        'name': fields.char('Task Summary', size=128, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'year': fields.char('Year', size=64, required=False, readonly=True),
        'user_id': fields.many2one('res.users', 'Assigned To', readonly=True),
        'date_start': fields.date('Starting Date',readonly=True),
        'no_of_days': fields.integer('# of Days', size=128, readonly=True),
        'date_end': fields.date('Ending Date', readonly=True),
        'date_deadline': fields.date('Deadline', readonly=True),
        'project_id': fields.many2one('project.project', 'Project', readonly=True),
        'hours_planned': fields.float('Planned Hours', readonly=True),
        'hours_effective': fields.float('Effective Hours', readonly=True),
        'hours_delay': fields.float('Avg. Plan.-Eff.', readonly=True),
        'remaining_hours': fields.float('Remaining Hours', readonly=True),
        'progress': fields.float('Progress', readonly=True, group_operator='avg'),
        'total_hours': fields.float('Total Hours', readonly=True),
        'closing_days': fields.float('Days to Close', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the task"),
        'opening_days': fields.float('Days to Open', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to Open the task"),
        'delay_endings_days': fields.float('Overpassed Deadline', digits=(16,2), readonly=True),
        'nbr': fields.integer('# of tasks', readonly=True),
        'priority' : fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Urgent'),
('0','Very urgent')], 'Priority', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('open', 'In Progress'), ('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')],'State', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True, groups="base.group_multi_company"),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'type_id': fields.many2one('project.task.type', 'Stage', readonly=True),
    }
    _order = 'name desc, project_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_project_task_user')
        cr.execute("""
            CREATE view report_project_task_user as
              SELECT
                    (select 1 ) AS nbr,
                    t.id as id,
                    to_char(date_start, 'YYYY') as year,
                    to_char(date_start, 'MM') as month,
                    to_char(date_start, 'YYYY-MM-DD') as day,
                    date_trunc('day',t.date_start) as date_start,
                    date_trunc('day',t.date_end) as date_end,
                    to_date(to_char(t.date_deadline, 'dd-MM-YYYY'),'dd-MM-YYYY') as date_deadline,
--                    sum(cast(to_char(date_trunc('day',t.date_end) - date_trunc('day',t.date_start),'DD') as int)) as no_of_days,
                    abs((extract('epoch' from (t.date_end-t.date_start)))/(3600*24))  as no_of_days,
                    t.user_id,
                    progress as progress,
                    t.project_id,
                    t.state,
                    t.effective_hours as hours_effective,
                    t.priority,
                    t.name as name,
                    t.company_id,
                    t.partner_id,
                    t.type_id,
                    remaining_hours as remaining_hours,
                    total_hours as total_hours,
                    t.delay_hours as hours_delay,
                    planned_hours as hours_planned,
                    (extract('epoch' from (t.date_end-t.create_date)))/(3600*24)  as closing_days,
                    (extract('epoch' from (t.date_start-t.create_date)))/(3600*24)  as opening_days,
                    abs((extract('epoch' from (t.date_deadline-t.date_end)))/(3600*24))  as delay_endings_days
              FROM project_task t

                GROUP BY
                    t.id,
                    remaining_hours,
                    t.effective_hours,
                    progress,
                    total_hours,
                    planned_hours,
                    hours_delay,
                    year,
                    month,
                    day,
                    create_date,
                    date_start,
                    date_end,
                    date_deadline,
                    t.user_id,
                    t.project_id,
                    t.state,
                    t.priority,
                    name,
                    t.company_id,
                    t.partner_id,
                    t.type_id

        """)

report_project_task_user()

#This class is generated for project deshboard purpose
class project_vs_hours(osv.osv):
    _name = "project.vs.hours"
    _description = " Project vs  hours"
    _auto = False
    _columns = {
        'project': fields.char('Project', size=128, required=True),
        'remaining_hours': fields.float('Remaining Hours', readonly=True),
        'user_id': fields.many2one('res.users', 'Assigned To', readonly=True),
        'planned_hours': fields.float('Planned Hours', readonly=True),
        'total_hours': fields.float('Total Hours', readonly=True),
        'state': fields.selection([('draft','Draft'),('open','Open'), ('pending','Pending'),('cancelled', 'Cancelled'),('close','Close'),('template', 'Template')], 'State', required=True, readonly=True)
    }
    _order = 'project desc'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'project_vs_hours')
        cr.execute("""
            CREATE or REPLACE view project_vs_hours as (
                select
                      min(pt.id) as id,
                      aaa.user_id as user_id,
                      aaa.name as project,
                      aaa.state,
                      sum(pt.remaining_hours) as remaining_hours,
                      sum(pt.planned_hours) as planned_hours,
                      sum(pt.total_hours) as total_hours
                 FROM project_project as pp,
                       account_analytic_account as aaa,
                       project_task as pt
                 WHERE aaa.id=pp.analytic_account_id and pt.project_id=pp.id and pp.analytic_account_id=aaa.id
                 GROUP BY aaa.user_id,aaa.state,aaa.name
                 UNION All
                 SELECT
                      min(pt.id) as id,
                      pur.uid as user_id,
                      aaa.name as project,
                      aaa.state,
                      sum(pt.remaining_hours) as remaining_hours,
                      sum(pt.planned_hours) as planned_hours,
                      sum(pt.total_hours) as total_hours
                 FROM project_project as pp,
                      project_user_rel as pur,
                      account_analytic_account as aaa,
                      project_task as pt
                 WHERE pur.project_id=pp.id and pt.project_id=pp.id and pp.analytic_account_id=aaa.id AND pur.uid != aaa.user_id
                 GROUP BY pur.uid,aaa.state,aaa.name
            )
        """)

project_vs_hours()

class task_by_days(osv.osv):
    _name = "task.by.days"
    _description = "Task By Days"
    _auto = False
    _columns = {
        'day': fields.char('Day', size=128, required=True),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True),
        'total_task': fields.float('Total tasks', readonly=True),
        'project_id':fields.many2one('project.project', 'Project')
     }
    _order = 'day desc'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'task_by_days')
        cr.execute("""
            CREATE or REPLACE view task_by_days as (
                SELECT
                    min(pt.id) as id,
                    to_char(pt.create_date, 'YYYY-MM-DD') as day,
                    count(*) as total_task,
                    pt.state as state,
                    pt.project_id
                FROM
                    project_task as pt
                GROUP BY
                    to_char(pt.create_date, 'YYYY-MM-DD'),pt.state,pt.project_id
            )
        """)

task_by_days()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

