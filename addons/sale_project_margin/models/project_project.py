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
        embedded_action_context = self.env.context.get('from_embedded_action', False)
        action = self.env['ir.actions.act_window']._for_xml_id('sale_project_margin.action_project_forecast_margin')
        all_sale_orders_lines = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
        action['display_name'] = self.env._("%(name)s's Forecast Margins", name=self.name)
        action["domain"] = [("id", "in", all_sale_orders_lines.ids)]
        action['context'] = {
            'from_embedded_action': embedded_action_context,
            'search_default_filter_order_date': not embedded_action_context,
        }
        return action
