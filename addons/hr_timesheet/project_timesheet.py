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

        action = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_timesheet', 'act_hr_timesheet_line_evry1_all_form', context=context).read()[0]
        action['context'] = {
            'default_project_id': ids[0],
            'default_is_timesheet': True,
        }
        action['domain'] = str([('project_id', 'in', ids)])
        return action

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
    }

    _defaults = {
        'progress': 0,
    }


    def onchange_project(self, cr, uid, ids, project_id, context=None):
        result = super(task, self).onchange_project(cr, uid, ids, project_id, context=context)
        if not project_id:
            return result
        if 'value' not in result:
            result['value'] = {}
        project = self.pool['project.project'].browse(cr, uid, project_id, context=context)
        return result


class res_partner(osv.osv):
    _inherit = 'res.partner'
#TODO remove; or move
    def unlink(self, cursor, user, ids, context=None):
        parnter_id=self.pool.get('project.project').search(cursor, user, [('partner_id', 'in', ids)])
        if parnter_id:
            raise UserError(_('You cannot delete a partner which is assigned to project, but you can uncheck the active box.'))
        return super(res_partner,self).unlink(cursor, user, ids,
                context=context)
