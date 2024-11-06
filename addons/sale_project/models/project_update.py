from odoo import api, models


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        template_values = super()._get_template_values(project)
        profitability_values = template_values.get('profitability')
        if profitability_values and 'revenues' in profitability_values and 'data' in profitability_values['revenues']:
            for section in profitability_values['revenues']['data']:
                all_sols = self.env['sale.order.line'].sudo().search(
                    project._get_domain_from_section_id(section["id"]),
                )
                section["sol"] = all_sols.with_context(with_price_unit=True)._read_format(['name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom', 'product_id'])
        return template_values

    @api.model
    def _get_profitability_values(self, project):
        if not project.allow_billable:
            return {}, False
        return super()._get_profitability_values(project)
