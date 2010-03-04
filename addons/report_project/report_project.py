# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv

class report_project_task_user(osv.osv):
    _name = "report.project.task.user"
    _description = "Tasks by user and project"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'project_id':fields.many2one('project.project', 'Project', readonly=True),
        'hours_planned': fields.float('Planned Hours', readonly=True),
        'hours_effective': fields.float('Effective Hours', readonly=True),
        'hours_delay': fields.float('Avg. Plan.-Eff.', readonly=True),
        'closing_days': fields.char('Avg Closing Delay', size=64, readonly=True),
        'task_closed': fields.integer('Task Closed', readonly=True),
    }
    _order = 'name desc, project_id'
    def init(self, cr):
        cr.execute("""
            create or replace view report_project_task_user as (
                select
                    min(t.id) as id,
                    to_char(date_close, 'YYYY-MM-01') as name,
                    count(distinct t.id) as task_closed,
                    t.user_id,
                    t.project_id,
                    sum(planned_hours) as hours_planned,
                    to_char(avg(date_close::abstime-t.create_date::timestamp), 'DD"d" HH24:MI:SS') as closing_days,
                    sum(w.hours) as hours_effective,
                    ((sum(planned_hours)-sum(w.hours))/count(distinct t.id))::decimal(16,2) as hours_delay
                from project_task t
                    left join project_task_work w on (t.id=w.task_id)
                where
                    t.state='done'
                group by
                    to_char(date_close, 'YYYY-MM-01'),t.user_id,project_id
            )
        """)
report_project_task_user()


class report_project_task(osv.osv):
    _name = "report.project.task"
    _description = "Tasks by project"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'project_id':fields.many2one('project.project', 'Project', readonly=True),
        'hours_planned': fields.float('Planned Hours', readonly=True),
        'hours_effective': fields.float('Effective Hours', readonly=True),
        'hours_delay': fields.float('Avg. Plan.-Eff.', readonly=True),
        'closing_days': fields.char('Avg Closing Delay', size=64, readonly=True),
        'task_closed': fields.integer('Task Closed', readonly=True),
    }
    _order = 'name desc, project_id'
    def init(self, cr):
        cr.execute("""
            create or replace view report_project_task as (
                select
                    min(t.id) as id,
                    to_char(date_close, 'YYYY-MM-01') as name,
                    count(distinct t.id) as task_closed,
                    t.project_id,
                    sum(planned_hours) as hours_planned,
                    to_char(avg(date_close::abstime-t.create_date::timestamp), 'DD"d" HH12:MI:SS') as closing_days,
                    sum(w.hours) as hours_effective,
                    ((sum(planned_hours)-sum(w.hours))/count(distinct t.id))::decimal(16,2) as hours_delay
                from project_task t
                    left join project_task_work w on (t.id=w.task_id)
                where
                    t.state='done'
                group by
                    to_char(date_close, 'YYYY-MM-01'),project_id
            )
        """)
report_project_task()





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

