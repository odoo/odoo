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

from lxml import etree
import time
from datetime import datetime, date

from tools.translate import _
from osv import fields, osv
from openerp.addons.resource.faces import task as Task

# I think we can remove this in v6.1 since VMT's improvements in the framework ?
#class project_project(osv.osv):
#    _name = 'project.project'
#project_project()

_TASK_STATE = [('draft', 'New'),('open', 'In Progress'),('pending', 'Pending'), ('done', 'Done'), ('cancelled', 'Cancelled')]

class project_task_type(osv.osv):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, size=64, translate=True),
        'description': fields.text('Description'),
        'sequence': fields.integer('Sequence'),
        'project_default': fields.boolean('Common to All Projects', help="If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects."),
        'project_ids': fields.many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', 'Projects'),
        'state': fields.selection(_TASK_STATE, 'State', required=True, help="The related state for the stage. The state of your document will automatically change regarding the selected stage. Example, a stage is related to the state 'Close', when your document reach this stage, it will be automatically closed."),
        'fold': fields.boolean('Hide in views if empty', help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
    }
    _defaults = {
        'state': 'draft',
        'sequence': 1,
        'fold': False,
    }
    _order = 'sequence'
project_task_type()

class project(osv.osv):
    _name = "project.project"
    _description = "Project"
    _inherits = {'account.analytic.account': "analytic_account_id"}
    _inherit = ['ir.needaction_mixin', 'mail.thread']

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if user == 1:
            return super(project, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        if context and context.get('user_preference'):
                cr.execute("""SELECT project.id FROM project_project project
                           LEFT JOIN account_analytic_account account ON account.id = project.analytic_account_id
                           LEFT JOIN project_user_rel rel ON rel.project_id = project.analytic_account_id
                           WHERE (account.user_id = %s or rel.uid = %s)"""%(user, user))
                return [(r[0]) for r in cr.fetchall()]
        return super(project, self).search(cr, user, args, offset=offset, limit=limit, order=order,
            context=context, count=count)

    def _complete_name(self, cr, uid, ids, name, args, context=None):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = (m.parent_id and (m.parent_id.name + '/') or '') + m.name
        return res

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        partner_obj = self.pool.get('res.partner')
        if not part:
            return {'value':{}}
        val = {}
        if 'pricelist_id' in self.fields_get(cr, uid, context=context):
            pricelist = partner_obj.read(cr, uid, part, ['property_product_pricelist'], context=context)
            pricelist_id = pricelist.get('property_product_pricelist', False) and pricelist.get('property_product_pricelist')[0] or False
            val['pricelist_id'] = pricelist_id
        return {'value': val}

    def _get_projects_from_tasks(self, cr, uid, task_ids, context=None):
        tasks = self.pool.get('project.task').browse(cr, uid, task_ids, context=context)
        project_ids = [task.project_id.id for task in tasks if task.project_id]
        return self.pool.get('project.project')._get_project_and_parents(cr, uid, project_ids, context)

    def _get_project_and_parents(self, cr, uid, ids, context=None):
        """ return the project ids and all their parent projects """
        res = set(ids)
        while ids:
            cr.execute("""
                SELECT DISTINCT parent.id
                FROM project_project project, project_project parent, account_analytic_account account
                WHERE project.analytic_account_id = account.id
                AND parent.analytic_account_id = account.parent_id
                AND project.id IN %s
                """, (tuple(ids),))
            ids = [t[0] for t in cr.fetchall()]
            res.update(ids)
        return list(res)

    def _get_project_and_children(self, cr, uid, ids, context=None):
        """ retrieve all children projects of project ids;
            return a dictionary mapping each project to its parent project (or None)
        """
        res = dict.fromkeys(ids, None)
        while ids:
            cr.execute("""
                SELECT project.id, parent.id
                FROM project_project project, project_project parent, account_analytic_account account
                WHERE project.analytic_account_id = account.id
                AND parent.analytic_account_id = account.parent_id
                AND parent.id IN %s
                """, (tuple(ids),))
            dic = dict(cr.fetchall())
            res.update(dic)
            ids = dic.keys()
        return res

    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        child_parent = self._get_project_and_children(cr, uid, ids, context)
        # compute planned_hours, total_hours, effective_hours specific to each project
        cr.execute("""
            SELECT project_id, COALESCE(SUM(planned_hours), 0.0),
                COALESCE(SUM(total_hours), 0.0), COALESCE(SUM(effective_hours), 0.0)
            FROM project_task WHERE project_id IN %s AND state <> 'cancelled'
            GROUP BY project_id
            """, (tuple(child_parent.keys()),))
        # aggregate results into res
        res = dict([(id, {'planned_hours':0.0,'total_hours':0.0,'effective_hours':0.0}) for id in ids])
        for id, planned, total, effective in cr.fetchall():
            # add the values specific to id to all parent projects of id in the result
            while id:
                if id in ids:
                    res[id]['planned_hours'] += planned
                    res[id]['total_hours'] += total
                    res[id]['effective_hours'] += effective
                id = child_parent[id]
        # compute progress rates
        for id in ids:
            if res[id]['total_hours']:
                res[id]['progress_rate'] = round(100.0 * res[id]['effective_hours'] / res[id]['total_hours'], 2)
            else:
                res[id]['progress_rate'] = 0.0
        return res

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for proj in self.browse(cr, uid, ids):
            if proj.tasks:
                raise osv.except_osv(_('Operation Not Permitted !'), _('You cannot delete a project containing tasks. I suggest you to desactivate it.'))
        return super(project, self).unlink(cr, uid, ids, *args, **kwargs)

    def _task_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        task_ids = self.pool.get('project.task').search(cr, uid, [('project_id', 'in', ids)])
        for task in self.pool.get('project.task').browse(cr, uid, task_ids, context):
            res[task.project_id.id] += 1
        return res

    _columns = {
        'complete_name': fields.function(_complete_name, string="Project Name", type='char', size=250),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the project without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of Projects."),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', help="Link this project to an analytic account if you need financial management on projects. It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.", ondelete="cascade", required=True),
        'priority': fields.integer('Sequence', help="Gives the sequence order when displaying the list of projects"),
        'warn_manager': fields.boolean('Notify Manager', help="If you check this field, the project manager will receive an email each time a task is completed by his team.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),

        'members': fields.many2many('res.users', 'project_user_rel', 'project_id', 'uid', 'Project Members',
            help="Project's members are users who can have an access to the tasks related to this project.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'tasks': fields.one2many('project.task', 'project_id', "Task Activities"),
        'planned_hours': fields.function(_progress_rate, multi="progress", string='Planned Time', help="Sum of planned hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 20),
            }),
        'effective_hours': fields.function(_progress_rate, multi="progress", string='Time Spent', help="Sum of spent hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 20),
            }),
        'total_hours': fields.function(_progress_rate, multi="progress", string='Total Time', help="Sum of total hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 20),
            }),
        'progress_rate': fields.function(_progress_rate, multi="progress", string='Progress', type='float', group_operator="avg", help="Percent of tasks closed according to the total of tasks todo.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'state'], 20),
            }),
        'resource_calendar_id': fields.many2one('resource.calendar', 'Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close':[('readonly',True)]} ),
        'warn_customer': fields.boolean('Warn Partner', help="If you check this, the user will have a popup when closing a task that propose a message to send by email to the customer.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'warn_header': fields.text('Mail Header', help="Header added at the beginning of the email for the warning message sent to the customer when a task is closed.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'warn_footer': fields.text('Mail Footer', help="Footer added at the beginning of the email for the warning message sent to the customer when a task is closed.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'type_ids': fields.many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', 'Tasks Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'use_tasks': fields.boolean('Use Tasks', help="Check this field if this project is aimed at managing tasks"),
        'task_count': fields.function(_task_count, type='integer', string="Open Tasks"),
        'color': fields.integer('Color Index'),
        'company_uom_id': fields.related('company_id', 'project_time_mode_id', type='many2one', relation='product.uom'),
     }
    
    def dummy(self, cr, uid, ids, context):
        return True
       
    def _get_type_common(self, cr, uid, context):
        ids = self.pool.get('project.task.type').search(cr, uid, [('project_default','=',1)], context=context)
        return ids

    _order = "sequence"
    _defaults = {
        'active': True,
        'priority': 1,
        'sequence': 10,
        'type_ids': _get_type_common,
        'use_tasks': True,
    }

    # TODO: Why not using a SQL contraints ?
    def _check_dates(self, cr, uid, ids, context=None):
        for leave in self.read(cr, uid, ids, ['date_start', 'date'], context=context):
            if leave['date_start'] and leave['date']:
                if leave['date_start'] > leave['date']:
                    return False
        return True

    _constraints = [
        (_check_dates, 'Error! project start-date must be lower then project end-date.', ['date_start', 'date'])
    ]

    def set_template(self, cr, uid, ids, context=None):
        res = self.setActive(cr, uid, ids, value=False, context=context)
        return res

    def set_done(self, cr, uid, ids, context=None):
        task_obj = self.pool.get('project.task')
        task_ids = task_obj.search(cr, uid, [('project_id', 'in', ids), ('state', 'not in', ('cancelled', 'done'))])
        task_obj.write(cr, uid, task_ids, {'state': 'done', 'date_end':time.strftime('%Y-%m-%d %H:%M:%S'), 'remaining_hours': 0.0})
        self.write(cr, uid, ids, {'state':'close'}, context=context)
        self.set_close_send_note(cr, uid, ids, context=context)
        return True

    def set_cancel(self, cr, uid, ids, context=None):
        task_obj = self.pool.get('project.task')
        task_ids = task_obj.search(cr, uid, [('project_id', 'in', ids), ('state', '!=', 'done')])
        task_obj.write(cr, uid, task_ids, {'state': 'cancelled', 'date_end':time.strftime('%Y-%m-%d %H:%M:%S'), 'remaining_hours': 0.0})
        self.write(cr, uid, ids, {'state':'cancelled'}, context=context)
        self.set_cancel_send_note(cr, uid, ids, context=context)
        return True

    def set_pending(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        self.set_pending_send_note(cr, uid, ids, context=context)
        return True

    def set_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        self.set_open_send_note(cr, uid, ids, context=context)
        return True

    def reset_project(self, cr, uid, ids, context=None):
        res = self.setActive(cr, uid, ids, value=True, context=context)
        self.set_open_send_note(cr, uid, ids, context=context)
        return res

    def map_tasks(self, cr, uid, old_project_id, new_project_id, context=None):
        """ copy and map tasks from old to new project """
        if context is None:
            context = {}
        map_task_id = {}
        task_obj = self.pool.get('project.task')
        proj = self.browse(cr, uid, old_project_id, context=context)
        for task in proj.tasks:
            map_task_id[task.id] =  task_obj.copy(cr, uid, task.id, {}, context=context)
        self.write(cr, uid, [new_project_id], {'tasks':[(6,0, map_task_id.values())]})
        task_obj.duplicate_task(cr, uid, map_task_id, context=context)
        return True

    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}

        default = default or {}
        context['active_test'] = False
        default['state'] = 'open'
        default['tasks'] = []
        proj = self.browse(cr, uid, id, context=context)
        if not default.get('name', False):
            default['name'] = proj.name + _(' (copy)')

        res = super(project, self).copy(cr, uid, id, default, context)
        self.map_tasks(cr,uid,id,res,context)
        return res

    def duplicate_template(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        result = []
        for proj in self.browse(cr, uid, ids, context=context):
            parent_id = context.get('parent_id', False)
            context.update({'analytic_project_copy': True})
            new_date_start = time.strftime('%Y-%m-%d')
            new_date_end = False
            if proj.date_start and proj.date:
                start_date = date(*time.strptime(proj.date_start,'%Y-%m-%d')[:3])
                end_date = date(*time.strptime(proj.date,'%Y-%m-%d')[:3])
                new_date_end = (datetime(*time.strptime(new_date_start,'%Y-%m-%d')[:3])+(end_date-start_date)).strftime('%Y-%m-%d')
            context.update({'copy':True})
            new_id = self.copy(cr, uid, proj.id, default = {
                                    'name': proj.name +_(' (copy)'),
                                    'state':'open',
                                    'date_start':new_date_start,
                                    'date':new_date_end,
                                    'parent_id':parent_id}, context=context)
            result.append(new_id)

            child_ids = self.search(cr, uid, [('parent_id','=', proj.analytic_account_id.id)], context=context)
            parent_id = self.read(cr, uid, new_id, ['analytic_account_id'])['analytic_account_id'][0]
            if child_ids:
                self.duplicate_template(cr, uid, child_ids, context={'parent_id': parent_id})

        if result and len(result):
            res_id = result[0]
            form_view_id = data_obj._get_id(cr, uid, 'project', 'edit_project')
            form_view = data_obj.read(cr, uid, form_view_id, ['res_id'])
            tree_view_id = data_obj._get_id(cr, uid, 'project', 'view_project')
            tree_view = data_obj.read(cr, uid, tree_view_id, ['res_id'])
            search_view_id = data_obj._get_id(cr, uid, 'project', 'view_project_project_filter')
            search_view = data_obj.read(cr, uid, search_view_id, ['res_id'])
            return {
                'name': _('Projects'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'project.project',
                'view_id': False,
                'res_id': res_id,
                'views': [(form_view['res_id'],'form'),(tree_view['res_id'],'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view['res_id'],
                'nodestroy': True
            }

    # set active value for a project, its sub projects and its tasks
    def setActive(self, cr, uid, ids, value=True, context=None):
        task_obj = self.pool.get('project.task')
        for proj in self.browse(cr, uid, ids, context=None):
            self.write(cr, uid, [proj.id], {'state': value and 'open' or 'template'}, context)
            cr.execute('select id from project_task where project_id=%s', (proj.id,))
            tasks_id = [x[0] for x in cr.fetchall()]
            if tasks_id:
                task_obj.write(cr, uid, tasks_id, {'active': value}, context=context)
            child_ids = self.search(cr, uid, [('parent_id','=', proj.analytic_account_id.id)])
            if child_ids:
                self.setActive(cr, uid, child_ids, value, context=None)
        return True

    def _schedule_header(self, cr, uid, ids, force_members=True, context=None):
        context = context or {}
        if type(ids) in (long, int,):
            ids = [ids]
        projects = self.browse(cr, uid, ids, context=context)

        for project in projects:
            if (not project.members) and force_members:
                raise osv.except_osv(_('Warning !'),_("You must assign members on the project '%s' !") % (project.name,))

        resource_pool = self.pool.get('resource.resource')

        result = "from openerp.addons.resource.faces import *\n"
        result += "import datetime\n"
        for project in self.browse(cr, uid, ids, context=context):
            u_ids = [i.id for i in project.members]
            if project.user_id and (project.user_id.id not in u_ids):
                u_ids.append(project.user_id.id)
            for task in project.tasks:
                if task.state in ('done','cancelled'):
                    continue
                if task.user_id and (task.user_id.id not in u_ids):
                    u_ids.append(task.user_id.id)
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            resource_objs = resource_pool.generate_resources(cr, uid, u_ids, calendar_id, context=context)
            for key, vals in resource_objs.items():
                result +='''
class User_%s(Resource):
    efficiency = %s
''' % (key,  vals.get('efficiency', False))

        result += '''
def Project():
        '''
        return result

    def _schedule_project(self, cr, uid, project, context=None):
        resource_pool = self.pool.get('resource.resource')
        calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
        working_days = resource_pool.compute_working_calendar(cr, uid, calendar_id, context=context)
        # TODO: check if we need working_..., default values are ok.
        puids = [x.id for x in project.members]
        if project.user_id:
            puids.append(project.user_id.id)
        result = """
  def Project_%d():
    start = \'%s\'
    working_days = %s
    resource = %s
"""       % (
            project.id,
            project.date_start, working_days,
            '|'.join(['User_'+str(x) for x in puids])
        )
        vacation = calendar_id and tuple(resource_pool.compute_vacation(cr, uid, calendar_id, context=context)) or False
        if vacation:
            result+= """
    vacation = %s
""" %   ( vacation, )
        return result

    #TODO: DO Resource allocation and compute availability
    def compute_allocation(self, rc, uid, ids, start_date, end_date, context=None):
        if context ==  None:
            context = {}
        allocation = {}
        return allocation

    def schedule_tasks(self, cr, uid, ids, context=None):
        context = context or {}
        if type(ids) in (long, int,):
            ids = [ids]
        projects = self.browse(cr, uid, ids, context=context)
        result = self._schedule_header(cr, uid, ids, False, context=context)
        for project in projects:
            result += self._schedule_project(cr, uid, project, context=context)
            result += self.pool.get('project.task')._generate_task(cr, uid, project.tasks, ident=4, context=context)

        local_dict = {}
        exec result in local_dict
        projects_gantt = Task.BalancedProject(local_dict['Project'])

        for project in projects:
            project_gantt = getattr(projects_gantt, 'Project_%d' % (project.id,))
            for task in project.tasks:
                if task.state in ('done','cancelled'):
                    continue

                p = getattr(project_gantt, 'Task_%d' % (task.id,))

                self.pool.get('project.task').write(cr, uid, [task.id], {
                    'date_start': p.start.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_end': p.end.strftime('%Y-%m-%d %H:%M:%S')
                }, context=context)
                if (not task.user_id) and (p.booked_resource):
                    self.pool.get('project.task').write(cr, uid, [task.id], {
                        'user_id': int(p.booked_resource[0].name[5:]),
                    }, context=context)
        return True

    # ------------------------------------------------
    # OpenChatter methods and notifications
    # ------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = []
            if obj.state == 'draft' and obj.user_id:
                result[obj.id] = [obj.user_id.id]
        return result

    def message_get_subscribers(self, cr, uid, ids, context=None):
        sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context);
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id:
                sub_ids.append(obj.user_id.id)
        return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)

    def create(self, cr, uid, vals, context=None):
        obj_id = super(project, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def create_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Project has been <b>created</b>."), context=context)

    def set_open_send_note(self, cr, uid, ids, context=None):
        message = _("Project has been <b>opened</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def set_pending_send_note(self, cr, uid, ids, context=None):
        message = _("Project is now <b>pending</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def set_cancel_send_note(self, cr, uid, ids, context=None):
        message = _("Project has been <b>cancelled</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def set_close_send_note(self, cr, uid, ids, context=None):
        message = _("Project has been <b>closed</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)
    
project()

class task(osv.osv):
    _name = "project.task"
    _description = "Task"
    _log_create = True
    _date_name = "date_start"
    _inherit = ['ir.needaction_mixin', 'mail.thread']


    def _resolve_project_id_from_context(self, cr, uid, context=None):
        """Return ID of project based on the value of 'project_id'
           context key, or None if it cannot be resolved to a single project.
        """
        if context is None: context = {}
        if type(context.get('default_project_id')) in (int, long):
            project_id = context['default_project_id']
            return project_id
        if isinstance(context.get('default_project_id'), basestring):
            project_name = context['default_project_id']
            project_ids = self.pool.get('project.project').name_search(cr, uid, name=project_name)
            if len(project_ids) == 1:
                return project_ids[0][0]

    def _read_group_type_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('project.task.type')
        project_id = self._resolve_project_id_from_context(cr, uid, context=context)
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid
        if read_group_order == 'type_id desc':
            # lame way to allow reverting search, should just work in the trivial case
            order = '%s desc' % order
        if project_id:
            domain = ['|', ('id','in',ids), ('project_ids','in',project_id)]
        else:
            domain = ['|', ('id','in',ids), ('project_default','=',1)]
        stage_ids = stage_obj._search(cr, uid, domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

    def _read_group_user_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        res_users = self.pool.get('res.users')
        project_id = self._resolve_project_id_from_context(cr, uid, context=context)
        access_rights_uid = access_rights_uid or uid
        if project_id:
            ids += self.pool.get('project.project').read(cr, access_rights_uid, project_id, ['members'], context=context)['members']
            order = res_users._order
            # lame way to allow reverting search, should just work in the trivial case
            if read_group_order == 'user_id desc':
                order = '%s desc' % order
            # de-duplicate and apply search order
            ids = res_users._search(cr, uid, [('id','in',ids)], order=order, access_rights_uid=access_rights_uid, context=context)
        result = res_users.name_get(cr, access_rights_uid, ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(ids.index(x[0]), ids.index(y[0])))
        return result

    _group_by_full = {
        'type_id': _read_group_type_id,
        'user_id': _read_group_user_id
    }


    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        obj_project = self.pool.get('project.project')
        for domain in args:
            if domain[0] == 'project_id' and (not isinstance(domain[2], str)):
                id = isinstance(domain[2], list) and domain[2][0] or domain[2]
                if id and isinstance(id, (long, int)):
                    if obj_project.read(cr, user, id, ['state'])['state'] == 'template':
                        args.append(('active', '=', False))
        return super(task, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def _str_get(self, task, level=0, border='***', context=None):
        return border+' '+(task.user_id and task.user_id.name.upper() or '')+(level and (': L'+str(level)) or '')+(' - %.1fh / %.1fh'%(task.effective_hours or 0.0,task.planned_hours))+' '+border+'\n'+ \
            border[0]+' '+(task.name or '')+'\n'+ \
            (task.description or '')+'\n\n'

    # Compute: effective_hours, total_hours, progress
    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        cr.execute("SELECT task_id, COALESCE(SUM(hours),0) FROM project_task_work WHERE task_id IN %s GROUP BY task_id",(tuple(ids),))
        hours = dict(cr.fetchall())
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {'effective_hours': hours.get(task.id, 0.0), 'total_hours': (task.remaining_hours or 0.0) + hours.get(task.id, 0.0)}
            res[task.id]['delay_hours'] = res[task.id]['total_hours'] - task.planned_hours
            res[task.id]['progress'] = 0.0
            if (task.remaining_hours + hours.get(task.id, 0.0)):
                res[task.id]['progress'] = round(min(100.0 * hours.get(task.id, 0.0) / res[task.id]['total_hours'], 99.99),2)
            if task.state in ('done','cancelled'):
                res[task.id]['progress'] = 100.0
        return res


    def onchange_remaining(self, cr, uid, ids, remaining=0.0, planned = 0.0):
        if remaining and not planned:
            return {'value':{'planned_hours': remaining}}
        return {}

    def onchange_planned(self, cr, uid, ids, planned = 0.0, effective = 0.0):
        return {'value':{'remaining_hours': planned - effective}}

    def onchange_project(self, cr, uid, id, project_id):
        if not project_id:
            return {}
        data = self.pool.get('project.project').browse(cr, uid, [project_id])
        partner_id=data and data[0].partner_id
        if partner_id:
            return {'value':{'partner_id':partner_id.id}}
        return {}

    def duplicate_task(self, cr, uid, map_ids, context=None):
        for new in map_ids.values():
            task = self.browse(cr, uid, new, context)
            child_ids = [ ch.id for ch in task.child_ids]
            if task.child_ids:
                for child in task.child_ids:
                    if child.id in map_ids.keys():
                        child_ids.remove(child.id)
                        child_ids.append(map_ids[child.id])

            parent_ids = [ ch.id for ch in task.parent_ids]
            if task.parent_ids:
                for parent in task.parent_ids:
                    if parent.id in map_ids.keys():
                        parent_ids.remove(parent.id)
                        parent_ids.append(map_ids[parent.id])
            #FIXME why there is already the copy and the old one
            self.write(cr, uid, new, {'parent_ids':[(6,0,set(parent_ids))], 'child_ids':[(6,0, set(child_ids))]})

    def copy_data(self, cr, uid, id, default={}, context=None):
        default = default or {}
        default.update({'work_ids':[], 'date_start': False, 'date_end': False, 'date_deadline': False})
        if not default.get('remaining_hours', False):
            default['remaining_hours'] = float(self.read(cr, uid, id, ['planned_hours'])['planned_hours'])
        default['active'] = True
        default['type_id'] = False
        if not default.get('name', False):
            default['name'] = self.browse(cr, uid, id, context=context).name or ''
            if not context.get('copy',False):
                new_name = _("%s (copy)")%default.get('name','')
                default.update({'name':new_name})
        return super(task, self).copy_data(cr, uid, id, default, context)


    def _is_template(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = True
            if task.project_id:
                if task.project_id.active == False or task.project_id.state == 'template':
                    res[task.id] = False
        return res

    def _get_task(self, cr, uid, ids, context=None):
        result = {}
        for work in self.pool.get('project.task.work').browse(cr, uid, ids, context=context):
            if work.task_id: result[work.task_id.id] = True
        return result.keys()

    _columns = {
        'active': fields.function(_is_template, store=True, string='Not a Template Task', type='boolean', help="This field is computed automatically and have the same behavior than the boolean 'active' field: if the task is linked to a template or unactivated project, it will be hidden unless specifically asked."),
        'name': fields.char('Task Summary', size=128, required=True, select=True),
        'description': fields.text('Description'),
        'priority': fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Important'), ('0','Very important')], 'Priority', select=True),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of tasks."),
        'type_id': fields.many2one('project.task.type', 'Stage'),
        'state': fields.related('type_id', 'state', type="selection", store=True,
                selection=_TASK_STATE, string="State", readonly=True,
                help='The state is set to \'Draft\', when a case is created.\
                      If the case is in progress the state is set to \'Open\'.\
                      When the case is over, the state is set to \'Done\'.\
                      If the case needs to be reviewed then the state is \
                      set to \'Pending\'.'),
        'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready To Pull')], 'Kanban State',
                                         help="A task's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this task\n"
                                              " * Ready To Pull indicates the task is ready to be pulled to the next stage",
                                         readonly=True, required=False),
        'create_date': fields.datetime('Create Date', readonly=True,select=True),
        'date_start': fields.datetime('Starting Date',select=True),
        'date_end': fields.datetime('Ending Date',select=True),
        'date_deadline': fields.date('Deadline',select=True),
        'project_id': fields.many2one('project.project', 'Project', ondelete='set null', select="1"),
        'parent_ids': fields.many2many('project.task', 'project_task_parent_rel', 'task_id', 'parent_id', 'Parent Tasks'),
        'child_ids': fields.many2many('project.task', 'project_task_parent_rel', 'parent_id', 'task_id', 'Delegated Tasks'),
        'notes': fields.text('Notes'),
        'planned_hours': fields.float('Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.'),
        'effective_hours': fields.function(_hours_get, string='Hours Spent', multi='hours', help="Computed using the sum of the task work done.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'remaining_hours': fields.float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
        'total_hours': fields.function(_hours_get, string='Total Hours', multi='hours', help="Computed as: Time Spent + Remaining Time.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'progress': fields.function(_hours_get, string='Progress (%)', multi='hours', group_operator="avg", help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours','state'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'delay_hours': fields.function(_hours_get, string='Delay Hours', multi='hours', help="Computed as difference between planned hours by the project manager and the total hours of the task.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'user_id': fields.many2one('res.users', 'Assigned to'),
        'delegated_user_id': fields.related('child_ids', 'user_id', type='many2one', relation='res.users', string='Delegated To'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'work_ids': fields.one2many('project.task.work', 'task_id', 'Work done'),
        'manager_id': fields.related('project_id', 'analytic_account_id', 'user_id', type='many2one', relation='res.users', string='Project Manager'),
        'company_id': fields.many2one('res.company', 'Company'),
        'id': fields.integer('ID', readonly=True),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'user_email', type='char', string='User Email', readonly=True),
    }

    _defaults = {
        'state': 'draft',
        'kanban_state': 'normal',
        'priority': '2',
        'progress': 0,
        'sequence': 10,
        'active': True,
        'user_id': lambda obj, cr, uid, context: uid,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'project.task', context=c)
    }

    _order = "priority, sequence, date_start, name, id"

    def set_priority(self, cr, uid, ids, priority):
        """Set task priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set task priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set task priority to normal
        """
        return self.set_priority(cr, uid, ids, '2')

    def _check_recursion(self, cr, uid, ids, context=None):
        for id in ids:
            visited_branch = set()
            visited_node = set()
            res = self._check_cycle(cr, uid, id, visited_branch, visited_node, context=context)
            if not res:
                return False

        return True

    def _check_cycle(self, cr, uid, id, visited_branch, visited_node, context=None):
        if id in visited_branch: #Cycle
            return False

        if id in visited_node: #Already tested don't work one more time for nothing
            return True

        visited_branch.add(id)
        visited_node.add(id)

        #visit child using DFS
        task = self.browse(cr, uid, id, context=context)
        for child in task.child_ids:
            res = self._check_cycle(cr, uid, child.id, visited_branch, visited_node, context=context)
            if not res:
                return False

        visited_branch.remove(id)
        return True

    def _check_dates(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_task = self.browse(cr, uid, ids[0], context=context)
        start = obj_task.date_start or False
        end = obj_task.date_end or False
        if start and end :
            if start > end:
                return False
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive tasks.', ['parent_ids']),
        (_check_dates, 'Error ! Task end-date must be greater then task start-date', ['date_start','date_end'])
    ]
    #
    # Override view according to the company definition
    #
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        users_obj = self.pool.get('res.users')

        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        obj_tm = users_obj.browse(cr, 1, uid, context=context).company_id.project_time_mode_id
        tm = obj_tm and obj_tm.name or 'Hours'

        res = super(task, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu=submenu)

        if tm in ['Hours','Hour']:
            return res

        eview = etree.fromstring(res['arch'])

        def _check_rec(eview):
            if eview.attrib.get('widget','') == 'float_time':
                eview.set('widget','float')
            for child in eview:
                _check_rec(child)
            return True

        _check_rec(eview)

        res['arch'] = etree.tostring(eview)

        for f in res['fields']:
            if 'Hours' in res['fields'][f]['string']:
                res['fields'][f]['string'] = res['fields'][f]['string'].replace('Hours',tm)
        return res

    def _check_child_task(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        tasks = self.browse(cr, uid, ids, context=context)
        for task in tasks:
            if task.child_ids:
                for child in task.child_ids:
                    if child.state in ['draft', 'open', 'pending']:
                        raise osv.except_osv(_("Warning !"), _("Child task still open.\nPlease cancel or complete child task first."))
        return True

    def action_close(self, cr, uid, ids, context=None):
        # This action open wizard to send email to partner or project manager after close task.
        if context == None:
            context = {}
        task_id = len(ids) and ids[0] or False
        self._check_child_task(cr, uid, ids, context=context)
        if not task_id: return False
        task = self.browse(cr, uid, task_id, context=context)
        project = task.project_id
        res = self.do_close(cr, uid, [task_id], context=context)
        if project.warn_manager or project.warn_customer:
            return {
                'name': _('Send Email after close task'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy': True,
                'context': {'active_id': task.id,
                            'active_model': 'project.task'}
           }
        return res

    def do_close(self, cr, uid, ids, context={}):
        """
        Close Task
        """
        request = self.pool.get('res.request')
        if not isinstance(ids,list): ids = [ids]
        for task in self.browse(cr, uid, ids, context=context):
            vals = {}
            project = task.project_id
            if project:
                # Send request to project manager
                if project.warn_manager and project.user_id and (project.user_id.id != uid):
                    request.create(cr, uid, {
                        'name': _("Task '%s' closed") % task.name,
                        'state': 'waiting',
                        'act_from': uid,
                        'act_to': project.user_id.id,
                        'ref_partner_id': task.partner_id.id,
                        'ref_doc1': 'project.task,%d'% (task.id,),
                        'ref_doc2': 'project.project,%d'% (project.id,),
                    }, context=context)

            for parent_id in task.parent_ids:
                if parent_id.state in ('pending','draft'):
                    reopen = True
                    for child in parent_id.child_ids:
                        if child.id != task.id and child.state not in ('done','cancelled'):
                            reopen = False
                    if reopen:
                        self.do_reopen(cr, uid, [parent_id.id], context=context)
            vals.update({'state': 'done'})
            vals.update({'remaining_hours': 0.0})
            if not task.date_end:
                vals.update({ 'date_end':time.strftime('%Y-%m-%d %H:%M:%S')})
            self.write(cr, uid, [task.id],vals, context=context)
            self.do_close_send_note(cr, uid, [task.id], context)
        return True

    def do_reopen(self, cr, uid, ids, context=None):
        request = self.pool.get('res.request')

        for task in self.browse(cr, uid, ids, context=context):
            project = task.project_id
            if project and project.warn_manager and project.user_id.id and (project.user_id.id != uid):
                request.create(cr, uid, {
                    'name': _("Task '%s' set in progress") % task.name,
                    'state': 'waiting',
                    'act_from': uid,
                    'act_to': project.user_id.id,
                    'ref_partner_id': task.partner_id.id,
                    'ref_doc1': 'project.task,%d' % task.id,
                    'ref_doc2': 'project.project,%d' % project.id,
                }, context=context)

            self.write(cr, uid, [task.id], {'state': 'open'}, context=context)
            self.do_open_send_note(cr, uid, [task.id], context)
        return True

    def do_cancel(self, cr, uid, ids, context={}):
        request = self.pool.get('res.request')
        tasks = self.browse(cr, uid, ids, context=context)
        self._check_child_task(cr, uid, ids, context=context)
        for task in tasks:
            project = task.project_id
            if project.warn_manager and project.user_id and (project.user_id.id != uid):
                request.create(cr, uid, {
                    'name': _("Task '%s' cancelled") % task.name,
                    'state': 'waiting',
                    'act_from': uid,
                    'act_to': project.user_id.id,
                    'ref_partner_id': task.partner_id.id,
                    'ref_doc1': 'project.task,%d' % task.id,
                    'ref_doc2': 'project.project,%d' % project.id,
                }, context=context)
            self.write(cr, uid, [task.id], {'state': 'cancelled', 'remaining_hours':0.0}, context=context)
            self.do_cancel_send_note(cr, uid, [task.id], context)
        return True

    def do_open(self, cr, uid, ids, context={}):
        if not isinstance(ids,list): ids = [ids]
        tasks= self.browse(cr, uid, ids, context=context)
        for t in tasks:
            data = {'state': 'open'}
            if not t.date_start:
                data['date_start'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.write(cr, uid, [t.id], data, context=context)
            self.do_open_send_note(cr, uid, [t.id], context)
        return True

    def do_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        self.do_draft_send_note(cr, uid, ids, context)
        return True


    def _delegate_task_attachments(self, cr, uid, task_id, delegated_task_id, context=None):
        attachment = self.pool.get('ir.attachment')
        attachment_ids = attachment.search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', task_id)], context=context)
        new_attachment_ids = []
        for attachment_id in attachment_ids:
            new_attachment_ids.append(attachment.copy(cr, uid, attachment_id, default={'res_id': delegated_task_id}, context=context))
        return new_attachment_ids


    def do_delegate(self, cr, uid, ids, delegate_data={}, context=None):
        """
        Delegate Task to another users.
        """
        assert delegate_data['user_id'], _("Delegated User should be specified")
        delegated_tasks = {}
        for task in self.browse(cr, uid, ids, context=context):
            delegated_task_id = self.copy(cr, uid, task.id, {
                'name': delegate_data['name'],
                'project_id': delegate_data['project_id'] and delegate_data['project_id'][0] or False,
                'user_id': delegate_data['user_id'] and delegate_data['user_id'][0] or False,
                'planned_hours': delegate_data['planned_hours'] or 0.0,
                'parent_ids': [(6, 0, [task.id])],
                'state': 'draft',
                'description': delegate_data['new_task_description'] or '',
                'child_ids': [],
                'work_ids': []
            }, context=context)
            self._delegate_task_attachments(cr, uid, task.id, delegated_task_id, context=context)
            newname = delegate_data['prefix'] or ''
            task.write({
                'remaining_hours': delegate_data['planned_hours_me'],
                'planned_hours': delegate_data['planned_hours_me'] + (task.effective_hours or 0.0),
                'name': newname,
            }, context=context)
            if delegate_data['state'] == 'pending':
                self.do_pending(cr, uid, [task.id], context=context)
            elif delegate_data['state'] == 'done':
                self.do_close(cr, uid, [task.id], context=context)
            self.do_delegation_send_note(cr, uid, [task.id], context)
            delegated_tasks[task.id] = delegated_task_id
        return delegated_tasks

    def do_pending(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'pending'}, context=context)
        self.do_pending_send_note(cr, uid, ids, context)
        return True

    def set_remaining_time(self, cr, uid, ids, remaining_time=1.0, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            if (task.state=='draft') or (task.planned_hours==0.0):
                self.write(cr, uid, [task.id], {'planned_hours': remaining_time}, context=context)
        self.write(cr, uid, ids, {'remaining_hours': remaining_time}, context=context)
        return True

    def set_remaining_time_1(self, cr, uid, ids, context=None):
        return self.set_remaining_time(cr, uid, ids, 1.0, context)

    def set_remaining_time_2(self, cr, uid, ids, context=None):
        return self.set_remaining_time(cr, uid, ids, 2.0, context)

    def set_remaining_time_5(self, cr, uid, ids, context=None):
        return self.set_remaining_time(cr, uid, ids, 5.0, context)

    def set_remaining_time_10(self, cr, uid, ids, context=None):
        return self.set_remaining_time(cr, uid, ids, 10.0, context)

    def set_kanban_state_blocked(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'blocked'}, context=context)

    def set_kanban_state_normal(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'normal'}, context=context)

    def set_kanban_state_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'kanban_state': 'done'}, context=context)

    def _change_type(self, cr, uid, ids, next, context=None):
        """
            go to the next stage
            if next is False, go to previous stage
        """
        for task in self.browse(cr, uid, ids):
            if  task.project_id.type_ids:
                typeid = task.type_id.id
                types_seq={}
                for type in task.project_id.type_ids :
                    types_seq[type.id] = type.sequence
                if next:
                    types = sorted(types_seq.items(), lambda x, y: cmp(x[1], y[1]))
                else:
                    types = sorted(types_seq.items(), lambda x, y: cmp(y[1], x[1]))
                sorted_types = [x[0] for x in types]
                if not typeid:
                    self.write(cr, uid, task.id, {'type_id': sorted_types[0]})
                elif typeid and typeid in sorted_types and sorted_types.index(typeid) != len(sorted_types)-1:
                    index = sorted_types.index(typeid)
                    self.write(cr, uid, task.id, {'type_id': sorted_types[index+1]})
                self.state_change_send_note(cr, uid, [task.id], context)
        return True

    def next_type(self, cr, uid, ids, context=None):
        return self._change_type(cr, uid, ids, True, context=context)

    def prev_type(self, cr, uid, ids, context=None):
        return self._change_type(cr, uid, ids, False, context=context)

    def _store_history(self, cr, uid, ids, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            self.pool.get('project.task.history').create(cr, uid, {
                'task_id': task.id,
                'remaining_hours': task.remaining_hours,
                'planned_hours': task.planned_hours,
                'kanban_state': task.kanban_state,
                'type_id': task.type_id.id,
                'state': task.state,
                'user_id': task.user_id.id

            }, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        task_id = super(task, self).create(cr, uid, vals, context=context)
        self._store_history(cr, uid, [task_id], context=context)
        self.create_send_note(cr, uid, [task_id], context=context)
        return task_id

    # Overridden to reset the kanban_state to normal whenever
    # the stage (type_id) of the task changes.
    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals and not 'kanban_state' in vals and 'type_id' in vals:
            new_stage = vals.get('type_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for t in self.browse(cr, uid, ids, context=context):
                #TO FIX:Kanban view doesn't raise warning 
#                stages = [stage.id for stage in t.project_id.type_ids]
#                if new_stage not in stages:
#                    raise osv.except_osv(_('Warning !'), _('Stage is not defined in the project.'))
                write_vals = vals_reset_kstate if t.type_id != new_stage else vals
                super(task,self).write(cr, uid, [t.id], write_vals, context=context)
            result = True
        else:
            result = super(task,self).write(cr, uid, ids, vals, context=context)
        if ('type_id' in vals) or ('remaining_hours' in vals) or ('user_id' in vals) or ('state' in vals) or ('kanban_state' in vals):
            self._store_history(cr, uid, ids, context=context)
            self.state_change_send_note(cr, uid, ids, context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        self._check_child_task(cr, uid, ids, context=context)
        res = super(task, self).unlink(cr, uid, ids, context)
        return res

    def _generate_task(self, cr, uid, tasks, ident=4, context=None):
        context = context or {}
        result = ""
        ident = ' '*ident
        for task in tasks:
            if task.state in ('done','cancelled'):
                continue
            result += '''
%sdef Task_%s():
%s  todo = \"%.2fH\"
%s  effort = \"%.2fH\"''' % (ident,task.id, ident,task.remaining_hours, ident,task.total_hours)
            start = []
            for t2 in task.parent_ids:
                start.append("up.Task_%s.end" % (t2.id,))
            if start:
                result += '''
%s  start = max(%s)
''' % (ident,','.join(start))

            if task.user_id:
                result += '''
%s  resource = %s
''' % (ident, 'User_'+str(task.user_id.id))

        result += "\n"
        return result
    
    # ---------------------------------------------------
    # OpenChatter methods and notifications
    # ---------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'draft' and obj.user_id:
                result[obj.id] = [obj.user_id.id]
        return result

    def message_get_subscribers(self, cr, uid, ids, context=None):
        sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context);
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id:
                sub_ids.append(obj.user_id.id)
            if obj.manager_id:
                sub_ids.append(obj.manager_id.id)
        return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)

    def create_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Task has been <b>created</b>."), context=context)

    def do_pending_send_note(self, cr, uid, ids, context=None):
        if not isinstance(ids,list): ids = [ids]
        msg = _('Task is now <b>pending</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def do_open_send_note(self, cr, uid, ids, context=None):
        msg = _('Task has been <b>opened</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def do_cancel_send_note(self, cr, uid, ids, context=None):
        msg = _('Task has been <b>canceled</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def do_close_send_note(self, cr, uid, ids, context=None):
        msg = _('Task has been <b>closed</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def do_draft_send_note(self, cr, uid, ids, context=None):
        msg = _('Task has been <b>renewed</b>.')
        return self.message_append_note(cr, uid, ids, body=msg, context=context)

    def do_delegation_send_note(self, cr, uid, ids, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            msg = _('Task has been <b>delegated</b> to <em>%s</em>.') % (task.user_id.name)
            self.message_append_note(cr, uid, [task.id], body=msg, context=context)
        return True

    def state_change_send_note(self, cr, uid, ids, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            msg = _('Stage changed to <b>%s</b>') % (task.type_id.name)
            self.message_append_note(cr, uid, [task.id], body=msg, context=context)
        return True

task()

class project_work(osv.osv):
    _name = "project.task.work"
    _description = "Project Task Work"
    _columns = {
        'name': fields.char('Work summary', size=128),
        'date': fields.datetime('Date', select="1"),
        'task_id': fields.many2one('project.task', 'Task', ondelete='cascade', required=True, select="1"),
        'hours': fields.float('Time Spent'),
        'user_id': fields.many2one('res.users', 'Done by', required=True, select="1"),
        'company_id': fields.related('task_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True)
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')
    }

    _order = "date desc"
    def create(self, cr, uid, vals, *args, **kwargs):
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'task_id' in vals:
            cr.execute('update project_task set remaining_hours=remaining_hours - %s where id=%s', (vals.get('hours',0.0), vals['task_id']))
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'hours' in vals:
            for work in self.browse(cr, uid, ids, context=context):
                cr.execute('update project_task set remaining_hours=remaining_hours - %s + (%s) where id=%s', (vals.get('hours',0.0), work.hours, work.task_id.id))
        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for work in self.browse(cr, uid, ids):
            cr.execute('update project_task set remaining_hours=remaining_hours + %s where id=%s', (work.hours, work.task_id.id))
        return super(project_work,self).unlink(cr, uid, ids,*args, **kwargs)
project_work()

class account_analytic_account(osv.osv):

    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
            vals['child_ids'] = []
        return super(account_analytic_account, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        project_obj = self.pool.get('project.project')
        analytic_ids = project_obj.search(cr, uid, [('analytic_account_id','in',ids)])
        if analytic_ids:
            raise osv.except_osv(_('Warning !'), _('Please delete the project linked with this account first.'))
        return super(account_analytic_account, self).unlink(cr, uid, ids, *args, **kwargs)

account_analytic_account()

#
# Tasks History, used for cumulative flow charts (Lean/Agile)
#

class project_task_history(osv.osv):
    _name = 'project.task.history'
    _description = 'History of Tasks'
    _rec_name = 'task_id'
    _log_access = False
    def _get_date(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for history in self.browse(cr, uid, ids, context=context):
            if history.state in ('done','cancelled'):
                result[history.id] = history.date
                continue
            cr.execute('''select
                    date
                from
                    project_task_history
                where
                    task_id=%s and
                    id>%s
                order by id limit 1''', (history.task_id.id, history.id))
            res = cr.fetchone()
            result[history.id] = res and res[0] or False
        return result

    def _get_related_date(self, cr, uid, ids, context=None):
        result = []
        for history in self.browse(cr, uid, ids, context=context):
            cr.execute('''select
                    id
                from
                    project_task_history
                where
                    task_id=%s and
                    id<%s
                order by id desc limit 1''', (history.task_id.id, history.id))
            res = cr.fetchone()
            if res:
                result.append(res[0])
        return result

    _columns = {
        'task_id': fields.many2one('project.task', 'Task', ondelete='cascade', required=True, select=True),
        'type_id': fields.many2one('project.task.type', 'Stage'),
        'state': fields.selection([('draft', 'New'), ('cancelled', 'Cancelled'),('open', 'In Progress'),('pending', 'Pending'), ('done', 'Done')], 'Status'),
        'kanban_state': fields.selection([('normal', 'Normal'),('blocked', 'Blocked'),('done', 'Ready To Pull')], 'Kanban State', required=False),
        'date': fields.date('Date', select=True),
        'end_date': fields.function(_get_date, string='End Date', type="date", store={
            'project.task.history': (_get_related_date, None, 20)
        }),
        'remaining_hours': fields.float('Remaining Time', digits=(16,2)),
        'planned_hours': fields.float('Planned Time', digits=(16,2)),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }
    _defaults = {
        'date': fields.date.context_today,
    }
project_task_history()

class project_task_history_cumulative(osv.osv):
    _name = 'project.task.history.cumulative'
    _table = 'project_task_history_cumulative'
    _inherit = 'project.task.history'
    _auto = False
    _columns = {
        'end_date': fields.date('End Date'),
        'project_id': fields.related('task_id', 'project_id', string='Project', type='many2one', relation='project.project')
    }
    def init(self, cr):
        cr.execute(""" CREATE OR REPLACE VIEW project_task_history_cumulative AS (
            SELECT
                history.date::varchar||'-'||history.history_id::varchar as id,
                history.date as end_date,
                *
            FROM (
                SELECT
                    id as history_id,
                    date+generate_series(0, CAST((coalesce(end_date,DATE 'tomorrow')::date - date)AS integer)-1) as date,
                    task_id, type_id, user_id, kanban_state, state,
                    greatest(remaining_hours,1) as remaining_hours, greatest(planned_hours,1) as planned_hours
                FROM
                    project_task_history
            ) as history
        )
        """)
project_task_history_cumulative()
