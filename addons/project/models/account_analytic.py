# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'
    _columns = {
        'use_tasks': fields.boolean('Tasks', help="Check this box to manage internal activities through this project"),
        'company_uom_id': fields.related('company_id', 'project_time_mode_id', string="Company UOM", type='many2one', relation='product.uom'),
    }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_tasks'] = template.use_tasks
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        if context is None: context = {}
        return vals.get('use_tasks') and not 'project_creation_in_progress' in context

    @api.cr_uid_id_context
    def project_create(self, cr, uid, analytic_account_id, vals, context=None):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        project_pool = self.pool.get('project.project')
        project_id = project_pool.search(cr, uid, [('analytic_account_id','=', analytic_account_id)])
        if not project_id and self._trigger_project_creation(cr, uid, vals, context=context):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': analytic_account_id,
                'use_tasks': True,
            }
            return project_pool.create(cr, uid, project_values, context=context)
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
            vals['child_ids'] = []
        analytic_account_id = super(account_analytic_account, self).create(cr, uid, vals, context=context)
        self.project_create(cr, uid, analytic_account_id, vals, context=context)
        return analytic_account_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        vals_for_project = vals.copy()
        for account in self.browse(cr, uid, ids, context=context):
            if not vals.get('name'):
                vals_for_project['name'] = account.name
            self.project_create(cr, uid, account.id, vals_for_project, context=context)
        return super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        proj_ids = self.pool['project.project'].search(cr, uid, [('analytic_account_id', 'in', ids)])
        has_tasks = self.pool['project.task'].search(cr, uid, [('project_id', 'in', proj_ids)], count=True, context=context)
        if has_tasks:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink(cr, uid, ids, context=context)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if context is None:
            context={}
        if context.get('current_model') == 'project.project':
            project_ids = self.search(cr, uid, args + [('name', operator, name)], limit=limit, context=context)
            return self.name_get(cr, uid, project_ids, context=context)

        return super(account_analytic_account, self).name_search(cr, uid, name, args=args, operator=operator, context=context, limit=limit)
