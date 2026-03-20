import ast

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    projected_margin = fields.Monetary(compute='_compute_projected_margin', export_string_translation=False)

    def _compute_projected_margin(self):
        all_sale_orders = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]}).sudo().order_id
        margin_per_project = dict(self.env['sale.order']._read_group(
            domain=self._get_sale_orders_domain(all_sale_orders),
            groupby=['project_id'],
            aggregates=['margin:sum'],
        ))
        for project in self:
            project.projected_margin = margin_per_project.get(project, 0.0)

    def action_projected_margin(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sale_margin.action_order_report_projected_margins')
        all_sale_orders_lines = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
        action["domain"] = [("id", "in", all_sale_orders_lines.ids)]
        context = ast.literal_eval(action.get('context', '{}'))
        context.update({'search_default_Customer': 0})
        action['context'] = context
        return action
