from odoo import api, models
from odoo.tools import format_duration


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
                sols = all_sols.with_context(with_price_unit=True)._read_format([
                    'name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom_id', 'product_id'
                ])
                for sol in sols:
                    if sol['product_uom_id'][1] == 'Hours':
                        sol['product_uom_qty'] = format_duration(sol['product_uom_qty'])
                        sol['qty_delivered'] = format_duration(sol['qty_delivered'])
                        sol['qty_invoiced'] = format_duration(sol['qty_invoiced'])
                section["sol"] = sols
        return template_values
