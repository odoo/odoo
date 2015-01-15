 #-*- coding: utf-8 -*-
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

from openerp.osv import fields,osv,orm
from openerp.tools.translate import _

class project_issue(osv.osv):
    _inherit = 'project.issue'
    _description = 'project issue'

    def _hours_get(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            progress = 0.0
            if issue.task_id:
                progress = issue.task_id.progress
            res[issue.id] = {'progress' : progress}
        return res

    def _get_issue_task(self, cr, uid, task_ids, context=None):
        issues = []
        issue_pool = self.pool.get('project.issue')
        for task in self.pool.get('project.task').browse(cr, uid, task_ids, context=context):
            issues += issue_pool.search(cr, uid, [('task_id','=',task.id)])
        return issues

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
            return {}

        result = super(project_issue, self).on_change_project(cr, uid, ids, project_id, context=context)
        
        project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
        if 'value' not in result:
            result['value'] = {}

        account = project.analytic_account_id
        if account:
            result['value']['analytic_account_id'] = account.id

        return result

    def on_change_account_id(self, cr, uid, ids, account_id, context=None):
        if not account_id:
            return {}

        account = self.pool.get('account.analytic.account').browse(cr, uid, account_id, context=context)
        result = {}

        if account and account.state == 'pending':
            result = {'warning' : {'title' : _('Analytic Account'), 'message' : _('The Analytic Account is pending !')}}
            
        return result


class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'account analytic line'
    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }
