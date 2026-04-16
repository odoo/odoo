import ast

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    estimated_cost = fields.Monetary(compute='_compute_estimated_cost', export_string_translation=False)
    estimated_cost_ratio = fields.Float(compute='_compute_estimated_cost', export_string_translation=False)

    def _compute_estimated_cost(self):
        for project in self:
            all_sale_orders_lines = project._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
            total_sold = sum(all_sale_orders_lines.mapped('price_subtotal'))
            project.estimated_cost = sum(all_sale_orders_lines.mapped(lambda line: line.purchase_price * line.product_uom_qty))
            project.estimated_cost_ratio = 100 * (project.estimated_cost / total_sold) if total_sold else 0.0

    def action_estimated_margin(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sale_margin.action_order_report_projected_margins')
        all_sale_orders_lines = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
        action["domain"] = [("id", "in", all_sale_orders_lines.ids)]
        context = ast.literal_eval(action.get('context', '{}'))
        context.update({'search_default_customer': 0})
        action['context'] = context
        return action
