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


class project_task_type(osv.osv):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, size=64, translate=True),
        'description': fields.text('Description'),
        'sequence': fields.integer('Sequence'),
    }

    _defaults = {
        'sequence': 1
    }

project_task_type()

class project(osv.osv):
    _name = "project.project"
    _description = "Project"
    _inherits = {'account.analytic.account': "analytic_account_id"}

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if user == 1:
            return super(project, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        if context and context.has_key('user_prefence') and context['user_prefence']:
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
            return {'value':{'contact_id': False, 'pricelist_id': False}}
        addr = partner_obj.address_get(cr, uid, [part], ['contact'])
        pricelist = partner_obj.read(cr, uid, part, ['property_product_pricelist'], context=context)
        pricelist_id = pricelist.get('property_product_pricelist', False) and pricelist.get('property_product_pricelist')[0] or False
        return {'value':{'contact_id': addr['contact'], 'pricelist_id': pricelist_id}}

    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        res = {}.fromkeys(ids, 0.0)
        progress = {}
        if not ids:
            return res
        cr.execute('''SELECT
                project_id, sum(planned_hours), sum(total_hours), sum(effective_hours), SUM(remaining_hours)
            FROM
                project_task
            WHERE
                project_id in %s AND
                state<>'cancelled'
            GROUP BY
                project_id''', (tuple(ids),))
        progress = dict(map(lambda x: (x[0], (x[1],x[2],x[3],x[4])), cr.fetchall()))
        for project in self.browse(cr, uid, ids, context=context):
            s = progress.get(project.id, (0.0,0.0,0.0,0.0))
            res[project.id] = {
                'planned_hours': s[0],
                'effective_hours': s[2],
                'total_hours': s[1],
                'progress_rate': s[1] and round(100.0*s[2]/s[1],2) or 0.0
            }
        return res

    def _get_project_task(self, cr, uid, ids, context=None):
        result = {}
        for task in self.pool.get('project.task').browse(cr, uid, ids, context=context):
            if task.project_id: result[task.project_id.id] = True
        return result.keys()

    def _get_project_work(self, cr, uid, ids, context=None):
        result = {}
        for work in self.pool.get('project.task.work').browse(cr, uid, ids, context=context):
            if work.task_id and work.task_id.project_id: result[work.task_id.project_id.id] = True
        return result.keys()

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for proj in self.browse(cr, uid, ids):
            if proj.tasks:
                raise osv.except_osv(_('Operation Not Permitted !'), _('You can not delete a project with tasks. I suggest you to deactivate it.'))
        return super(project, self).unlink(cr, uid, ids, *args, **kwargs)

    _columns = {
        'complete_name': fields.function(_complete_name, method=True, string="Project Name", type='char', size=250),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the project without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of Projects."),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', help="Link this project to an analytic account if you need financial management on projects. It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.", ondelete="cascade", required=True),
        'priority': fields.integer('Sequence', help="Gives the sequence order when displaying the list of projects"),
        'warn_manager': fields.boolean('Warn Manager', help="If you check this field, the project manager will receive a request each time a task is completed by his team.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),

        'members': fields.many2many('res.users', 'project_user_rel', 'project_id', 'uid', 'Project Members',
            help="Project's members are users who can have an access to the tasks related to this project.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'tasks': fields.one2many('project.task', 'project_id', "Project tasks"),
        'planned_hours': fields.function(_progress_rate, multi="progress", method=True, string='Planned Time', help="Sum of planned hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (lambda self, cr, uid, ids, c={}: ids, ['tasks'], 10),
                'project.task': (_get_project_task, ['planned_hours', 'effective_hours', 'remaining_hours', 'total_hours', 'progress', 'delay_hours','state'], 10),
            }),
        'effective_hours': fields.function(_progress_rate, multi="progress", method=True, string='Time Spent', help="Sum of spent hours of all tasks related to this project and its child projects."),
        'total_hours': fields.function(_progress_rate, multi="progress", method=True, string='Total Time', help="Sum of total hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (lambda self, cr, uid, ids, c={}: ids, ['tasks'], 10),
                'project.task': (_get_project_task, ['planned_hours', 'effective_hours', 'remaining_hours', 'total_hours', 'progress', 'delay_hours','state'], 10),
            }),
        'progress_rate': fields.function(_progress_rate, multi="progress", method=True, string='Progress', type='float', group_operator="avg", help="Percent of tasks closed according to the total of tasks todo."),
        'warn_customer': fields.boolean('Warn Partner', help="If you check this, the user will have a popup when closing a task that propose a message to send by email to the customer.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'warn_header': fields.text('Mail Header', help="Header added at the beginning of the email for the warning message sent to the customer when a task is closed.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'warn_footer': fields.text('Mail Footer', help="Footer added at the beginning of the email for the warning message sent to the customer when a task is closed.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'type_ids': fields.many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', 'Tasks Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
     }
    _order = "sequence"
    _defaults = {
        'active': True,
        'priority': 1,
        'sequence': 10,
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
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("The project '%s' has been closed.") % name
            self.log(cr, uid, id, message)
        return True

    def set_cancel(self, cr, uid, ids, context=None):
        task_obj = self.pool.get('project.task')
        task_ids = task_obj.search(cr, uid, [('project_id', 'in', ids), ('state', '!=', 'done')])
        task_obj.write(cr, uid, task_ids, {'state': 'cancelled', 'date_end':time.strftime('%Y-%m-%d %H:%M:%S'), 'remaining_hours': 0.0})
        self.write(cr, uid, ids, {'state':'cancelled'}, context=context)
        return True

    def set_pending(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        return True

    def set_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True

    def reset_project(self, cr, uid, ids, context=None):
        res = self.setActive(cr, uid, ids, value=True, context=context)
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("The project '%s' has been opened.") % name
            self.log(cr, uid, id, message)
        return res

    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}

        proj = self.browse(cr, uid, id, context=context)
        default = default or {}
        context['active_test'] = False
        default['state'] = 'open'
        if not default.get('name', False):
            default['name'] = proj.name + _(' (copy)')
        res = super(project, self).copy(cr, uid, id, default, context)

        return res

    def duplicate_template(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        project_obj = self.pool.get('project.project')
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
            new_id = project_obj.copy(cr, uid, proj.id, default = {
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

project()

class users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'context_project_id': fields.many2one('project.project', 'Project')
    }
users()

class task(osv.osv):
    _name = "project.task"
    _description = "Task"
    _log_create = True
    _date_name = "date_start"

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
        partner_id=data and data[0].parent_id.partner_id
        if partner_id:
            return {'value':{'partner_id':partner_id.id}}
        return {}
    
    def _default_project(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'project_id' in context and context['project_id']:
            return int(context['project_id'])
        return False

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

    def _check_dates(self, cr, uid, ids, context=None):
        task = self.read(cr, uid, ids[0], ['date_start', 'date_end'])
        if task['date_start'] and task['date_end']:
             if task['date_start'] > task['date_end']:
                 return False
        return True

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
        'active': fields.function(_is_template, method=True, store=True, string='Not a Template Task', type='boolean', help="This field is computed automatically and have the same behavior than the boolean 'active' field: if the task is linked to a template or unactivated project, it will be hidden unless specifically asked."),
        'name': fields.char('Task Summary', size=128, required=True),
        'description': fields.text('Description'),
        'priority': fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Important'), ('0','Very important')], 'Priority'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of tasks."),
        'type_id': fields.many2one('project.task.type', 'Stage'),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', readonly=True, required=True,
                                  help='If the task is created the state is \'Draft\'.\n If the task is started, the state becomes \'In Progress\'.\n If review is needed the task is in \'Pending\' state.\
                                  \n If the task is over, the states is set to \'Done\'.'),
        'create_date': fields.datetime('Create Date', readonly=True,select=True),
        'date_start': fields.datetime('Starting Date',select=True),
        'date_end': fields.datetime('Ending Date',select=True),
        'date_deadline': fields.date('Deadline',select=True),
        'project_id': fields.many2one('project.project', 'Project', ondelete='cascade'),
        'parent_ids': fields.many2many('project.task', 'project_task_parent_rel', 'task_id', 'parent_id', 'Parent Tasks'),
        'child_ids': fields.many2many('project.task', 'project_task_parent_rel', 'parent_id', 'task_id', 'Delegated Tasks'),
        'notes': fields.text('Notes'),
        'planned_hours': fields.float('Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.'),
        'effective_hours': fields.function(_hours_get, method=True, string='Hours Spent', multi='hours', help="Computed using the sum of the task work done.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'remaining_hours': fields.float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
        'total_hours': fields.function(_hours_get, method=True, string='Total Hours', multi='hours', help="Computed as: Time Spent + Remaining Time.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'progress': fields.function(_hours_get, method=True, string='Progress (%)', multi='hours', group_operator="avg", help="Computed as: Time Spent / Total Time.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours','state'], 10),
                'project.task.work': (_get_task, ['hours'], 10),
            }),
        'delay_hours': fields.function(_hours_get, method=True, string='Delay Hours', multi='hours', help="Computed as difference of the time estimated by the project manager and the real time to close the task.",
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
        'id': fields.integer('ID'),
    }

    _defaults = {
        'state': 'draft',
        'priority': '2',
        'progress': 0,
        'sequence': 10,
        'active': True,
        'project_id': _default_project,
        'user_id': lambda obj, cr, uid, context: uid,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'project.task', context=c)
    }

    _order = "sequence,priority, date_start, name, id"

    def _check_recursion(self, cr, uid, ids, context=None):
        obj_task = self.browse(cr, uid, ids[0], context=context)
        parent_ids = [x.id for x in obj_task.parent_ids]
        children_ids = [x.id for x in obj_task.child_ids]

        if (obj_task.id in children_ids) or (obj_task.id in parent_ids):
            return False

        while(ids):
            cr.execute('SELECT DISTINCT task_id '\
                       'FROM project_task_parent_rel '\
                       'WHERE parent_id IN %s', (tuple(ids),))
            child_ids = map(lambda x: x[0], cr.fetchall())
            c_ids = child_ids
            if (list(set(parent_ids).intersection(set(c_ids)))) or (obj_task.id in c_ids):
                return False
            while len(c_ids):
                s_ids = self.search(cr, uid, [('parent_ids', 'in', c_ids)])
                if (list(set(parent_ids).intersection(set(s_ids)))):
                    return False
                c_ids = s_ids
            ids = child_ids
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

    def action_close(self, cr, uid, ids, context=None):
        # This action open wizard to send email to partner or project manager after close task.
        project_id = len(ids) and ids[0] or False
        if not project_id: return False
        task = self.browse(cr, uid, project_id, context=context)
        project = task.project_id
        res = self.do_close(cr, uid, [project_id], context=context)
        if project.warn_manager or project.warn_customer:
           return {
                'name': _('Send Email after close task'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'project.task.close',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy': True,
                'context': {'active_id': task.id}
           }
        return res

    def do_close(self, cr, uid, ids, context=None):
        """
        Close Task
        """
        request = self.pool.get('res.request')
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
                    })

            for parent_id in task.parent_ids:
                if parent_id.state in ('pending','draft'):
                    reopen = True
                    for child in parent_id.child_ids:
                        if child.id != task.id and child.state not in ('done','cancelled'):
                            reopen = False
                    if reopen:
                        self.do_reopen(cr, uid, [parent_id.id])
            vals.update({'state': 'done'})
            vals.update({'remaining_hours': 0.0})
            if not task.date_end:
                vals.update({ 'date_end':time.strftime('%Y-%m-%d %H:%M:%S')})
            self.write(cr, uid, [task.id],vals)
            message = _("The task '%s' is done") % (task.name,)
            self.log(cr, uid, task.id, message)
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
                })

            self.write(cr, uid, [task.id], {'state': 'open'})

        return True

    def do_cancel(self, cr, uid, ids, *args):
        request = self.pool.get('res.request')
        tasks = self.browse(cr, uid, ids)
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
                })
            message = _("The task '%s' is cancelled.") % (task.name,)
            self.log(cr, uid, task.id, message)
            self.write(cr, uid, [task.id], {'state': 'cancelled', 'remaining_hours':0.0})
        return True

    def do_open(self, cr, uid, ids, *args):
        tasks= self.browse(cr,uid,ids)
        for t in tasks:
            data = {'state': 'open'}
            if not t.date_start:
                data['date_start'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self.write(cr, uid, [t.id], data)
            message = _("The task '%s' is opened.") % (t.name,)
            self.log(cr, uid, t.id, message)
        return True

    def do_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        return True

    def do_delegate(self, cr, uid, task_id, delegate_data={}, context=None):
        """
        Delegate Task to another users.
        """
        task = self.browse(cr, uid, task_id, context=context)
        self.copy(cr, uid, task.id, {
            'name': delegate_data['name'],
            'user_id': delegate_data['user_id'],
            'planned_hours': delegate_data['planned_hours'],
            'remaining_hours': delegate_data['planned_hours'],
            'parent_ids': [(6, 0, [task.id])],
            'state': 'draft',
            'description': delegate_data['new_task_description'] or '',
            'child_ids': [],
            'work_ids': []
        }, context=context)
        newname = delegate_data['prefix'] or ''
        self.write(cr, uid, [task.id], {
            'remaining_hours': delegate_data['planned_hours_me'],
            'planned_hours': delegate_data['planned_hours_me'] + (task.effective_hours or 0.0),
            'name': newname,
        }, context=context)
        if delegate_data['state'] == 'pending':
            self.do_pending(cr, uid, [task.id], context)
        else:
            self.do_close(cr, uid, [task.id], context=context)
        user_pool = self.pool.get('res.users')
        delegate_user = user_pool.browse(cr, uid, delegate_data['user_id'], context=context)
        message = _("The task '%s' has been delegated to %s.") % (delegate_data['name'], delegate_user.name)
        self.log(cr, uid, task.id, message)
        return True

    def do_pending(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'pending'})
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("The task '%s' is pending.") % name
            self.log(cr, uid, id, message)
        return True

    def next_type(self, cr, uid, ids, *args):
        for task in self.browse(cr, uid, ids):
            typeid = task.type_id.id
            types = map(lambda x:x.id, task.project_id.type_ids or [])
            if types:
                if not typeid:
                    self.write(cr, uid, task.id, {'type_id': types[0]})
                elif typeid and typeid in types and types.index(typeid) != len(types)-1:
                    index = types.index(typeid)
                    self.write(cr, uid, task.id, {'type_id': types[index+1]})
        return True

    def prev_type(self, cr, uid, ids, *args):
        for task in self.browse(cr, uid, ids):
            typeid = task.type_id.id
            types = map(lambda x:x.id, task.project_id and task.project_id.type_ids or [])
            if types:
                if typeid and typeid in types:
                    index = types.index(typeid)
                    self.write(cr, uid, task.id, {'type_id': index and types[index-1] or False})
        return True

task()

class project_work(osv.osv):
    _name = "project.task.work"
    _description = "Project Task Work"
    _columns = {
        'name': fields.char('Work summary', size=128),
        'date': fields.datetime('Date'),
        'task_id': fields.many2one('project.task', 'Task', ondelete='cascade', required=True),
        'hours': fields.float('Time Spent'),
        'user_id': fields.many2one('res.users', 'Done by', required=True),
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

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
