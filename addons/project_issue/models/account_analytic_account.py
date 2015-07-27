# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class account_analytic_account(osv.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    _columns = {
        'use_issues': fields.boolean('Use Issues', help="Check this box to manage customer activities through this project"),
    }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        res = super(account_analytic_account, self)._trigger_project_creation(cr, uid, vals, context=context)
        return res or (vals.get('use_issues') and not 'project_creation_in_progress' in context)

    def unlink(self, cr, uid, ids, context=None):
        proj_ids = self.pool['project.project'].search(cr, uid, [('analytic_account_id', 'in', ids)])
        has_issues = self.pool['project.issue'].search(cr, uid, [('project_id', 'in', proj_ids)], count=True, context=context)
        if has_issues:
            raise UserError(_('Please remove existing issues in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink(cr, uid, ids, context=context)
