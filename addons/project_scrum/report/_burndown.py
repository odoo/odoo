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

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import pooler
from report.render import render
class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf

def compute_burndown(cr, uid, tasks_ids, date_start, date_stop):
    latest = False
    pool = pooler.get_pool(cr.dbname)
    project_task_pool = pool.get('project.task')
    task_work_pool = pool.get('project.task.work')
    if len(tasks_ids):
        tasks_ids = project_task_pool.search(cr, uid, [('id','in',tasks_ids)], order='create_date')
        tasks = project_task_pool.read(cr, uid, tasks_ids, ['create_date','planned_hours','state'])
        tasks_ids = project_task_pool.search(cr, uid, [('id','in',tasks_ids),('state', 'in', ['open','progress'])], order='create_date')
        work_ids = task_work_pool.search(cr, uid, [('task_id','in',tasks_ids)], order='date')
        close_tasks = task_work_pool.read(cr, uid, work_ids, ['date','hours','state'])        
        tasks_ids = project_task_pool.search(cr, uid, [('id','in',tasks_ids),('state', 'in', ['cancelled','done'])], order='date_end')
        close_tasks += project_task_pool.read(cr, uid, tasks_ids, ['date_end','planned_hours'])
        
    else:
        tasks = []
        close_tasks = []

    current_date = date_start
    total = 0
    done = 0
    result = []
    while datetime.strptime(current_date, '%Y-%m-%d') <= datetime.strptime(date_stop, '%Y-%m-%d'):
        while len(tasks) and tasks[0]['create_date'] and datetime.strptime(tasks[0]['create_date'][:10], '%Y-%m-%d')<=datetime.strptime(current_date, '%Y-%m-%d'):
            latest = tasks.pop(0)
            total += float(latest.get('planned_hours',0.0))
        i = 0
        while i < len(close_tasks):
            if close_tasks[i]:
                date_end = close_tasks[i].get('date',False)
                hours = float(close_tasks[i].get('hours',0.0))
                if not date_end:
                    date_end = close_tasks[i].get('date_end',False)
                    hours = float(close_tasks[i].get('planned_hours',0.0))
                if datetime.strptime(date_end[:10], '%Y-%m-%d')<=datetime.strptime(current_date, '%Y-%m-%d'):
                    t = close_tasks.pop(i)
                    done += hours
            i+=1
        result.append( (int(time.mktime(time.strptime(current_date,'%Y-%m-%d'))), total-done) )
        current_date = (datetime.strptime(current_date, '%Y-%m-%d') + relativedelta(days=1)).strftime('%Y-%m-%d')
        if not len(tasks) and not len(close_tasks):
            break
    result.append( (int(time.mktime(time.strptime(date_stop,'%Y-%m-%d'))), 0) )
    return result



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

