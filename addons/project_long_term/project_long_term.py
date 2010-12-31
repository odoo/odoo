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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools.translate import _
from osv import fields, osv
from resource.faces import task as Task
import operator

class project_phase(osv.osv):
    _name = "project.phase"
    _description = "Project Phase"

    def _check_recursion(self, cr, uid, ids, context=None):
         if context is None:
            context = {}

         data_phase = self.browse(cr, uid, ids[0], context=context)
         prev_ids = data_phase.previous_phase_ids
         next_ids = data_phase.next_phase_ids
         # it should neither be in prev_ids nor in next_ids
         if (data_phase in prev_ids) or (data_phase in next_ids):
             return False
         ids = [id for id in prev_ids if id in next_ids]
         # both prev_ids and next_ids must be unique
         if ids:
             return False
         # unrelated project
         prev_ids = [rec.id for rec in prev_ids]
         next_ids = [rec.id for rec in next_ids]
         # iter prev_ids
         while prev_ids:
             cr.execute('SELECT distinct prv_phase_id FROM project_phase_rel WHERE next_phase_id IN %s', (tuple(prev_ids),))
             prv_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if data_phase.id in prv_phase_ids:
                 return False
             ids = [id for id in prv_phase_ids if id in next_ids]
             if ids:
                 return False
             prev_ids = prv_phase_ids
         # iter next_ids
         while next_ids:
             cr.execute('SELECT distinct next_phase_id FROM project_phase_rel WHERE prv_phase_id IN %s', (tuple(next_ids),))
             next_phase_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
             if data_phase.id in next_phase_ids:
                 return False
             ids = [id for id in next_phase_ids if id in prev_ids]
             if ids:
                 return False
             next_ids = next_phase_ids
         return True

    def _check_dates(self, cr, uid, ids, context=None):
         for phase in self.read(cr, uid, ids, ['date_start', 'date_end'], context=context):
             if phase['date_start'] and phase['date_end'] and phase['date_start'] > phase['date_end']:
                 return False
         return True

    def _check_constraint_start(self, cr, uid, ids, context=None):
         phase = self.read(cr, uid, ids[0], ['date_start', 'constraint_date_start'], context=context)
         if phase['date_start'] and phase['constraint_date_start'] and phase['date_start'] < phase['constraint_date_start']:
             return False
         return True

    def _check_constraint_end(self, cr, uid, ids, context=None):
         phase = self.read(cr, uid, ids[0], ['date_end', 'constraint_date_end'], context=context)
         if phase['date_end'] and phase['constraint_date_end'] and phase['date_end'] > phase['constraint_date_end']:
             return False
         return True

    def _get_default_uom_id(self, cr, uid):
       model_data_obj = self.pool.get('ir.model.data')
       model_data_id = model_data_obj._get_id(cr, uid, 'product', 'uom_hour')
       return model_data_obj.read(cr, uid, [model_data_id], ['res_id'])[0]['res_id']

    def _compute(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if not ids:
            return res
        for phase in self.browse(cr, uid, ids, context=context):
            tot = 0.0
            for task in phase.task_ids:
                tot += task.planned_hours
            res[phase.id] = tot
        return res

    _columns = {
        'name': fields.char("Name", size=64, required=True),
        'date_start': fields.date('Start Date', help="It's computed according to the phases order : the start date of the 1st phase is set by you while the other start dates depend on the end date of their previous phases", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'date_end': fields.date('End Date', help=" It's computed by the scheduler according to the start date and the duration.", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'constraint_date_start': fields.date('Minimum Start Date', help='force the phase to start after this date', states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'constraint_date_end': fields.date('Deadline', help='force the phase to finish before this date', states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'project_id': fields.many2one('project.project', 'Project', required=True),
        'next_phase_ids': fields.many2many('project.phase', 'project_phase_rel', 'prv_phase_id', 'next_phase_id', 'Next Phases', states={'cancelled':[('readonly',True)]}),
        'previous_phase_ids': fields.many2many('project.phase', 'project_phase_rel', 'next_phase_id', 'prv_phase_id', 'Previous Phases', states={'cancelled':[('readonly',True)]}),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of phases."),
        'duration': fields.float('Duration', required=True, help="By default in days", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'product_uom': fields.many2one('product.uom', 'Duration UoM', required=True, help="UoM (Unit of Measure) is the unit of measurement for Duration", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'task_ids': fields.one2many('project.task', 'phase_id', "Project Tasks", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'resource_ids': fields.one2many('project.resource.allocation', 'phase_id', "Project Resources",states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'responsible_id': fields.many2one('res.users', 'Responsible', states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'state': fields.selection([('draft', 'Draft'), ('open', 'In Progress'), ('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True,
                                  help='If the phase is created the state \'Draft\'.\n If the phase is started, the state becomes \'In Progress\'.\n If review is needed the phase is in \'Pending\' state.\
                                  \n If the phase is over, the states is set to \'Done\'.'),
        'total_hours': fields.function(_compute, method=True, string='Total Hours'),
     }
    _defaults = {
        'responsible_id': lambda obj,cr,uid,context: uid,
        'state': 'draft',
        'sequence': 10,
        'product_uom': lambda self,cr,uid,c: self.pool.get('product.uom').search(cr, uid, [('name', '=', _('Day'))], context=c)[0]
    }
    _order = "project_id, date_start, sequence, name"
    _constraints = [
        (_check_recursion,'Loops in phases not allowed',['next_phase_ids', 'previous_phase_ids']),
        (_check_dates, 'Phase start-date must be lower than phase end-date.', ['date_start', 'date_end']),
    ]

    def onchange_project(self, cr, uid, ids, project, context=None):
        result = {}
        result['date_start'] = False
        project_obj = self.pool.get('project.project')
        if project:
            project_id = project_obj.browse(cr, uid, project, context=context)
            result['date_start'] = project_id.date_start
        return {'value': result}


    def _check_date_start(self, cr, uid, phase, date_end, context=None):
       """
       Check And Compute date_end of phase if change in date_start < older time.
       """
       uom_obj = self.pool.get('product.uom')
       resource_obj = self.pool.get('resource.resource')
       cal_obj = self.pool.get('resource.calendar')
       calendar_id = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
       resource_id = resource_obj.search(cr, uid, [('user_id', '=', phase.responsible_id.id)])
       if resource_id:
            res = resource_obj.read(cr, uid, resource_id, ['calendar_id'], context=context)[0]
            cal_id = res.get('calendar_id', False) and res.get('calendar_id')[0] or False
            if cal_id:
                calendar_id = cal_id
       default_uom_id = self._get_default_uom_id(cr, uid)
       avg_hours = uom_obj._compute_qty(cr, uid, phase.product_uom.id, phase.duration, default_uom_id)
       work_times = cal_obj.interval_min_get(cr, uid, calendar_id, date_end, avg_hours or 0.0, resource_id and resource_id[0] or False)
       dt_start = work_times[0][0].strftime('%Y-%m-%d')
       self.write(cr, uid, [phase.id], {'date_start': dt_start, 'date_end': date_end.strftime('%Y-%m-%d')}, context=context)

    def _check_date_end(self, cr, uid, phase, date_start, context=None):
       """
       Check And Compute date_end of phase if change in date_end > older time.
       """
       uom_obj = self.pool.get('product.uom')
       resource_obj = self.pool.get('resource.resource')
       cal_obj = self.pool.get('resource.calendar')
       calendar_id = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
       resource_id = resource_obj.search(cr, uid, [('user_id', '=', phase.responsible_id.id)], context=context)
       if resource_id:
            res = resource_obj.read(cr, uid, resource_id, ['calendar_id'], context=context)[0]
            cal_id = res.get('calendar_id', False) and res.get('calendar_id')[0] or False
            if cal_id:
                calendar_id = cal_id
       default_uom_id = self._get_default_uom_id(cr, uid)
       avg_hours = uom_obj._compute_qty(cr, uid, phase.product_uom.id, phase.duration, default_uom_id)
       work_times = cal_obj.interval_get(cr, uid, calendar_id, date_start, avg_hours or 0.0, resource_id and resource_id[0] or False)
       dt_end = work_times[-1][1].strftime('%Y-%m-%d')
       self.write(cr, uid, [phase.id], {'date_start': date_start.strftime('%Y-%m-%d'), 'date_end': dt_end}, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if not default.get('name', False):
            default['name'] = self.browse(cr, uid, id, context=context).name + _(' (copy)')
        return super(project_phase, self).copy(cr, uid, id, default, context)

    def set_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        return True

    def set_open(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'open'})
        return True

    def set_pending(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'pending'})
        return True

    def set_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True

    def set_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'done'})
        return True

    def generate_resources(self, cr, uid, ids, context=None):
        """
        Return a list of  Resource Class objects for the resources allocated to the phase.
        """
        res = {}
        resource_pool = self.pool.get('resource.resource')
        for phase in self.browse(cr, uid, ids, context=context):
            user_ids = map(lambda x:x.resource_id.user_id.id, phase.resource_ids)
            project = phase.project_id
            calendar_id  = project.resource_calendar_id and project.resource_calendar_id.id or False
            resource_objs = resource_pool.generate_resources(cr, uid, user_ids, calendar_id, context=context)
            res[phase.id] = resource_objs
        return res

    def generate_schedule(self, cr, uid, ids, start_date=False, calendar_id=False, context=None):
        """
        Schedule phase with the start date till all the next phases are completed.
        @param: start_date (datetime.datetime) : start date for the phase. It would be either Start date of phase or start date of project or system current date
        @param: calendar_id : working calendar of the project
        """
        if context is None:
            context = {}
        resource_pool = self.pool.get('resource.resource')
        data_pool = self.pool.get('ir.model.data')
        resource_allocation_pool = self.pool.get('project.resource.allocation')
        uom_pool = self.pool.get('product.uom')
        data_model, day_uom_id = data_pool.get_object_reference(cr, uid, 'product', 'uom_day')
        for phase in self.browse(cr, uid, ids, context=context):
            if not phase.responsible_id:
                raise osv.except_osv(_('No responsible person assigned !'),_("You must assign a responsible person for phase '%s' !") % (phase.name,))

            if not start_date:
                start_date = phase.project_id.date_start or phase.date_start or datetime.now().strftime("%Y-%m-%d")
                start_date = datetime.strftime((datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d") 
            phase_resource_obj = resource_pool.generate_resources(cr, uid, [phase.responsible_id.id], calendar_id, context=context)
            avg_days = uom_pool._compute_qty(cr, uid, phase.product_uom.id, phase.duration, day_uom_id)
            duration = str(avg_days) + 'd'
            # Create a new project for each phase
            def Project():
                # If project has working calendar then that
                # else the default one would be considered
                start = start_date
                minimum_time_unit = 1
                resource = phase_resource_obj
                working_hours_per_day = 24
                vacation = []
                if calendar_id:
                    working_hours_per_day = 8 #TODO: it should be come from calendars
                    vacation = tuple(resource_pool.compute_vacation(cr, uid, calendar_id))
                working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
                def phase():
                    effort = duration

            project = Task.BalancedProject(Project)

            s_date = project.phase.start.to_datetime()
            e_date = project.phase.end.to_datetime()
            # Recalculate date_start and date_end
            # according to constraints on date start and date end on phase
            if phase.constraint_date_start and str(s_date) < phase.constraint_date_start:
                start_date = datetime.strptime(phase.constraint_date_start, '%Y-%m-%d')
            else:
                start_date = s_date
            if phase.constraint_date_end and str(e_date) > phase.constraint_date_end:
                end_date= datetime.strptime(phase.constraint_date_end, '%Y-%m-%d')
                date_start = phase.constraint_date_end
            else:
                end_date = e_date
                date_start = end_date
            # Write the calculated dates back
            ctx = context.copy()
            ctx.update({'scheduler': True})
            self.write(cr, uid, [phase.id], {
                                          'date_start': start_date.strftime('%Y-%m-%d'),
                                          'date_end': end_date.strftime('%Y-%m-%d')
                                        }, context=ctx)
            # write dates into Resources Allocation
            for resource in phase.resource_ids:
                resource_allocation_pool.write(cr, uid, [resource.id], {
                                        'date_start': start_date.strftime('%Y-%m-%d'),
                                        'date_end': end_date.strftime('%Y-%m-%d')
                                    }, context=ctx)
            # Recursive call till all the next phases scheduled
            for phase in phase.next_phase_ids:
               if phase.state in ['draft', 'open', 'pending']:
                   id_cal = phase.project_id.resource_calendar_id and phase.project_id.resource_calendar_id.id or False
                   self.generate_schedule(cr, uid, [phase.id], date_start, id_cal, context=context)
               else:
                   continue
        return True

    def schedule_tasks(self, cr, uid, ids, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """
        task_pool = self.pool.get('project.task')
        resource_pool = self.pool.get('resource.resource')
        resources_list = self.generate_resources(cr, uid, ids, context=context)
        return_msg = {}
        for phase in self.browse(cr, uid, ids, context=context):
            start_date = phase.date_start
            if not start_date and phase.project_id.date_start:
                start_date = phase.project_id.date_start
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            resources = resources_list.get(phase.id, [])
            calendar_id = phase.project_id.resource_calendar_id.id
            task_ids = map(lambda x : x.id, (filter(lambda x : x.state in ['draft'] , phase.task_ids))) #reassign only task not yet started
            if task_ids:
                task_pool.generate_schedule(cr, uid, task_ids, resources, calendar_id, start_date, context=context)

            if not task_ids:
                warning_msg = _("No tasks to compute for Phase '%s'.") % (phase.name)
                if "warning" not in return_msg:
                    return_msg["warning"] =  warning_msg
                else:
                    return_msg["warning"] = return_msg["warning"] + "\n" + warning_msg
        return return_msg
project_phase()

class project_resource_allocation(osv.osv):
    _name = 'project.resource.allocation'
    _description = 'Project Resource Allocation'
    _rec_name = 'resource_id'

    def get_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for allocation in self.browse(cr, uid, ids, context=context):
            name = allocation.phase_id.name
            name += ' (%s%%)' %(allocation.useability)
            res[allocation.id] = name
        return res
    _columns = {
        'name': fields.function(get_name, method=True, type='char', size=256),
        'resource_id': fields.many2one('resource.resource', 'Resource', required=True),
        'phase_id': fields.many2one('project.phase', 'Project Phase', ondelete='cascade', required=True),
        'project_id': fields.related('phase_id', 'project_id', type='many2one', relation="project.project", string='Project', store=True),
        'user_id': fields.related('resource_id', 'user_id', type='many2one', relation="res.users", string='User'),
        'date_start': fields.date('Start Date', help="Starting Date"),
        'date_end': fields.date('End Date', help="Ending Date"),
        'useability': fields.float('Availability', help="Availability of this resource for this project phase in percentage (=50%)"),
    }
    _defaults = {
        'useability': 100,
    }

project_resource_allocation()

class project(osv.osv):
    _inherit = "project.project"
    _columns = {
        'phase_ids': fields.one2many('project.phase', 'project_id', "Project Phases"),
        'resource_calendar_id': fields.many2one('resource.calendar', 'Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close':[('readonly',True)]} ),
    }
    def generate_members(self, cr, uid, ids, context=None):
        """
        Return a list of  Resource Class objects for the resources allocated to the phase.
        """
        res = {}
        resource_pool = self.pool.get('resource.resource')
        for project in self.browse(cr, uid, ids, context=context):
            user_ids = map(lambda x:x.id, project.members)
            calendar_id  = project.resource_calendar_id and project.resource_calendar_id.id or False
            resource_objs = resource_pool.generate_resources(cr, uid, user_ids, calendar_id, context=context)
            res[project.id] = resource_objs
        return res

    def schedule_phases(self, cr, uid, ids, context=None):
        """
        Schedule the phases.
        """
        if type(ids) in (long, int,):
            ids = [ids]
        phase_pool = self.pool.get('project.phase')
        for project in self.browse(cr, uid, ids, context=context):
            phase_ids = phase_pool.search(cr, uid, [('project_id', '=', project.id),
                                                  ('state', 'in', ['draft', 'open', 'pending']),
                                                  ('previous_phase_ids', '=', False)
                                                  ])
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            start_date = False
            phase_pool.generate_schedule(cr, uid, phase_ids, start_date, calendar_id, context=context)
        return True

    def schedule_tasks(self, cr, uid, ids, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """
        if type(ids) in (long, int,):
            ids = [ids]
        user_pool = self.pool.get('res.users')
        task_pool = self.pool.get('project.task')
        resource_pool = self.pool.get('resource.resource')
        resources_list = self.generate_members(cr, uid, ids, context=context)
        return_msg = {}
        for project in self.browse(cr, uid, ids, context=context):
            start_date = project.date_start
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            resources = resources_list.get(project.id, [])
            calendar_id = project.resource_calendar_id.id
            task_ids = task_pool.search(cr, uid, [('project_id', '=', project.id),
                                              ('state', 'in', ['draft', 'open', 'pending'])
                                              ])


            if task_ids:
                task_pool.generate_schedule(cr, uid, task_ids, resources, calendar_id, start_date, context=context)
            else:
                warning_msg = _("No tasks to compute for Project '%s'.") % (project.name)
                if "warning" not in return_msg:
                    return_msg["warning"] =  warning_msg
                else:
                    return_msg["warning"] = return_msg["warning"] + "\n" + warning_msg

        return return_msg

project()

class resource_resource(osv.osv):
    _inherit = "resource.resource"
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('project_id',False):
            project_pool = self.pool.get('project.project')
            project_rec = project_pool.browse(cr, uid, context['project_id'], context=context)
            user_ids = [user_id.id for user_id in project_rec.members]
            args.append(('user_id','in',user_ids))
        return super(resource_resource, self).search(cr, uid, args, offset, limit, order, context, count)

resource_resource()

class project_task(osv.osv):
    _inherit = "project.task"
    _columns = {
        'phase_id': fields.many2one('project.phase', 'Project Phase'),
    }

    def generate_schedule(self, cr, uid, ids, resources, calendar_id, start_date, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """
        resource_pool = self.pool.get('resource.resource')
        if not ids:
            return False
        if context is None:
            context = {}
        user_pool = self.pool.get('res.users')
        project_pool = self.pool.get('project.project')
        priority_dict = {'0': 1000, '1': 800, '2': 500, '3': 300, '4': 100}
        # Create dynamic no of tasks with the resource specified
        def create_tasks(task_number, eff, priorty=500, obj=False):
            def task():
                """
                task is a dynamic method!
                """
                effort = eff
                if obj:
                    resource = obj
                priority = priorty
            task.__doc__ = "TaskNO%d" %task_number
            task.__name__ = "task%d" %task_number
            return task

        # Create a 'Faces' project with all the tasks and resources
        def Project():
            title = "Project"
            start = datetime.strftime(datetime.strptime(start_date, "%Y-%m-%d"), "%Y-%m-%d %H:%M")
            try:
                resource = reduce(operator.or_, resources)
            except:
                raise osv.except_osv(_('Error'), _('Resources should be allocated to your phases and Members should be assigned to your Project!'))
            minimum_time_unit = 1
            working_hours_per_day = 24
            vacation = []
            if calendar_id:
                working_hours_per_day = 8 #TODO: it should be come from calendars
                vacation = tuple(resource_pool.compute_vacation(cr, uid, calendar_id, context=context))
            working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
            # Dynamic creation of tasks
            task_number = 0
            for openobect_task in self.browse(cr, uid, ids, context=context):
                hours = str(openobect_task.planned_hours )+ 'H'
                if openobect_task.priority in priority_dict.keys():
                    priorty = priority_dict[openobect_task.priority]
                real_resource = False
                if openobect_task.user_id:
                    for task_resource in resources:
                        if task_resource.__name__ == task_resource:
                            real_resource = task_resource
                            break

                task = create_tasks(task_number, hours, priorty, real_resource)
                task_number += 1


        face_projects = Task.BalancedProject(Project)
        loop_no = 0
        # Write back the computed dates
        for face_project in face_projects:
            s_date = face_project.start.to_datetime()
            e_date = face_project.end.to_datetime()
            if loop_no > 0:
                ctx = context.copy()
                ctx.update({'scheduler': True})
                user_id = user_pool.search(cr, uid, [('name', '=', face_project.booked_resource[0].__name__)])
                self.write(cr, uid, [ids[loop_no-1]], {
                                                    'date_start': s_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                    'date_end': e_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                    'user_id': user_id[0]
                                                }, context=ctx)

            loop_no += 1
        return True
project_task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
