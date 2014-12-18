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
import time
import datetime

from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _

class project_project(osv.osv):
    _inherit = 'project.project'

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
            FROM project_task
            LEFT JOIN project_task_type ON project_task.stage_id = project_task_type.id
            WHERE project_task.project_id IN %s AND project_task_type.fold = False
            GROUP BY project_id
            """, (tuple(child_parent.keys()),))
        # aggregate results into res
        res = dict([(id, {'planned_hours':0.0, 'total_hours':0.0, 'effective_hours':0.0}) for id in ids])
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

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        res = super(project_project, self).onchange_partner_id(cr, uid, ids, part, context)
        if part and res and ('value' in res):
            # set Invoice Task Work to 100%
            data_obj = self.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, uid, 'hr_timesheet_invoice', 'timesheet_invoice_factor1')
            if data_id:
                factor_id = data_obj.browse(cr, uid, data_id).res_id
                res['value'].update({'to_invoice': factor_id})
        return res

    _columns = {
        'planned_hours': fields.function(_progress_rate, multi="progress", string='Planned Time', help="Sum of planned hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'timesheet_ids', 'stage_id'], 20),
            }),
        'effective_hours': fields.function(_progress_rate, multi="progress", string='Time Spent', help="Sum of spent hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'timesheet_ids', 'stage_id'], 20),
            }),
        'total_hours': fields.function(_progress_rate, multi="progress", string='Total Time', help="Sum of total hours of all tasks related to this project and its child projects.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'timesheet_ids', 'stage_id'], 20),
            }),
        'progress_rate': fields.function(_progress_rate, multi="progress", string='Progress', type='float', group_operator="avg", help="Percent of tasks closed according to the total of tasks todo.",
            store = {
                'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
                'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'timesheet_ids', 'stage_id'], 20),
            }),
    }

    _defaults = {
        'invoice_on_timesheets': True,
    }

    def open_timesheets(self, cr, uid, ids, context=None):
        """ open Timesheets view """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        project = self.browse(cr, uid, ids[0], context)
        view_context = {
            'search_default_account_id': [project.analytic_account_id.id],
            'default_account_id': project.analytic_account_id.id,
        }
        help = _("""<p class="oe_view_nocontent_create">Record your timesheets for the project '%s'.</p>""") % (project.name,)
        try:
            if project.to_invoice and project.partner_id:
                help+= _("""<p>Timesheets on this project may be invoiced to %s, according to the terms defined in the contract.</p>""" ) % (project.partner_id.name,)
        except:
            # if the user do not have access rights on the partner
            pass

        res = mod_obj.get_object_reference(cr, uid, 'hr_timesheet', 'act_hr_timesheet_line_evry1_all_form')
        id = res and res[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['name'] = _('Timesheets')
        result['context'] = view_context
        result['help'] = help
        return result

class hr_analytic_timesheet(osv.Model):
    _inherit = 'hr.analytic.timesheet'
    _description = 'hr analytic timesheet'
    _columns = {
        'task_id' : fields.many2one('project.task', 'Task'),
    }

class task(osv.osv):
    _inherit = "project.task"
    _description = 'project task'

    # Compute: effective_hours, total_hours, progress
    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        cr.execute("SELECT t.task_id, SUM(l.unit_amount) FROM hr_analytic_timesheet t, account_analytic_line l \
                WHERE l.id = t.line_id AND t.task_id IN %s GROUP BY t.task_id", (tuple(ids),))
        hours = dict(cr.fetchall())
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {'effective_hours': hours.get(task.id, 0.0), 'remaining_hours': task.planned_hours - hours.get(task.id, 0.0)}
            res[task.id]['total_hours'] = res[task.id]['remaining_hours'] + hours.get(task.id, 0.0)
            res[task.id]['delay_hours'] = res[task.id]['total_hours'] - task.planned_hours
            res[task.id]['progress'] = 0.0
            if (task.remaining_hours + hours.get(task.id, 0.0)):
                res[task.id]['progress'] = round(min(100.0 * hours.get(task.id, 0.0) / res[task.id]['total_hours'], 99.99),2)
            # TDE CHECK: if task.state in ('done','cancelled'):
            if task.stage_id and task.stage_id.fold:
                res[task.id]['progress'] = 100.0
        return res

    def _get_task(self, cr, uid, line_id, context=None):
        result = {}
        for work in self.pool.get('hr.analytic.timesheet').browse(cr, uid, line_id, context=context):
            if work.task_id: result[work.task_id.id] = True
        return result.keys()

    _columns = {
        'remaining_hours': fields.function(_hours_get, string='Remaining Hours', multi='line_id', help="Total remaining time, can be re-estimated periodically by the assignee of the task.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'hr.analytic.timesheet': (_get_task, ['line_id'], 10),
            }),
        'effective_hours': fields.function(_hours_get, string='Hours Spent', multi='line_id', help="Computed using the sum of the task work done.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'hr.analytic.timesheet': (_get_task, ['line_id'], 10),
            }),
        'total_hours': fields.function(_hours_get, string='Total', multi='line_id', help="Computed as: Time Spent + Remaining Time.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'hr.analytic.timesheet': (_get_task, ['line_id'], 10),
            }),
        'progress': fields.function(_hours_get, string='Working Time Progress (%)', multi='line_id', group_operator="avg", help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours', 'state', 'stage_id'], 10),
                'hr.analytic.timesheet': (_get_task, ['line_id'], 10),
            }),
        'delay_hours': fields.function(_hours_get, string='Delay Hours', multi='line_id', help="Computed as difference between planned hours by the project manager and the total hours of the task.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'hr.analytic.timesheet': (_get_task, ['line_id'], 10),
            }),
        'timesheet_ids': fields.one2many('hr.analytic.timesheet', 'task_id', 'Timesheets'),
        'analytic_account_id': fields.related('project_id', 'analytic_account_id',
                    type='many2one', relation='account.analytic.account',string='Analytic Account', store=True),
    }

    _defaults = {
        'progress': 0,
    }

    def _get_effective_hours(self, task):
        return task.effective_hours

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def unlink(self, cursor, user, ids, context=None):
        parnter_id=self.pool.get('project.project').search(cursor, user, [('partner_id', 'in', ids)])
        if parnter_id:
            raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a partner which is assigned to project, but you can uncheck the active box.'))
        return super(res_partner,self).unlink(cursor, user, ids,
                context=context)


class account_analytic_line(osv.osv):
   _inherit = "account.analytic.line"

   def get_product(self, cr, uid, context=None):
        emp_obj = self.pool.get('hr.employee')
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if emp_ids:
            employee = emp_obj.browse(cr, uid, emp_ids, context=context)[0]
            if employee.product_id:return employee.product_id.id
        return False
   
   _defaults = {'product_id': get_product,}
   
   def on_change_account_id(self, cr, uid, ids, account_id):
       res = {}
       if not account_id:
           return res
       res.setdefault('value',{})
       acc = self.pool.get('account.analytic.account').browse(cr, uid, account_id)
       st = acc.to_invoice.id
       res['value']['to_invoice'] = st or False
       if acc.state == 'close' or acc.state == 'cancelled':
           raise osv.except_osv(_('Invalid Analytic Account!'), _('You cannot select a Analytic Account which is in Close or Cancelled state.'))
       return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
