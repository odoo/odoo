# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from lxml import etree
import mx.DateTime
import time
from tools.translate import _
from osv import fields, osv


class project_phase(osv.osv):
    _name = "project.phase"
    _description = "Project Phase"



    def _check_recursion(self,cr,uid,ids):
         obj_self = self.browse(cr, uid, ids[0])
         prev_ids = obj_self.previous_phase_ids
         next_ids = obj_self.next_phase_ids
         #it should nither be in prev_ids nor in next_ids
         if (obj_self in prev_ids) or (obj_self in next_ids):
             return False
         ids = [id for id in prev_ids if id in next_ids]

         #both prev_ids and next_ids must be unique
         if ids:
             return False
         #unrelated project

         prev_ids = [rec.id for rec in prev_ids]
         next_ids = [rec.id for rec in next_ids]

         #iter prev_ids
         while prev_ids:
             cr.execute('select distinct prv_phase_id from project_phase_previous_rel where phase_id in ('+','.join(map(str, prev_ids))+')')
             prv_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if obj_self.id in prv_phase_ids:
                 return False
             ids = [id for id in prv_phase_ids if id in next_ids]
             if ids:
                 return False
             prev_ids = prv_phase_ids

        #iter next_ids
         while next_ids:
             cr.execute('select distinct next_phase_id from project_phase_next_rel where phase_id in ('+','.join(map(str, next_ids))+')')
             next_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if obj_self.id in next_phase_ids:
                 return False
             ids = [id for id in next_phase_ids if id in prev_ids]
             if ids:
                 return False
             next_ids = next_phase_ids
         return True


    _columns = {
        'name': fields.char("Phase Name", size=64, required=True),
        'date_start': fields.datetime('Starting Date'),
        'date_end': fields.datetime('End Date'),
        'constraint_date_start': fields.datetime('Constraint Starting Date'),
        'constraint_date_end': fields.datetime('Constraint End Date'),
        'project_id': fields.many2one('project.project', 'Project', required=True),
        'next_phase_ids': fields.many2many('project.phase', 'project_phase_next_rel', 'phase_id', 'next_phase_id', 'Next Phases'),
        'previous_phase_ids': fields.many2many('project.phase', 'project_phase_previous_rel', 'phase_id', 'prv_phase_id', 'Previous Phases'),
        'duration': fields.float('Duration'),
        'product_uom': fields.many2one('product.uom', 'Duration UoM', help="UoM (Unit of Measure) is the unit of measurement for Duration"),
        'task_ids': fields.one2many('project.task', 'phase_id', "Project Tasks"),
        'resource_ids': fields.one2many('project.resource.allocation', 'phase_id', "Project Resources"),
     }

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-%m-%d'),
    }

    _order = "name"
    _constraints = [
        (_check_recursion,'Error ! Loops In Phases Not Allowed',['next_phase_ids','previous_phase_ids'])
    ]

    def timeformat_convert(self,cr, uid, time_string, context={}):
        # To Convert input time string:: 8.5 to output time string 8:30
        split_list = str(time_string).split('.')
        hour_part = split_list[0]
        mins_part = split_list[1]
        round_mins  = int(round(float(mins_part) * 60,-2))
        converted_string = hour_part + ':' + str(round_mins)[0:2]
        return converted_string

    def compute_hours(self,cr,uid,calendar_id,context = None):
        #  To compute average hours of the working calendar

        resource_week_pool = self.pool.get('resource.calendar.week')
        week_ids = resource_week_pool.search(cr,uid,[('calendar_id','=',calendar_id)])
        week_obj = resource_week_pool.read(cr,uid,week_ids,['dayofweek','hour_from','hour_to'])
        hours = []
        hr = 0
        wk_days = []
        for week in week_obj:
            if week['dayofweek'] not in wk_days:
                wk_days.append(week['dayofweek'])
            hour_from_str = self.timeformat_convert(cr,uid,week['hour_from'])
            hour_to_str = self.timeformat_convert(cr,uid,week['hour_to'])
            hours.append(week['hour_from'])
            hours.append(week['hour_to'])

        for hour in range(len(hours)):
                if hour%2 ==0:
                    hr += float(hours[hour+1]) - float(hours[hour])
        return hr/len(wk_days)

    def constraint_date_start(self,cr,uid,phase,date_end,context=None):
       # Recursive call for all previous phases if change in date_start < older time

       resource_cal_pool = self.pool.get('resource.calendar')
       calendar_id = phase.project_id.resource_calendar_id.id
       avg_hours = self.compute_hours(cr,uid,calendar_id)
       hours = phase.duration * avg_hours
       work_time = resource_cal_pool.interval_min_get(cr, uid, calendar_id or False, date_end, hours or 0.0)
       dt_start = work_time[0][0].strftime('%Y-%m-%d %H:%M:%S')
       self.write(cr,uid,[phase.id],{'date_start':dt_start,'date_end':date_end.strftime('%Y-%m-%d %H:%M:%S')})

    def constraint_date_end(self,cr,uid,phase,date_start,context=None):
       # Recursive call for all next phases if change in date_end > older time

       resource_cal_pool = self.pool.get('resource.calendar')
       calendar_id = phase.project_id.resource_calendar_id.id
       avg_hours = self.compute_hours(cr,uid,calendar_id)
       hours = phase.duration * avg_hours
       work_time = resource_cal_pool.interval_get(cr, uid, calendar_id or False, date_start, hours or 0.0)
       dt_end = work_time[-1][1].strftime('%Y-%m-%d %H:%M:%S')
       self.write(cr,uid,[phase.id],{'date_start':date_start.strftime('%Y-%m-%d %H:%M:%S'),'date_end':dt_end})

    def write(self, cr, uid, ids, vals,context=None):
        phase = self.browse(cr,uid,ids[0])
        resource_cal_pool = self.pool.get('resource.calendar')
        calendar_id = phase.project_id.resource_calendar_id.id
        avg_hours = self.compute_hours(cr,uid,calendar_id)

        if not context:
            context = {}
# write method changes the date_start and date_end
#for previous and next phases respectively based on valid condition

        if vals.get('date_start'):
            if vals['date_start'] < phase.date_start:
                dt_start = mx.DateTime.strptime(vals['date_start'],'%Y-%m-%d %H:%M:%S')
                hrs = phase.duration * avg_hours
                work_times = resource_cal_pool.interval_get(cr, uid, calendar_id or False, dt_start, hrs or 0.0)
                vals['date_end'] = work_times[-1][1].strftime('%Y-%m-%d %H:%M:%S')
                super(project_phase, self).write(cr, uid, ids, vals, context=context)

                for prv_phase in phase.previous_phase_ids:
                   self.constraint_date_start(cr,uid,prv_phase,dt_start)

        if vals.get('date_end'):
            if vals['date_end'] > phase.date_end:
                dt_end = mx.DateTime.strptime(vals['date_end'],'%Y-%m-%d %H:%M:%S')
                hrs = phase.duration * avg_hours
                work_times = resource_cal_pool.interval_min_get(cr, uid, calendar_id or False, dt_end, hrs or 0.0)
                vals['date_start'] = work_times[0][0].strftime('%Y-%m-%d %H:%M:%S')
                super(project_phase, self).write(cr, uid, ids, vals, context=context)

                for next_phase in phase.next_phase_ids:
                   self.constraint_date_end(cr,uid,next_phase,dt_end)
        return super(project_phase, self).write(cr, uid, ids, vals, context=context)

project_phase()

class project_resource_allocation(osv.osv):
    _name = 'project.resource.allocation'
    _description = 'Project Resource Allocation'
    _rec_name = 'resource_id'
    _columns = {
        'resource_id': fields.many2one('resource.resource', 'Resource', required=True),
        'phase_id': fields.many2one('project.phase', 'Project Phase', required=True),
        'useability': fields.float('Useability', help="Useability of this ressource for this project phase in percentage (=50%)"),
    }
    _defaults = {
        'useability': lambda *a: 100,
    }

project_resource_allocation()

class project(osv.osv):
    _inherit = "project.project"

    _columns = {
        'phase_ids': fields.one2many('project.phase', 'project_id', "Project Phases")
    }

project()

class task(osv.osv):
    _inherit = "project.task"

    _columns = {
        'phase_id': fields.many2one('project.phase', 'Project Phase')
    }
task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

