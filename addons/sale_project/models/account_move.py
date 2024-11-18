# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

<<<<<<< 18.0
    def _get_action_per_item(self):
        action = self.env.ref('account.action_move_out_invoice_type').id
        return {invoice.id: action for invoice in self}
||||||| 9e3ad1086a2577d13f307cbfbb33020c4081f37d
    def _compute_analytic_distribution(self):
        # when a project creates an aml, it adds an analytic account to it. the following filter is to save this
        # analytic account from being overridden by analytic default rules and lack thereof
        project_amls = self.filtered(lambda aml: aml.analytic_distribution and any(aml.sale_line_ids.project_id))
        super(AccountMoveLine, self - project_amls)._compute_analytic_distribution()
        project_id = self.env.context.get('project_id')
        if project_id:
            analytic_account = self.env['project.project'].browse(project_id).analytic_account_id
            for line in self:
                line.analytic_distribution = line.analytic_distribution or {analytic_account.id: 100}
=======
    def _compute_analytic_distribution(self):
        # when a project creates an aml, it adds an analytic account to it. the following filter is to save this
        # analytic account from being overridden by analytic default rules and lack thereof
        project_amls = self.filtered(lambda aml: aml.analytic_distribution and any(aml.sale_line_ids.project_id))
        super(AccountMoveLine, self - project_amls)._compute_analytic_distribution()
        project_id = self.env.context.get('project_id')
        if project_id:
            analytic_account = self.env['project.project'].browse(project_id).analytic_account_id
            for line in project_amls:
                line.analytic_distribution = line.analytic_distribution or {analytic_account.id: 100}
>>>>>>> eab95d42e845edc4ea2de8a0c7b7bc9766601f39
