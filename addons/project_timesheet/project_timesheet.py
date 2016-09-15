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
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {
                'effective_hours': 0.0,
                'remaining_hours': task.planned_hours,
                'progress': 100.0 if task.stage_id and task.stage_id.fold else 0.0,
                'total_hours': task.planned_hours,
                'delay_hours': 0.0,
            }
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
        for line in self.pool.get('account.analytic.line').search_read(cr,uid,[('task_id', '!=', False),('id','in',id)], ['task_id'], context=context):
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
    }

    _defaults = {
        'progress': 0,
    }

    def _prepare_delegate_values(self, cr, uid, ids, delegate_data, context=None):
        vals = super(task, self)._prepare_delegate_values(cr, uid, ids, delegate_data, context)
        for task in self.browse(cr, uid, ids, context=context):
            vals[task.id]['planned_hours'] += task.effective_hours
        return vals


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
