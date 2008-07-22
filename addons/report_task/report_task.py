##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

class  report_task_user_pipeline_open (osv.osv):
    _name = "report.task.user.pipeline.open"
    _description = "Tasks by user and project"
    _auto = False
    _columns = {
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'task_nbr': fields.float('Task Number', readonly=True),
        'task_hrs': fields.float('Task Hours', readonly=True),
        'task_progress': fields.float('Task Progress', readonly=True),
        'company_id' : fields.many2one('res.company', 'Company'),
        'task_state': fields.selection([('draft', 'Draft'),('open', 'Open'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done'),('no','No Task')], 'State', readonly=True),
    }

    def init(self, cr):
        cr.execute('''
            create or replace view report_task_user_pipeline_open as (
                select
                    u.id as id,
                    u.id as user_id,
                    u.company_id as company_id,
                    count(t.*) as task_nbr,
                    sum(t.planned_hours) as task_hrs,
                    sum(t.planned_hours * (100 - t.progress) / 100) as task_progress,
                    case when t.state is null then 'no' else t.state end as task_state
                from
                    res_users u
                left join 
                    project_task t on (u.id = t.user_id)
                where
                    u.active
                group by
                    u.id, u.company_id, t.state
            )
        ''')
report_task_user_pipeline_open()


