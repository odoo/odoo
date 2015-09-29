 #-*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.analytic.models import analytic
from openerp.osv import fields,osv,orm
from openerp.tools.translate import _

class project_issue(osv.osv):
    _inherit = 'project.issue'
    _description = 'project issue'

    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            res[issue.id] = { 'progress' : issue.task_id.progress or 0.0 }
        return res

    def _get_issue_task(self, cr, uid, task_ids, context=None):
        return self.pool['project.issue'].search(cr, uid, [('task_id', 'in', task_ids)], context=context)

    _columns = {
        'progress': fields.function(_hours_get, string='Progress (%)', multi='line_id', group_operator="avg", help="Computed as: Time Spent / Total Time.",
            store = {
                'project.issue': (lambda self, cr, uid, ids, c={}: ids, ['task_id'], 10),
                'project.task': (_get_issue_task, ['progress'], 10),
            }),
        'timesheet_ids': fields.one2many('account.analytic.line', 'issue_id', 'Timesheets'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'), 
    }
    
    def on_change_project(self, cr, uid, ids, project_id, context=None):
        if not project_id:
            return {'value': {'analytic_account_id': False}}

        result = super(project_issue, self).on_change_project(cr, uid, ids, project_id, context=context)
        
        project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
        if 'value' not in result:
            result['value'] = {}

        account = project.analytic_account_id
        if account:
            result['value']['analytic_account_id'] = account.id

        return result


class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'account analytic line'
    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }
