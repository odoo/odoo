from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_above_budget = fields.Boolean('Is Above Budget', compute='_compute_above_budget')
    is_analytic = fields.Boolean('Is Analytic', compute='_compute_is_analytic')

    @api.depends('order_line.analytic_distribution')
    def _compute_is_analytic(self):
        for order in self:
            order.is_analytic = any(order.order_line.mapped('analytic_distribution'))

    @api.depends('order_line.budget_line_ids', 'order_line.price_unit', 'order_line.product_qty', 'order_line.qty_invoiced', 'state')
    def _compute_above_budget(self):
        for order in self:
            uncommitted_amount = sum(
                line.price_unit * (line.product_qty - line.qty_invoiced)
                for line in order.order_line if line.budget_line_ids
            ) if order.state not in ('purchase', 'done') else 0
            order.is_above_budget = any(
                budget.committed_amount + uncommitted_amount > budget.budget_amount
                for budget in order.order_line.mapped('budget_line_ids')
            )

    def action_budget(self):
        self.ensure_one()
        analytic_account_ids = [
            int(account)
            for line in self.order_line
            for account_ids in (line.analytic_distribution or {})
            for account in account_ids.split(',')
        ]
        action = self.env["ir.actions.actions"]._for_xml_id("account_budget.budget_report_action")
        action['domain'] = [('auto_account_id', 'in', analytic_account_ids), ('budget_analytic_id.budget_type', '!=', 'revenue')]
        return action
