# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    use_issues = fields.Boolean(string='Use Issues', help="Check this box to manage customer activities through this project")

    @api.multi
    def unlink(self):
        if self.env['project.issue'].search_count([('project_id.analytic_account_id', 'in', self.ids)]):
            raise UserError(_('Please remove existing issues in the project linked to the accounts you want to delete.'))
        return super(AccountAnalyticAccount, self).unlink()

    @api.model
    def _trigger_project_creation(self, vals):
        res = super(AccountAnalyticAccount, self)._trigger_project_creation(vals)
        return res or (vals.get('use_issues') and not 'project_creation_in_progress' in self.env.context)
