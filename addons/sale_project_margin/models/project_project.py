from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    estimated_cost = fields.Monetary(compute='_compute_estimated_cost', export_string_translation=False)
    estimated_cost_ratio = fields.Float(compute='_compute_estimated_cost', export_string_translation=False)

    def _compute_estimated_cost(self):
        sale_order_items_per_project_id = self._fetch_sale_order_items_per_project_id({'project.task': [('is_closed', '=', False)]})
        for project in self:
            sale_order_lines = sale_order_items_per_project_id.get(project.id, self.env['sale.order.line']).sudo()
            project_currency = project.currency_id or self.env.company.currency_id
            project_company = project.company_id or self.env.company
            total_sold = 0.0
            estimated_cost = 0.0
            for line in sale_order_lines:
                line_currency = line.currency_id or project_currency
                price_subtotal = line.price_subtotal
                cost = line.purchase_price * line.product_uom_qty
                if line_currency != project_currency:
                    date = line.order_id.date_order
                    if price_subtotal:
                        price_subtotal = line_currency._convert(price_subtotal, project_currency, project_company, date)
                    if cost:
                        cost = line_currency._convert(cost, project_currency, project_company, date)
                total_sold += price_subtotal
                estimated_cost += cost
            project.estimated_cost = estimated_cost
            project.estimated_cost_ratio = (100 * (estimated_cost / total_sold)) if total_sold else 0.0

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
