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
        'task_state': fields.selection([('draft', 'Draft'),('open', 'Open'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done'),('no','No Task')], 'Status', readonly=True),
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

class  report_closed_task(osv.osv):
    _name = "report.closed.task"
    _description = "Closed Task Report"
    _auto = False
    _columns = {
        'sequence': fields.integer('Sequence', readonly=True),
        'name': fields.char('Task summary', size=128, readonly=True),
        'project_id': fields.many2one('project.project', 'Project', readonly=True),
        'user_id': fields.many2one('res.users', 'Assigned to', readonly=True),
        'date_deadline': fields.datetime('Deadline', readonly=True),
        'planned_hours': fields.float('Planned Hours', readonly=True),
        'delay_hours': fields.float('Delay Hours', readonly=True),
        'progress': fields.float('Progress (%)', readonly=True),
        'priority' : fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Urgent'), ('0','Very urgent')], 'Importance', readonly=True),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'Status', readonly=True),
        'remaining_hours': fields.float('Remaining Hours', readonly=True),
        'date_close' : fields.datetime('Date Closed', readonly=True)
    }

    def init(self, cr):
        cr.execute('''
            create or replace view report_closed_task as (
                select
                   tsk.id as id, tsk.sequence as sequence, tsk.name as name,
                   tsk.project_id as project_id, tsk.user_id as user_id,
                   tsk.date_deadline as date_deadline, tsk.planned_hours as planned_hours,
                   tsk.delay_hours as delay_hours, tsk.progress as progress,
                   tsk.priority as priority, tsk.state as state,
                   tsk.remaining_hours as remaining_hours, tsk.date_close as date_close
                from
                    project_task tsk
                where
                    (tsk.date_close < CURRENT_DATE AND tsk.date_close >= (CURRENT_DATE-15))
            )
        ''')
report_closed_task()

#class report_timesheet_task(osv.osv):
#    _name = "report.timesheet.task"
#    _description = "Report on Timesheets and Tasks per User Per Month"
#    _auto = False
#   
#    def get_hrs_timesheet(self, cr, uid, ids, name,args,context):
#        result = {}
#        
#        for record in self.browse(cr, uid, ids, context):
#            last_date = mx.DateTime.strptime(record.month, '%Y-%m-%d') + mx.DateTime.RelativeDateTime(months=1) - 1
#            obj=self.pool.get('hr_timesheet_sheet.sheet')
#            sheet_ids = obj.search(cr,uid,[('user_id','=',record.user_id.id),('date_current','>=',record.month),('date_current','<=',last_date.strftime('%Y-%m-%d'))])
#            data_days = obj.read(cr,uid,sheet_ids,['total_attendance_day','date_current','user_id'])
#            total = 0.0
#            for day_attendance in data_days:
#                total += day_attendance['total_attendance_day']
#            result[record.id] = total
#        
#        return result
#        
#    _columns = {
#        'month': fields.date('Month', required=True,readonly=True),
#        'user_id': fields.many2one('res.users', 'User' ,readonly=True, required=True),
#        'timesheet_hrs': fields.function(get_hrs_timesheet,method=True, string="Timesheet Hrs" ),
#        'task_hrs': fields.float('Task Hrs', readonly=True, required=True),
#      }
#    
#    
#    def init(self, cr): 
#        cr.execute("""create or replace view report_timesheet_task as (
#         select min(p.id) as id, to_char(p.date, 'YYYY-MM-01') as  month, min(r.id) as user_id, sum(p.hours) as task_hrs,0.0 as timesheet_hrs 
#        from project_task_work p,res_users r 
#        where (r.id=p.user_id) 
#        group by  to_char(p.date, 'YYYY-MM-01'))""")
#        
#        
#
#report_timesheet_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

