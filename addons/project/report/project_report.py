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
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'date_start': fields.datetime('Starting Date',readonly=True),
        'date_end': fields.datetime('Ending Date',readonly=True),
        'date_deadline': fields.date('Deadline',readonly=True),
        'project_id':fields.many2one('project.project', 'Project', readonly=True),
        'hours_planned': fields.float('Planned Hours', readonly=True),
        'hours_effective': fields.float('Effective Hours', readonly=True),
        'hours_delay': fields.float('Avg. Plan.-Eff.', readonly=True),
        'closing_days': fields.char('Avg Closing Delay', size=64, readonly=True),
        'nbr': fields.integer('#Number of tasks', readonly=True),
        'priority' : fields.selection([('4','Very Low'),
                                       ('3','Low'),
                                       ('2','Medium'),
                                       ('1','Urgent'),
                                       ('0','Very urgent')],
                                       'Importance',readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'state': fields.selection([
               ('draft', 'Draft'),
               ('open', 'In Progress'),
               ('pending', 'Pending'),
               ('cancelled', 'Cancelled'),
               ('done', 'Done')],
            'State', readonly=True),
        'company_id': fields.many2one('res.company', 'Company',readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner',readonly=True),
        'type': fields.many2one('project.task.type', 'Stage',readonly=True),



    }
    _order = 'name desc, project_id'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_project_task_user')
        cr.execute("""
            create or replace view report_project_task_user as (
                select
                    min(t.id) as id,
                    to_char(date_start, 'YYYY') as name,
                    to_char(date_start, 'MM') as month,
                    count(distinct t.id) as nbr,
                    date_trunc('day',t.date_start) as date_start,
                    date_trunc('day',t.date_end) as date_end,
                    to_date(to_char(t.date_deadline, 'dd-MM-YYYY'),'dd-MM-YYYY') as date_deadline,
                    t.user_id,
                    t.project_id,
                    t.state,
                    t.priority,
                    t.company_id,
                    t.partner_id,
                    t.type,
                    sum(planned_hours) as hours_planned,
                    to_char(avg(date_end::abstime-t.create_date::timestamp), 'DD"d" HH24:MI:SS') as closing_days,
                    sum(w.hours) as hours_effective,
                    ((sum(planned_hours)-sum(w.hours))/count(distinct t.id))::decimal(16,2) as hours_delay
                from project_task t
                    left join project_task_work w on (t.id=w.task_id)
                group by
                    to_char(date_start, 'YYYY'),
                    to_char(date_start, 'MM'),
                    t.priority,
                    t.user_id,
                    t.state,
                    t.date_end,
                    to_date(to_char(t.date_deadline, 'dd-MM-YYYY'),'dd-MM-YYYY'),
                    t.date_start,
                    t.company_id,
                    t.partner_id,
                    t.type,
                    t.project_id
            )
        """)
report_project_task_user()

#This class is generated for project deshboard purpose
class project_vs_remaining_hours(osv.osv):
    _name = "project.vs.remaining.hours"
    _description = " Project vs Remaining hours"
    _auto = False
    _columns = {
        'project': fields.char('Project', size=128, required=True),
        'remaining_hours': fields.float('Remaining Hours', readonly=True),
        'state': fields.selection([('draft','Draft'),('open','Open'), ('pending','Pending'),('cancelled', 'Cancelled'),('close','Close'),('template', 'Template')], 'State', required=True,readonly=True)
    }
    _order = 'project desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'project_vs_remaining_hours')
        cr.execute("""
            create or replace view project_vs_remaining_hours as (
                   select
                       min(pt.id) as id,
                       a.name as project,
                       sum(pt.remaining_hours) as remaining_hours,
                       a.state
                    from
                         project_task as pt,
                         project_project as p,
                         account_analytic_account as a
                    where
                        pt.project_id=p.id and
                        p.category_id = a.id
                    group by
                        a.name,a.state
            )
        """)
project_vs_remaining_hours()

class task_by_days(osv.osv):
    _name = "task.by.days"
    _description = "Task By Days"
    _auto = False
    _columns = {
        'day': fields.char('Day', size=128, required=True),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True),
        'total_task': fields.float('Total tasks', readonly=True)
     }
    _order = 'day desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'task_by_days')
        cr.execute("""
            create or replace view task_by_days as (
                select
                    min(pt.id) as id,
                    to_char(pt.create_date, 'YYYY-MM-DD') as day,
                    count(*) as total_task,
                    pt.state as state
                from
                    project_task as pt
                group by
                    to_char(pt.create_date, 'YYYY-MM-DD'),pt.state
            )
        """)
task_by_days()

class task_by_days_vs_planned_hours(osv.osv):
    _name = "task.by.days.vs.planned.hours"
    _description = "Task By Days vs Planned Hours"
    _auto = False
    _columns = {
        'day': fields.char('Day', size=128, required=True),
        'planned_hour': fields.float('Planned Hours', readonly=True)
     }
    _order = 'day desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'task_by_days_vs_planned_hours')
        cr.execute("""
            create or replace view task_by_days_vs_planned_hours as (
                select
                    min(pt.id) as id,
                    to_char(pt.create_date, 'YYYY-MM-DD') as day,
                    sum(planned_hours) as planned_hour
                from
                    project_task as pt
                group by
                    to_char(pt.create_date, 'YYYY-MM-DD')
            )
        """)
task_by_days_vs_planned_hours()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

