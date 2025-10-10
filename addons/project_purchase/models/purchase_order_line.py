# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'order_id.partner_id', 'order_id.project_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        ProjectProject = self.env['project.project']
        for line in self:
            project_id = line._context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.order_id.project_id
            if line.display_type or not project:
                continue
            if line.analytic_distribution:
                applied_root_plans = self.env['account.analytic.account'].browse(
                    list({int(account_id) for ids in line.analytic_distribution for account_id in ids.split(",")})
                ).root_plan_id
                if accounts_to_add := project._get_analytic_accounts().filtered(
                        lambda account: account.root_plan_id not in applied_root_plans
                ):
                    line.analytic_distribution = {
                        f"{account_ids},{','.join(map(str, accounts_to_add.ids))}": percentage
                        for account_ids, percentage in line.analytic_distribution.items()
                    }
            else:
                line.analytic_distribution = project._get_analytic_distribution()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._recompute_recordset(fnames=['analytic_distribution'])
        return lines
