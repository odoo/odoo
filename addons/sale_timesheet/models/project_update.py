# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_utils, format_amount, formatLang
from odoo.tools.misc import format_duration


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        template_values = super(ProjectUpdate, self)._get_template_values(project)
        services = self._get_services_values(project)
        profitability = self._get_profitability_values(project)
        show_profitability = bool(profitability and profitability.get('analytic_account_id') and (profitability.get('costs') or profitability.get('revenues')))
        show_sold = template_values['project'].allow_billable and len(services.get('data', [])) > 0
        return {
            **template_values,
            'show_sold': show_sold,
            'show_profitability': show_profitability,
            'show_activities': template_values['show_activities'] or show_profitability or show_sold,
            'services': services,
            'profitability': profitability,
            'format_value': lambda value, is_hour: str(round(value, 2)) if not is_hour else format_duration(value),
        }

    @api.model
    def _get_services_values(self, project):
        if not project.allow_billable:
            return {}

        services = []
        sols = self.env['sale.order.line'].search(
            project._get_sale_items_domain([
                ('is_downpayment', '=', False),
            ]),
        )
        product_uom_unit = self.env.ref('uom.product_uom_unit')
        product_uom_hour = self.env.ref('uom.product_uom_hour')
        company_uom = self.env.company.timesheet_encode_uom_id
        for sol in sols:
            #We only want to consider hours and days for this calculation
            is_unit = sol.product_uom == product_uom_unit
            if sol.product_uom.category_id == company_uom.category_id or is_unit:
                product_uom_qty = sol.product_uom._compute_quantity(sol.product_uom_qty, company_uom, raise_if_failure=False)
                qty_delivered = sol.product_uom._compute_quantity(sol.qty_delivered, company_uom, raise_if_failure=False)
                qty_invoiced = sol.product_uom._compute_quantity(sol.qty_invoiced, company_uom, raise_if_failure=False)
                unit = sol.product_uom if is_unit else company_uom
                services.append({
                    'name': sol.with_context(with_price_unit=True).display_name,
                    'sold_value': product_uom_qty,
                    'effective_value': qty_delivered,
                    'remaining_value': product_uom_qty - qty_delivered,
                    'invoiced_value': qty_invoiced,
                    'unit': unit.name,
                    'is_unit': is_unit,
                    'is_hour': unit == product_uom_hour,
                    'sol': sol,
                })

        return {
            'data': services,
            'company_unit_name': company_uom.name,
            'is_hour': company_uom == product_uom_hour,
        }

    @api.model
    def _get_profitability_values(self, project):
        costs_revenues = project.analytic_account_id and project.allow_billable
        if not (self.user_has_groups('project.group_project_manager') and costs_revenues):
            return {}
        profitability_items = project._get_profitability_items(False)
        costs = sum(profitability_items['costs']['total'].values())
        revenues = sum(profitability_items['revenues']['total'].values())
        margin = revenues + costs
        return {
            'analytic_account_id': project.analytic_account_id,
            'costs': costs,
            'costs_formatted': format_amount(self.env, -costs, project.currency_id),
            'revenues': revenues,
            'revenues_formatted': format_amount(self.env, revenues, project.currency_id),
            'margin': margin,
            'margin_formatted': format_amount(self.env, margin, project.currency_id),
            'margin_percentage': formatLang(self.env,
                                            not float_utils.float_is_zero(costs, precision_digits=2) and (margin / -costs) * 100 or 0.0,
                                            digits=0),
        }
