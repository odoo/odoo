# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.analytic.models import analytic
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

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
        res = dict([(id, {'planned_hours': 0.0, 'total_hours': 0.0, 'effective_hours': 0.0}) for id in ids])
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
            'default_is_timesheet':True
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

    def open_contract(self, cr, uid, ids, context=None):
        """ open Contract view """

        res = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'project_timesheet', 'action_project_analytic_account', context=context)
        contract_ids = self.browse(cr, uid, ids, context=context)
        account_ids = [x.analytic_account_id.id for x in contract_ids]
        res['res_id'] = account_ids and account_ids[0] or None
        return res


class task(osv.osv):
    _inherit = "project.task"

    # Compute: effective_hours, total_hours, progress
    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        tasks_data = self.pool['account.analytic.line'].read_group(cr, uid, [('task_id', 'in', ids)], ['task_id','unit_amount'], ['task_id'], context=context)
        for data in tasks_data:
            task = self.browse(cr, uid, data['task_id'][0], context=context)
            res[data['task_id'][0]] = {'effective_hours': data.get('unit_amount', 0.0), 'remaining_hours': task.planned_hours - data.get('unit_amount', 0.0)}
            res[data['task_id'][0]]['total_hours'] = res[data['task_id'][0]]['remaining_hours'] + data.get('unit_amount', 0.0)
            res[data['task_id'][0]]['delay_hours'] = res[data['task_id'][0]]['total_hours'] - task.planned_hours
            res[data['task_id'][0]]['progress'] = 0.0
            if (task.planned_hours > 0.0 and data.get('unit_amount', 0.0)):
                res[data['task_id'][0]]['progress'] = round(min(100.0 * data.get('unit_amount', 0.0) / task.planned_hours, 99.99),2)
            # TDE CHECK: if task.state in ('done','cancelled'):
            if task.stage_id and task.stage_id.fold:
                res[data['task_id'][0]]['progress'] = 100.0
        return res

    def _get_task(self, cr, uid, id, context=None):
        res = []
        for line in self.pool.get('account.analytic.line').search_read(cr,uid,[('task_id', '!=', False),('id','in',id)], context=context):
            res.append(line['task_id'][0])
        return res

    def _get_total_hours(self):
        return super(task, self)._get_total_hours() + self.effective_hours

    _columns = {
        'remaining_hours': fields.function(_hours_get, string='Remaining Hours', multi='line_id', help="Total remaining time, can be re-estimated periodically by the assignee of the task.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
            }),
        'effective_hours': fields.function(_hours_get, string='Hours Spent', multi='line_id', help="Computed using the sum of the task work done.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
            }),
        'total_hours': fields.function(_hours_get, string='Total', multi='line_id', help="Computed as: Time Spent + Remaining Time.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
            }),
        'progress': fields.function(_hours_get, string='Working Time Progress (%)', multi='line_id', group_operator="avg", help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours', 'state', 'stage_id'], 10),
                'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
            }),
        'delay_hours': fields.function(_hours_get, string='Delay Hours', multi='line_id', help="Computed as difference between planned hours by the project manager and the total hours of the task.",
            store = {
                'project.task': (lambda self, cr, uid, ids, c={}: ids, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
                'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
            }),
        'timesheet_ids': fields.one2many('account.analytic.line', 'task_id', 'Timesheets'),
        'analytic_account_id': fields.related('project_id', 'analytic_account_id',
            type='many2one', relation='account.analytic.account', string='Analytic Account', store=True),
        'contract_state': fields.related('project_id', 'analytic_account_id', 'state', relation="account.analytic.account", string='Contract Status', type='selection', selection=analytic.ANALYTIC_ACCOUNT_STATE),
    }

    _defaults = {
        'progress': 0,
    }

    def _prepare_delegate_values(self, cr, uid, ids, delegate_data, context=None):
        vals = super(task, self)._prepare_delegate_values(cr, uid, ids, delegate_data, context)
        for task in self.browse(cr, uid, ids, context=context):
            vals[task.id]['planned_hours'] += task.effective_hours
        return vals

    def onchange_project(self, cr, uid, ids, project_id, context=None):
        result = super(task, self).onchange_project(cr, uid, ids, project_id, context=context)
        if not project_id:
            return result
        if 'value' not in result:
            result['value'] = {}
        project = self.pool['project.project'].browse(cr, uid, project_id, context=context)
        result['value']['contract_state'] = project.analytic_account_id.state
        return result


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def unlink(self, cursor, user, ids, context=None):
        parnter_id=self.pool.get('project.project').search(cursor, user, [('partner_id', 'in', ids)])
        if parnter_id:
            raise UserError(_('You cannot delete a partner which is assigned to project, but you can uncheck the active box.'))
        return super(res_partner,self).unlink(cursor, user, ids,
                context=context)

class account_analytic_line(osv.osv):
    _inherit = "account.analytic.line"
    _columns = {
        'task_id' : fields.many2one('project.task', 'Task'),
    }
