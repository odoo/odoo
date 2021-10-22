# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_utils, format_amount, formatLang


class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        template_values = super(ProjectUpdate, self)._get_template_values(project)
        services = self._get_services_values(project)
        profitability = self._get_profitability_values(project)
        show_sold = template_values['project'].allow_billable and len(services.get('data', [])) > 0
        return {
            **template_values,
            'show_sold': show_sold,
            'show_profitability': bool(profitability),
            'show_activities': template_values['show_activities'] or show_sold or bool(profitability),
            'services': services,
            'profitability': profitability,
        }

    @api.model
    def _get_project_sols(self, project):
        # TODO: remove me in master
        return

    @api.model
    def _get_services_values(self, project):
        if not project.allow_billable:
            return {}
        services = []
        total_sold, total_effective, total_remaining = 0, 0, 0
        sols = project._get_sale_order_lines()
        name_by_sol = dict(sols.name_get())
        product_uom_unit = self.env.ref('uom.product_uom_unit')
        for sol in sols:
            #We only want to consider hours and days for this calculation
            is_unit = sol.product_uom == product_uom_unit
            if sol.product_uom.category_id == self.env.company.timesheet_encode_uom_id.category_id or is_unit:
                product_uom_qty = sol.product_uom._compute_quantity(sol.product_uom_qty, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
                qty_delivered = sol.product_uom._compute_quantity(sol.qty_delivered, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
                services.append({
                    'name': name_by_sol[sol.id] if len(sols.order_id) > 1 else sol.name,
                    'sold_value': product_uom_qty,
                    'effective_value': qty_delivered,
                    'remaining_value': product_uom_qty - qty_delivered,
                    'unit': sol.product_uom.name if is_unit else self.env.company.timesheet_encode_uom_id.name,
                    'is_unit': is_unit,
                    'sol': sol,
                })
                if sol.product_uom.category_id == self.env.company.timesheet_encode_uom_id.category_id:
                    total_sold += product_uom_qty
                    total_effective += qty_delivered
        total_remaining = total_sold - total_effective
        return {
            'data': services,
            'total_sold': total_sold,
            'total_effective': total_effective,
            'total_remaining': total_remaining,
            'company_unit_name': self.env.company.timesheet_encode_uom_id.name,
        }

    @api.model
    def _get_profitability_values(self, project):
        costs_revenues = project.analytic_account_id and project.allow_billable
        if not (self.user_has_groups('project.group_project_manager') and costs_revenues):
            return {}
        profitability = project._get_profitability_common()
        return {
            'analytic_account_id': project.analytic_account_id,
            'costs': format_amount(self.env, -profitability['costs'], self.env.company.currency_id),
            'revenues': format_amount(self.env, profitability['revenues'], self.env.company.currency_id),
            'margin': profitability['margin'],
            'margin_formatted': format_amount(self.env, profitability['margin'], self.env.company.currency_id),
            'margin_percentage': formatLang(self.env,
                                            not float_utils.float_is_zero(profitability['costs'], precision_digits=2) and -(profitability['margin'] / profitability['costs']) * 100 or 0.0,
                                            digits=0),
        }
