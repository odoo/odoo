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


from mx import DateTime
import time

def compute_burndown(cr, uid, tasks_id, date_start, date_stop):
    latest = False
    if tasks_id:
        cr.execute('select id,create_date,state,planned_hours from project_task where id in %s order by create_date', (tuple(tasks_id),))
        tasks = cr.fetchall()

        cr.execute('select w.date,w.hours from project_task_work w left join project_task t on (t.id=w.task_id) where t.id in %s and t.state in (\'open\',\'progress\') order by date', (tuple(tasks_id),))

        tasks2 = cr.fetchall()

        cr.execute('select date_close,planned_hours from project_task where id in %s and state in (\'cancelled\',\'done\') order by date_close', (tuple(tasks_id),))
        tasks2 += cr.fetchall()
        tasks2.sort()
    else:
        tasks = []
        tasks2 = []

    current_date = date_start
    total = 0
    done = 0
    result = []
    while current_date<=date_stop:
        while len(tasks) and tasks[0][1] and tasks[0][1][:10]<=current_date:
            latest = tasks.pop(0)
            total += latest[3]
        i = 0
        while i<len(tasks2):
            if tasks2[i][0] and tasks2[i][0][:10]<=current_date:
                t = tasks2.pop(i)
                done += t[1]
            else:
                i+=1
        result.append( (int(time.mktime(time.strptime(current_date,'%Y-%m-%d'))), total-done) )
        current_date = (DateTime.strptime(current_date, '%Y-%m-%d') + DateTime.RelativeDateTime(days=1)).strftime('%Y-%m-%d')
        if not len(tasks) and not len(tasks2):
            break
    result.append( (int(time.mktime(time.strptime(date_stop,'%Y-%m-%d'))), 0) )
    return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
