##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: project.py 1005 2005-07-25 08:41:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
                    substring(date_close for 7)||'-01' as name,
                    count(distinct t.id) as task_closed,
                    t.user_id,
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
                    substring(date_close for 7),t.user_id,project_id
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
                    substring(date_close for 7)||'-01' as name,
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
                    substring(date_close for 7),project_id
            )
        """)
report_project_task()




