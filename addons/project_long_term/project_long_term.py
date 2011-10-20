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
from tools.translate import _
from osv import fields, osv
from resource.faces import task as Task 
from operator import itemgetter

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
        'date_start': fields.date('Start Date', help="It's computed by the scheduler according the project date or the end date of the previous phase.", states={'done':[('readonly',True)], 'cancelled':[('readonly',True)]}),
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
        'state': fields.selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True,
                                  help='If the phase is created the state \'Draft\'.\n If the phase is started, the state becomes \'In Progress\'.\n If review is needed the phase is in \'Pending\' state.\
                                  \n If the phase is over, the states is set to \'Done\'.'),
        'total_hours': fields.function(_compute, string='Total Hours'),
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

    def generate_phase(self, cr, uid, ids, f, parent=False, context=None):
        if context is None:
            context = {}
        phase_ids = []
        data_pool = self.pool.get('ir.model.data')
        uom_pool = self.pool.get('product.uom')
        task_pool = self.pool.get('project.task')
        data_model, day_uom_id = data_pool.get_object_reference(cr, uid, 'product', 'uom_day')
        for phase in self.browse(cr, uid, ids, context=context):
            avg_days = uom_pool._compute_qty(cr, uid, phase.product_uom.id, phase.duration, day_uom_id)
            duration = str(avg_days) + 'd'
            # Create a new project for each phase
            str_resource = ('%s & '*len(phase.resource_ids))[:-2]
            str_vals = str_resource % tuple(map(lambda x: 'Resource_%s'%x.resource_id.id, phase.resource_ids))

            # Phases Defination for the Project
            s = '''
    def Phase_%s():
        title = \"%s\"
        effort = \'%s\'
        resource = %s
'''%(phase.id, phase.name, duration, str_vals or False)

            # Recalculate date_start and date_end
            # according to constraints on date start and date end on phase
            start_date = ''
            end_date = ''
            if phase.constraint_date_start:
                start_date = datetime.strptime(phase.constraint_date_start, '%Y-%m-%d')
                s += '''
        start = \"%s\"
'''%(datetime.strftime(start_date, "%Y-%m-%d"))
            else:
                if parent:
                    start = 'up.Phase_%s.end' % (parent.id)
                    s += '''
        start = %s
'''%(start)
                else:
                    start = phase.project_id.date_start or phase.date_start
                    s += '''
        start = \"%s\"
'''%(start)                
                
            if phase.constraint_date_end :
                end_date= datetime.strptime(phase.constraint_date_end, '%Y-%m-%d')
                s += '''
        end = \"%s\"
'''%(datetime.strftime(end_date, "%Y-%m-%d"))               


                #start = datetime.strftime((datetime.strptime(start, "%Y-%m-%d")), "%Y-%m-%d")

            phase_ids.append(phase.id)
            parent = False
            task_ids = []
            todo_task_ids = task_pool.search(cr, uid, [('id', 'in', map(lambda x : x.id, phase.task_ids)),
                                              ('state', 'in', ['draft', 'open', 'pending'])
                                              ], order='sequence')
            if todo_task_ids :
                for task in task_pool.browse(cr, uid, todo_task_ids, context=context):
                    s += task_pool.generate_task(cr, uid, task.id, parent=parent, flag=False, context=context)
                    if not parent:
                        parent = task
                    task_ids.append(task.id)
            
            f += s + '\n'
            # Recursive call till all the next phases scheduled
            for next_phase in phase.next_phase_ids:
                if next_phase.state in ['draft', 'open', 'pending']:
                    rf, rphase_ids = self.generate_phase(cr, uid, [next_phase.id], f = '', parent=phase, context=context)
                    f += rf +'\n'
                    phase_ids += rphase_ids
                else:   
                    continue
        return f, phase_ids

    def schedule_tasks(self, cr, uid, ids, context=None):
        """
        Schedule tasks base on faces lib
        """
        if context is None:
            context = {}
        if type(ids) in (long, int,):
            ids = [ids]
        task_pool = self.pool.get('project.task')
        resource_pool = self.pool.get('resource.resource')
        for phase in self.browse(cr, uid, ids, context=context):
            project = phase.project_id
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            start_date = project.date_start
            #Creating resources using the member of the Project
            u_ids = [i.id for i in project.members]
            resource_objs = resource_pool.generate_resources(cr, uid, u_ids, calendar_id, context=context)
            start_date = datetime.strftime((datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d")
            func_str = ''
            start = start_date
            minimum_time_unit = 1
            # default values
            working_hours_per_day = 24
            working_days_per_week = 7
            working_days_per_month = 30
            working_days_per_year = 365
            
            vacation = []
            if calendar_id:
                working_hours_per_day = 8 #TODO: it should be come from calendars
                working_days_per_week = 5
                working_days_per_month = 20
                working_days_per_year = 200
                vacation = tuple(resource_pool.compute_vacation(cr, uid, calendar_id, context=context))

            working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
            
            cls_str = ''
            # Creating Resources for the Project
            for key, vals in resource_objs.items():
                cls_str +='''
    class Resource_%s(Resource):
        title = \"%s\"
        vacation = %s
        efficiency = %s
'''%(key,  vals.get('name',False), vals.get('vacation', False), vals.get('efficiency', False))
    
            # Create a new project for each phase
            func_str += '''
def Phase_%d():
    from resource.faces import Resource
    title = \"%s\"
    start = \'%s\'
    minimum_time_unit = %s
    working_hours_per_day = %s
    working_days_per_week = %s
    working_days_per_month = %s
    working_days_per_year = %s
    vacation = %s
    working_days =  %s
'''%(phase.id, phase.name, start, minimum_time_unit, working_hours_per_day,  working_days_per_week, working_days_per_month, working_days_per_year, vacation, working_days )
            
            parent = False
            task_ids = []
            todo_task_ids = task_pool.search(cr, uid, [('id', 'in', map(lambda x : x.id, phase.task_ids)),
                                              ('state', 'in', ['draft', 'open', 'pending'])
                                              ], order='sequence')
            for task in task_pool.browse(cr, uid, todo_task_ids, context=context):
                func_str += task_pool.generate_task(cr, uid, task.id, parent=parent, flag=True, context=context)
                if not parent:
                    parent = task
                task_ids.append(task.id)
            func_str += cls_str
            phase_id = phase.id
            #check known constraints before running Face algorithm in order to have the error translated
            if not phase.project_id.date_start:
                raise osv.except_osv(_('Error !'),_('Task Scheduling is not possible.\nProject should have the Start date for scheduling.'))
            # Allocating Memory for the required Project and Pahses and Resources
            exec(func_str)
            Phase = eval('Phase_%d' % phase.id)
            phase = None
            try:
                phase = Task.BalancedProject(Phase)
            except Exception, e:
                raise osv.except_osv(_('Error !'),e)

            for task_id in task_ids:
                task = eval("phase.Task_%d" % task_id)
                start_date = task.start.to_datetime()
                end_date = task.end.to_datetime()
                
                task_pool.write(cr, uid, [task_id], {
                                      'date_start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                      'date_end': end_date.strftime('%Y-%m-%d %H:%M:%S')
                                    }, context=context)
        return True
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
        'name': fields.function(get_name, type='char', size=256),
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
        Schedule phase base on faces lib
        """
        if context is None:
            context = {}
        if type(ids) in (long, int,):
            ids = [ids]
        phase_pool = self.pool.get('project.phase')
        task_pool = self.pool.get('project.task')        
        resource_pool = self.pool.get('resource.resource')
        data_pool = self.pool.get('ir.model.data')
        resource_allocation_pool = self.pool.get('project.resource.allocation')
        data_model, day_uom_id = data_pool.get_object_reference(cr, uid, 'product', 'uom_day')
        
        #Checking the Valid Phase resource allocation from project member
        for project in self.browse(cr, uid, ids, context=context):
            flag = False
            res_missing = []
            members_ids = []
            if project.members:
                members_ids = [user.id for user in project.members]
            for phase in project.phase_ids:
                if phase.resource_ids:
                    res_ids = [ re.id for re in  phase.resource_ids] 
                    for res in resource_allocation_pool.browse(cr, uid, res_ids, context=context):
                        if res.resource_id.user_id.id not in members_ids:
                            res_missing += [res.resource_id.name]
                            flag = True
            if flag:
                raise osv.except_osv(_('Warning !'),_("Resource(s) %s is(are) not member(s) of the project '%s' .") % (",".join(res_missing), project.name))

        for project in self.browse(cr, uid, ids, context=context):
            root_phase_ids = phase_pool.search(cr, uid, [('project_id', '=', project.id),
                                                  ('state', 'in', ['draft', 'open', 'pending']),
                                                  ('previous_phase_ids', '=', False)
                                                  ])
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            start_date = project.date_start
            #if start_date:
            #    start_date = datetime.strftime((datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d")
            #Creating resources using the member of the Project
            u_ids = [i.id for i in project.members]
            resource_objs = resource_pool.generate_resources(cr, uid, u_ids, calendar_id, context=context)
            func_str = ''
            start = start_date
            minimum_time_unit = 1
            # default values
            working_hours_per_day = 24
            working_days_per_week = 7
            working_days_per_month = 30
            working_days_per_year = 365
            
            vacation = []
            if calendar_id:
                working_hours_per_day = 8 #TODO: it should be come from calendars
                working_days_per_week = 5
                working_days_per_month = 20
                working_days_per_year = 200
                vacation = tuple(resource_pool.compute_vacation(cr, uid, calendar_id, context=context))

            working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
            
            cls_str = ''
            # Creating Resources for the Project
            for key, vals in resource_objs.items():
                cls_str +='''
    class Resource_%s(Resource):
        title = \"%s\"
        vacation = %s
        efficiency = %s
'''%(key,  vals.get('name',False), vals.get('vacation', False), vals.get('efficiency', False))
        
            # Create a new project for each phase
            func_str += '''
def Project_%d():
    from resource.faces import Resource
    title = \"%s\"
    start = \'%s\'
    minimum_time_unit = %s
    working_hours_per_day = %s
    working_days_per_week = %s
    working_days_per_month = %s
    working_days_per_year = %s
    vacation = %s
    working_days =  %s
'''%(project.id, project.name, start, minimum_time_unit, working_hours_per_day,  working_days_per_week, working_days_per_month, working_days_per_year, vacation, working_days )

            func_str += cls_str
            phase_ids = []
            for root_phase in phase_pool.browse(cr, uid, root_phase_ids, context=context):
                phases, child_phase_ids = phase_pool.generate_phase(cr, uid, [root_phase.id], '', context=context)
                func_str += phases
                phase_ids += child_phase_ids
        
            project_id = project.id
            if not project.date_start:
                raise osv.except_osv(_('Error !'),_('Task Scheduling is not possible.\nProject should have the Start date for scheduling.'))
            # Allocating Memory for the required Project and Phases and Resources
            exec(func_str)
            Project = eval('Project_%d' % project.id)
            project = None
            try:
                project = Task.BalancedProject(Project)
            except Exception, e:
                raise osv.except_osv(_('Error !'), e)
            
            for phase_id in phase_ids:
                act_phase = phase_pool.browse(cr, uid, phase_id, context=context)
                resources = act_phase.resource_ids
                phase = eval("project.Phase_%d" % phase_id)
                start_date = phase.start.to_datetime()
                end_date = phase.end.to_datetime()
                
                if resources:
                    for res in resources:
                        vals = {}
                        vals.update({'date_start' :  start_date })
                        vals.update({'date_end' :  end_date})
                        resource_allocation_pool.write(cr, uid, res.id, vals, context=context)
                if act_phase.task_ids:
                    for task in act_phase.task_ids:
                        vals = {}
                        #Getting values of the Tasks
                        temp = eval("phase.Task_%s"%task.id)
                        if temp.booked_resource:
                            res_name = temp.booked_resource[0].title
                            res_id = resource_pool.search(cr, uid,[('name','=',res_name)], context = context)
                            if res_id:
                                res = resource_pool.browse(cr, uid, res_id[0], context = context)
                                vals.update({'user_id' : res.user_id.id})
                                               
                        vals.update({'date_start' : temp.start.strftime('%Y-%m-%d %H:%M:%S')})
                        vals.update({'date_end' : temp.end.strftime('%Y-%m-%d %H:%M:%S')})
                        task_pool.write(cr, uid, task.id, vals, context=context)


                phase_pool.write(cr, uid, [phase_id], {
                                        'date_start': start_date.strftime('%Y-%m-%d'),
                                        'date_end': end_date.strftime('%Y-%m-%d')
                                    }, context=context)
        return True            

    #TODO: DO Resource allocation and compute availability
    def compute_allocation(self, rc, uid, ids, start_date, end_date, context=None):
        if context ==  None:
            context = {}
        allocation = {}
        return allocation

    def schedule_tasks(self, cr, uid, ids, context=None):
        """
        Schedule task base on faces lib
        """
        if context is None:
            context = {}
        if type(ids) in (long, int,):
            ids = [ids]
        task_pool = self.pool.get('project.task')
        resource_pool = self.pool.get('resource.resource')
        data_pool = self.pool.get('ir.model.data')
        data_model, day_uom_id = data_pool.get_object_reference(cr, uid, 'product', 'uom_day')

        for project in self.browse(cr, uid, ids, context=context):
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            start_date = project.date_start
        
            #Checking the Valid Phase resource allocation from project member
            flag = False
            res_missing = []
            members_ids = []
            if project.members:
                members_ids = [user.id for user in project.members]
            for phase in project.phase_ids:
                if phase.resource_ids:
                    res_ids = [ re.id for re in  phase.resource_ids] 
                    for res in self.pool.get('project.resource.allocation').browse(cr, uid, res_ids, context=context):
                        if res.resource_id.user_id.id not in members_ids:
                            res_missing += [res.resource_id.name]
                            flag = True
            if flag:
                raise osv.except_osv(_('Warning !'),_("Resource(s) %s is(are) not member(s) of the project '%s' .") % (",".join(res_missing), project.name))
            #Creating resources using the member of the Project
            u_ids = [i.id for i in project.members]
            resource_objs = resource_pool.generate_resources(cr, uid, u_ids, calendar_id, context=context)
            try:
                start_date = datetime.strftime((datetime.strptime(start_date, "%Y-%m-%d")), "%Y-%m-%d")
            except:
                raise osv.except_osv(_('Error !'),_('Task Scheduling is not possible.\nProject should have the Start date for scheduling.'))
            func_str = ''
            start = start_date
            minimum_time_unit = 1
            # default values
            working_hours_per_day = 24
            working_days_per_week = 7
            working_days_per_month = 30
            working_days_per_year = 365
            
            vacation = []
            if calendar_id:
                working_hours_per_day = 8 #TODO: it should be come from calendars
                working_days_per_week = 5
                working_days_per_month = 20
                working_days_per_year = 200
                vacation = tuple(resource_pool.compute_vacation(cr, uid, calendar_id, context=context))

            working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
            
            cls_str = ''
            # Creating Resources for the Project
            for key, vals in resource_objs.items():
                cls_str +='''
    class Resource_%s(Resource):
        title = \"%s\"
        vacation = %s
        efficiency = %s
'''%(key,  vals.get('name',False), vals.get('vacation', False), vals.get('efficiency', False))
    
            # Create a new project for each phase
            func_str += '''
def Project_%d():
    from resource.faces import Resource
    title = \"%s\"
    start = \'%s\'
    minimum_time_unit = %s
    working_hours_per_day = %s
    working_days_per_week = %s
    working_days_per_month = %s
    working_days_per_year = %s
    vacation = %s
    working_days =  %s
'''%(project.id, project.name, start, minimum_time_unit, working_hours_per_day,  working_days_per_week, working_days_per_month, working_days_per_year, vacation, working_days )
            
            parent = False
            task_ids = []
            todo_task_ids = task_pool.search(cr, uid, [('project_id', '=', project.id),
                                              ('state', 'in', ['draft', 'open', 'pending'])
                                              ], order='sequence')
            if todo_task_ids:
                for task in task_pool.browse(cr, uid, todo_task_ids, context=context):
                    func_str += task_pool.generate_task(cr, uid, task.id, parent=parent, flag=True,context=context)
                    if not parent:
                        parent = task
                    task_ids.append(task.id)
            func_str += cls_str

            if not project.date_start:# or not project.members:
                raise osv.except_osv(_('Error !'),_('Task Scheduling is not possible.\nProject should have the Start date for scheduling.'))
            # Allocating Memory for the required Project and Phases and Resources
            exec(func_str)
            Project = eval('Project_%d' % project.id)
            project = None
            try:
                project = Task.BalancedProject(Project)
            except Exception, e:
                raise osv.except_osv(_('Error !'), e)
            
            for task_id in task_ids:
                task = eval("project.Task_%d" % task_id)
                start_date = task.start.to_datetime()
                end_date = task.end.to_datetime()
                
                task_pool.write(cr, uid, [task_id], {
                                      'date_start': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                                      'date_end': end_date.strftime('%Y-%m-%d %H:%M:%S')
                                    }, context=context)
        return True

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
    _defaults = {
        'user_id' : False
    }

    def generate_task(self, cr, uid, task_id, parent=False, flag=False, context=None):
        if context is None:
            context = {}
        task = self.browse(cr, uid, task_id, context=context)
        duration = str(task.planned_hours)+ 'H'
        str_resource = False
        parent = task.parent_ids
        if task.phase_id.resource_ids:
            str_resource = ('%s | '*len(task.phase_id.resource_ids))[:-2]
            str_resource = str_resource % tuple(map(lambda x: 'Resource_%s'%x.resource_id.id, task.phase_id.resource_ids))
        # Task Defination for the Phase of the Project
        if not flag:
            s = '''
        def Task_%s():
            title = \"%s\"
            effort = \'%s\'
            resource = %s
'''%(task.id, task.name, duration, str_resource)
            if task.child_ids:
                seq = [[child.planned_hours, child.id] for child in task.child_ids]
                seq.sort(key=itemgetter(0))
                s +='''
            start = up.Task_%s.end
    '''%(seq[-1][1])
        else:
            s = '''
    def Task_%s():
        title = \"%s\"
        effort = \'%s\'
        resource = %s
'''%(task.id, task.name, duration, str_resource)
            if task.child_ids:
                seq = [[child.planned_hours, child.id] for child in task.child_ids]
                seq.sort(key=itemgetter(0))
                s +='''
        start = up.Task_%s.end
'''%(seq[-1][1])
        s += '\n'
        return s
project_task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
