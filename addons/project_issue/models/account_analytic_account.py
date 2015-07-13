# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.exceptions import UserError
from openerp.tools.translate import _


class AccountAnalyticAccount(models.Model):
    _description = 'Analytic Account'
    _inherit = 'account.analytic.account'

    use_issues = fields.Boolean('Issues', help="Check this box to manage customer activities through this project")

    @api.v7
    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(AccountAnalyticAccount, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_issues'] = template.use_issues
        return res

    @api.v8
    @api.onchange('template_id')
    def on_change_template(self):
        if self.template_id:
            res = super(AccountAnalyticAccount, self).on_change_template(template_id=self.template_id.id, date_start=self.date_start)
            if 'value' in res:
                self.use_issues = self.template_id.use_issues
                for key, value in res["value"].iteritems():
                    setattr(self, key, value)

    @api.model
    def _trigger_project_creation(self, vals):
        res = super(AccountAnalyticAccount, self)._trigger_project_creation(vals)
        return res or (vals.get('use_issues') and not 'project_creation_in_progress' in self.env.context)

    @api.multi
    def unlink(self):
        projects = self.env['project.project'].search([('analytic_account_id', 'in', self.ids)])
        for project in projects:
            if project.issue_count:
                raise UserError(_('Please remove existing issues in the project linked to the accounts you want to delete.'))
        return super(AccountAnalyticAccount, self).unlink()
