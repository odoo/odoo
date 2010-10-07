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

from lxml import etree
from mx import DateTime
from mx.DateTime import now
import time
from tools.translate import _

from osv import fields, osv
from tools.translate import _

class project(osv.osv):
    _name = "project.project"
    _description = "Project"

    def _complete_name(self, cr, uid, ids, name, args, context):
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = (m.parent_id and (m.parent_id.name + '/') or '') + m.name
        return res


    def check_recursion(self, cursor, user, ids, parent=None):
        return super(project, self).check_recursion(cursor, user, ids,
                parent=parent)

    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value':{'contact_id': False, 'pricelist_id': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])

        pricelist = self.pool.get('res.partner').browse(cr, uid, part).property_product_pricelist.id
        return {'value':{'contact_id': addr['contact'], 'pricelist_id': pricelist}}

    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        res = {}.fromkeys(ids, 0.0)
        progress = {}
        if not ids:
            return res
        ids2 = self.search(cr, uid, [('parent_id','child_of',ids)])
        if ids2:
            cr.execute('''SELECT
                    project_id, sum(planned_hours), sum(total_hours), sum(effective_hours)
                FROM
                    project_task 
                WHERE
                    project_id in %s AND
                    state<>'cancelled'
                GROUP BY
                    project_id''',
                       (tuple(ids2),))
            progress = dict(map(lambda x: (x[0], (x[1],x[2],x[3])), cr.fetchall()))
        for project in self.browse(cr, uid, ids, context=context):
            s = [0.0,0.0,0.0]
            tocompute = [project]
            while tocompute:
                p = tocompute.pop()
                tocompute += p.child_id
                for i in range(3):
                    s[i] += progress.get(p.id, (0.0,0.0,0.0))[i]
            res[project.id] = {
                'planned_hours': s[0],
                'effective_hours': s[2],
                'total_hours': s[1],
                'progress_rate': s[1] and (100.0 * s[2] / s[1]) or 0.0
            }
        return res

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for proj in self.browse(cr, uid, ids):
            if proj.tasks:
                raise osv.except_osv(_('Operation Not Permitted !'), _('You can not delete a project with tasks. I suggest you to deactivate it.'))
        return super(project, self).unlink(cr, uid, ids, *args, **kwargs)
    _columns = {
        'name': fields.char("Project Name", size=128, required=True),
        'complete_name': fields.function(_complete_name, method=True, string="Project Name", type='char', size=128),
        'active': fields.boolean('Active'),
        'category_id': fields.many2one('account.analytic.account','Analytic Account', help="Link this project to an analytic account if you need financial management on projects. It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc."),
        'priority': fields.integer('Sequence'),
        'manager': fields.many2one('res.users', 'Project Manager'),
        'warn_manager': fields.boolean('Warn Manager', help="If you check this field, the project manager will receive a request each time a task is completed by his team."),
        'members': fields.many2many('res.users', 'project_user_rel', 'project_id', 'uid', 'Project Members', help="Project's member. Not used in any computation, just for information purpose."),
        'tasks': fields.one2many('project.task', 'project_id', "Project tasks"),
        'parent_id': fields.many2one('project.project', 'Parent Project',\
            help="If you have [?] in the name, it means there are no analytic account linked to project."),
        'child_id': fields.one2many('project.project', 'parent_id', 'Subproject'),
        'planned_hours': fields.function(_progress_rate, multi="progress", method=True, string='Planned Time', help="Sum of planned hours of all tasks related to this project."),
        'effective_hours': fields.function(_progress_rate, multi="progress", method=True, string='Time Spent', help="Sum of spent hours of all tasks related to this project."),
        'total_hours': fields.function(_progress_rate, multi="progress", method=True, string='Total Time', help="Sum of total hours of all tasks related to this project."),
        'progress_rate': fields.function(_progress_rate, multi="progress", method=True, string='Progress', type='float', help="Percent of tasks closed according to the total of tasks todo."),
        'date_start': fields.date('Starting Date'),
        'date_end': fields.date('Expected End'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'contact_id': fields.many2one('res.partner.address', 'Contact'),
        'warn_customer': fields.boolean('Warn Partner', help="If you check this, the user will have a popup when closing a task that propose a message to send by email to the customer."),
        'warn_header': fields.text('Mail Header', help="Header added at the beginning of the email for the warning message sent to the customer when a task is closed."),
        'warn_footer': fields.text('Mail Footer', help="Footer added at the beginning of the email for the warning message sent to the customer when a task is closed."),
        'notes': fields.text('Notes', help="Internal description of the project."),
        'timesheet_id': fields.many2one('hr.timesheet.group', 'Working Time', help="Timetable working hours to adjust the gantt diagram report"),
        'state': fields.selection([('template', 'Template'), ('open', 'Running'), ('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'State', required=True, readonly=True),
     }

    _defaults = {
        'active': lambda *a: True,
        'manager': lambda object,cr,uid,context: uid,
        'priority': lambda *a: 1,
        'date_start': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'open'
    }

    _order = "parent_id,priority,name"
    _constraints = [
        (check_recursion, 'Error ! You can not create recursive projects.', ['parent_id'])
    ]

    # toggle activity of projects, their sub projects and their tasks
    def set_template(self, cr, uid, ids, context={}):
        res = self.setActive(cr, uid, ids, value=False, context=context) 
        return res

    def set_done(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        return True

    def set_cancel(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'cancelled'}, context=context)
        return True

    def set_pending(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'pending'}, context=context)
        return True

    def set_open(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True

    def reset_project(self, cr, uid, ids, context={}):
        res = self.setActive(cr, uid, ids,value=True, context=context)
        return res

    def copy(self, cr, uid, id, default={},context={}):
        proj = self.browse(cr, uid, id, context=context)
        default = default or {}
        context['active_test'] = False
        default['state'] = 'open'
        if not default.get('name', False):
            default['name'] = proj.name+_(' (copy)')
        res = super(project, self).copy(cr, uid, id, default, context)
        ids = self.search(cr, uid, [('parent_id','child_of', [res])])
        cr.execute('update project_task set active=True where project_id in %s', (tuple(ids),))
        return res

    def duplicate_template(self, cr, uid, ids,context={}):
        default = {'parent_id': context.get('parent_id',False)}
        for id in ids:
            self.copy(cr, uid, id, default=default)
        cr.commit()
        raise osv.except_osv(_('Operation Done'), _('A new project has been created !\nWe suggest you to close this one and work on this new project.'))

    # set active value for a project, its sub projects and its tasks
    def setActive(self, cr, uid, ids, value=True, context={}):   
        for proj in self.browse(cr, uid, ids, context):            
            self.write(cr, uid, [proj.id], {'state': value and 'open' or 'template'}, context)
            cr.execute('select id from project_task where project_id=%s', (proj.id,))
            tasks_id = [x[0] for x in cr.fetchall()]
            if tasks_id:
                self.pool.get('project.task').write(cr, uid, tasks_id, {'active': value}, context)
            cr.execute('select id from project_project where parent_id=%s', (proj.id,))            
            project_ids = [x[0] for x in cr.fetchall()]            
            for child in project_ids:
                self.setActive(cr, uid, [child], value, context)     		
        return True
project()

class project_task_type(osv.osv):
    _name = 'project.task.type'
    _description = 'Project task type'
    _columns = {
        'name': fields.char('Type', required=True, size=64, translate=True),
        'description': fields.text('Description'),
    }
project_task_type()

class task(osv.osv):
    _name = "project.task"
    _description = "Tasks"
    _date_name = "date_start"
    def _str_get(self, task, level=0, border='***', context={}):
        return border+' '+(task.user_id and task.user_id.name.upper() or '')+(level and (': L'+str(level)) or '')+(' - %.1fh / %.1fh'%(task.effective_hours or 0.0,task.planned_hours))+' '+border+'\n'+ \
            border[0]+' '+(task.name or '')+'\n'+ \
            (task.description or '')+'\n\n'

    def _history_get(self, cr, uid, ids, name, args, context={}):
        result = {}
        for task in self.browse(cr, uid, ids, context=context):
            result[task.id] = self._str_get(task, border='===')
            t2 = task.parent_id
            level = 0
            while t2:
                level -= 1
                result[task.id] = self._str_get(t2, level) + result[task.id]
                t2 = t2.parent_id
            t3 = map(lambda x: (x,1), task.child_ids)
            while t3:
                t2 = t3.pop(0)
                result[task.id] = result[task.id] + self._str_get(t2[0], t2[1])
                t3 += map(lambda x: (x,t2[1]+1), t2[0].child_ids)
        return result

# Compute: effective_hours, total_hours, progress
    def _hours_get(self, cr, uid, ids, field_names, args, context):
        cr.execute("SELECT task_id, COALESCE(SUM(hours),0) FROM project_task_work WHERE task_id in %s GROUP BY task_id", (tuple(ids),))
        hours = dict(cr.fetchall())
        res = {}
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {}
            res[task.id]['effective_hours'] = hours.get(task.id, 0.0)
            res[task.id]['total_hours'] = task.remaining_hours + hours.get(task.id, 0.0)
            if (task.remaining_hours + hours.get(task.id, 0.0)):
                res[task.id]['progress'] = round(min(100.0 * hours.get(task.id, 0.0) / res[task.id]['total_hours'], 100),2)
            else:
                res[task.id]['progress'] = 0.0
            res[task.id]['delay_hours'] = res[task.id]['total_hours'] - task.planned_hours
        return res

    def onchange_planned(self, cr, uid, ids, planned, effective=0.0):
        return {'value':{'remaining_hours': planned-effective}}

    def _default_project(self, cr, uid, context={}):
        if 'project_id' in context and context['project_id']:
            return context['project_id']
        return False

    #_sql_constraints = [
    #    ('remaining_hours', 'CHECK (remaining_hours>=0)', 'Please increase and review remaining hours ! It can not be smaller than 0.'),
    #]
    
    def copy_data(self, cr, uid, id, default={},context={}):
        default = default or {}
        default['work_ids'] = []
        default['remaining_hours'] = float(self.read(cr, uid, id, ['planned_hours'])['planned_hours'])
        return super(task, self).copy_data(cr, uid, id, default, context)

    _columns = {
        'active': fields.boolean('Active'),
        'name': fields.char('Task summary', size=128, required=True),
        'description': fields.text('Description'),
        'priority' : fields.selection([('4','Very Low'), ('3','Low'), ('2','Medium'), ('1','Urgent'), ('0','Very urgent')], 'Importance'),
        'sequence': fields.integer('Sequence'),
        'type': fields.many2one('project.task.type', 'Type'),
        'state': fields.selection([('draft', 'Draft'),('open', 'In Progress'),('pending', 'Pending'), ('cancelled', 'Cancelled'), ('done', 'Done')], 'Status', readonly=True, required=True),
        'date_start': fields.datetime('Starting Date'),
        'date_deadline': fields.datetime('Deadline'),
        'date_close': fields.datetime('Date Closed', readonly=True),
        'project_id': fields.many2one('project.project', 'Project', ondelete='cascade',
            help="If you have [?] in the project name, it means there are no analytic account linked to this project."),
        'parent_id': fields.many2one('project.task', 'Parent Task'),
        'child_ids': fields.one2many('project.task', 'parent_id', 'Delegated Tasks'),
        'history': fields.function(_history_get, method=True, string="Task Details", type="text"),
        'notes': fields.text('Notes'),

        'planned_hours': fields.float('Planned Hours', required=True, help='Estimated time to do the task, usually set by the project manager when the task is in draft state.'),
        'effective_hours': fields.function(_hours_get, method=True, string='Hours Spent', multi='hours', store=True, help="Computed using the sum of the task work done."),
        'remaining_hours': fields.float('Remaining Hours', digits=(16,4), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
        'total_hours': fields.function(_hours_get, method=True, string='Total Hours', multi='hours', store=True, help="Computed as: Time Spent + Remaining Time."),
        'progress': fields.function(_hours_get, method=True, string='Progress (%)', multi='hours', store=True, help="Computed as: Time Spent / Total Time."),
        'delay_hours': fields.function(_hours_get, method=True, string='Delay Hours', multi='hours', store=True, help="Computed as: Total Time - Estimated Time. It gives the difference of the time estimated by the project manager and the real time to close the task."),

        'user_id': fields.many2one('res.users', 'Assigned to'),
        'delegated_user_id': fields.related('child_ids','user_id',type='many2one', relation='res.users', string='Delegated To'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'work_ids': fields.one2many('project.task.work', 'task_id', 'Work done'),
    }
    _defaults = {
        'user_id': lambda obj,cr,uid,context: uid,
        'state': lambda *a: 'draft',
        'priority': lambda *a: '2',
        'progress': lambda *a: 0,
        'sequence': lambda *a: 10,
        'active': lambda *a: True,
        'date_start': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'project_id': _default_project,
    }
    _order = "sequence, priority, date_deadline, id"

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from project_task where id in %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, _('Error ! You cannot create recursive tasks.'), ['parent_id'])
    ]
    #
    # Override view according to the company definition
    #
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False):
        tm = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.project_time_mode or False
        f = self.pool.get('res.company').fields_get(cr, uid, ['project_time_mode'], context)
        word = 'Hours'
        if tm:
            word = dict(f['project_time_mode']['selection'])[tm]

        res = super(task, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar)
        if (not tm) or (tm=='hours'):
            return res
        eview = etree.fromstring(res['arch'])
        def _check_rec(eview, tm):
            if eview.attrib.get('widget',False) == 'float_time':
                eview.set('widget','float')
            for child in eview:
                _check_rec(child, tm)
            return True
        _check_rec(eview, tm)
        res['arch'] = etree.tostring(eview)
        for f in res['fields']:
            if 'Hours' in res['fields'][f]['string']:
                res['fields'][f]['string'] = res['fields'][f]['string'].replace('Hours',word)
        return res

    def do_close(self, cr, uid, ids, *args):
        request = self.pool.get('res.request')
        tasks = self.browse(cr, uid, ids)
        for task in tasks:
            project = task.project_id
            if project:
                if project.warn_manager and project.manager and (project.manager.id != uid):
                    request.create(cr, uid, {
                        'name': _("Task '%s' closed") % task.name,
                        'state': 'waiting',
                        'act_from': uid,
                        'act_to': project.manager.id,
                        'ref_partner_id': task.partner_id.id,
                        'ref_doc1': 'project.task,%d'% (task.id,),
                        'ref_doc2': 'project.project,%d'% (project.id,),
                    })
            self.write(cr, uid, [task.id], {'state': 'done', 'date_close':time.strftime('%Y-%m-%d %H:%M:%S'), 'remaining_hours': 0.0})
            if task.parent_id and task.parent_id.state in ('pending','draft'):
                reopen = True
                for child in task.parent_id.child_ids:
                    if child.id != task.id and child.state not in ('done','cancelled'):
                        reopen = False
                if reopen:
                    self.do_reopen(cr, uid, [task.parent_id.id])
        return True

    def do_reopen(self, cr, uid, ids, *args):
        request = self.pool.get('res.request')
        tasks = self.browse(cr, uid, ids)
        for task in tasks:
            project = task.project_id
            if project and project.warn_manager and project.manager.id and (project.manager.id != uid):
                request.create(cr, uid, {
                    'name': _("Task '%s' set in progress") % task.name,
                    'state': 'waiting',
                    'act_from': uid,
                    'act_to': project.manager.id,
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
            if project.warn_manager and project.manager and (project.manager.id != uid):
                request.create(cr, uid, {
                    'name': _("Task '%s' cancelled") % task.name,
                    'state': 'waiting',
                    'act_from': uid,
                    'act_to': project.manager.id,
                    'ref_partner_id': task.partner_id.id,
                    'ref_doc1': 'project.task,%d' % task.id,
                    'ref_doc2': 'project.project,%d' % project.id,
                })
            self.write(cr, uid, [task.id], {'state': 'cancelled', 'remaining_hours':0.0})
        return True

    def do_open(self, cr, uid, ids, *args):
        tasks= self.browse(cr,uid,ids)
        for t in tasks:
            self.write(cr, uid, [t.id], {'state': 'open'})
        return True

    def do_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        return True


    def do_pending(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'pending'})
        return True


task()

class project_work(osv.osv):
    _name = "project.task.work"
    _description = "Task Work"
    _columns = {
        'name': fields.char('Work summary', size=128),
        'date': fields.datetime('Date'),
        'task_id': fields.many2one('project.task', 'Task', ondelete='cascade', required=True),
        'hours': fields.float('Time Spent'),
        'user_id': fields.many2one('res.users', 'Done by', required=True),
    }
    _defaults = {
        'user_id': lambda obj,cr,uid,context: uid,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')
    }
    _order = "date desc"
    def create(self, cr, uid, vals, *args, **kwargs):
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'task_id' in vals:
            cr.execute('update project_task set remaining_hours=remaining_hours - %s where id=%s', (vals.get('hours',0.0), vals['task_id']))
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids,vals,context={}):
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'hours' in vals:
            for work in self.browse(cr, uid, ids, context):
                cr.execute('update project_task set remaining_hours=remaining_hours - %s + (%s) where id=%s', (vals.get('hours',0.0), work.hours, work.task_id.id))
        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for work in self.browse(cr, uid, ids):
            cr.execute('update project_task set remaining_hours=remaining_hours + %s where id=%s', (work.hours, work.task_id.id))
        return super(project_work,self).unlink(cr, uid, ids,*args, **kwargs)
project_work()

class config_compute_remaining(osv.osv_memory):
    _name='config.compute.remaining'
    def _get_remaining(self,cr, uid, ctx):
        if 'active_id' in ctx:
            return self.pool.get('project.task').browse(cr,uid,ctx['active_id']).remaining_hours
        return False

    _columns = {
        'remaining_hours' : fields.float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
            }

    _defaults = {
        'remaining_hours': _get_remaining
        }
    
    def compute_hours(self, cr, uid, ids, context=None):
        if 'active_id' in context:
            remaining_hrs=self.browse(cr,uid,ids)[0].remaining_hours
            self.pool.get('project.task').write(cr,uid,context['active_id'],{'remaining_hours':remaining_hrs})
        return {
                'type': 'ir.actions.act_window_close',
         }
config_compute_remaining()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

