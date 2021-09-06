# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_utils, format_amount, formatLang

from collections import defaultdict

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        return {
            **super(ProjectUpdate, self)._get_template_values(project),
            'services': self._get_services_values(project),
            'profitability': self._get_profitability_values(project),
        }

    @api.model
    def _get_project_sols(self, project):
        return self.env['sale.order.line'].search([('order_id', '=', project.sale_order_id.id), ('is_service', '=', True)])

    @api.model
    def _get_services_values(self, project):
        if not project.allow_billable:
            return {}
        services = []
        total_sold_per_uom = defaultdict(float)
        total_effective_per_uom = defaultdict(float)
        total_sold, total_effective, total_remaining = 0, 0, 0
        sols = self._get_project_sols(project)
        for sol in sols:
            #We only want to consider hours and days for this calculation
            if sol.product_uom.category_id == self.env.company.timesheet_encode_uom_id.category_id:
                services.append({
                    'name': sol.name,
                    'uom': sol.product_uom.name,
                    'sold_value': sol.product_uom_qty,
                    'effective_value': sol.qty_delivered,
                    'remaining_value': sol.product_uom_qty - sol.qty_delivered,
                    'sol': sol,
                })
                total_sold_per_uom[sol.product_uom] += sol.product_uom_qty
                total_effective_per_uom[sol.product_uom] += sol.qty_delivered
        total_sold = sum(
            uom._compute_quantity(sol.product_uom_qty, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            for uom, quantity in total_sold_per_uom.items()
        )
        total_effective = sum(
            uom._compute_quantity(sol.product_uom_qty, self.env.company.timesheet_encode_uom_id, raise_if_failure=False)
            for uom, quantity in total_effective_per_uom.items()
        )
        total_remaining = total_sold - total_effective
        return {
            'data': services,
            'total_sold': total_sold,
            'total_effective': total_effective,
            'total_remaining': total_remaining,
        }

    @api.model
    def _get_profitability_values(self, project):
        costs_revenues = project.analytic_account_id and project.allow_billable
        timesheets = project.allow_timesheets and self.user_has_groups('hr_timesheet.group_hr_timesheet_user')
        if not (self.user_has_groups('project.group_project_manager') and (costs_revenues or timesheets)):
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
