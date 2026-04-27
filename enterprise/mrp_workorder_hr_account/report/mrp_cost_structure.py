# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models
from odoo.tools import SQL


class MrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'

    def get_lines(self, productions):
        lines = super().get_lines(productions)
        currency_table = self.env['res.currency']._get_simple_currency_table(self.env.companies)
        employee_times = self.env['mrp.workcenter.productivity'].search([
            ('production_id', 'in', productions.ids),
            ('employee_id', '!=', False),
        ])
        if employee_times:
            query = SQL("""SELECT
                                wo.product_id,
                                emp.name,
                                t.employee_cost,
                                op.id,
                                wo.name,
                                sum(t.duration),
                                account_currency_table.rate
                            FROM mrp_workcenter_productivity t
                            LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
                            LEFT JOIN mrp_routing_workcenter op ON (wo.operation_id = op.id)
                            LEFT JOIN %(currency_table)s ON account_currency_table.company_id = t.company_id
                            LEFT JOIN hr_employee emp ON t.employee_id = emp.id
                            WHERE t.workorder_id IS NOT NULL AND t.employee_id IS NOT NULL AND wo.production_id IN %(production_ids)s
                            GROUP BY product_id, emp.id, op.id, wo.name, t.employee_cost, account_currency_table.rate
                            ORDER BY emp.name
                        """,
                        currency_table=currency_table,
                        production_ids=tuple(productions.ids))
            self.env.cr.execute(query)
            empl_cost_by_product = defaultdict(list)
            for product, employee_name, employee_cost, op_id, wo_name, duration, currency_rate in self.env.cr.fetchall():
                cost = employee_cost * currency_rate
                empl_cost_by_product[product].append([employee_name, op_id, wo_name, duration / 60.0, cost * currency_rate])
            for product_lines in lines:
                empl_cost_line = empl_cost_by_product.get(product_lines['product'].id, [])
                cost = sum((l[-1] * l[-2] for l in empl_cost_line))
                product_lines['operations'] += empl_cost_line
                product_lines['total_cost_operations'] += cost
                product_lines['total_cost'] += cost
        return lines

    def _compute_mo_operation_cost(self, currency_table, Workorders, total_cost_by_mo, operation_cost_by_mo, total_cost_operations, operations):
        query = SQL("""  SELECT
                        wo.production_id,
                        wo.id,
                        op.id,
                        wo.name,
                        wc.name,
                        wo.duration,
                        CASE WHEN wo.costs_hour = 0.0 THEN wc.costs_hour ELSE wo.costs_hour END AS costs_hour,
                        account_currency_table.rate,
                        SUM(t.duration/60.0 * emp.hourly_cost) as employee_total_cost
                    FROM mrp_workcenter_productivity t
                    LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
                    LEFT JOIN hr_employee emp ON (emp.id = t.employee_id)
                    LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id)
                    LEFT JOIN mrp_routing_workcenter op ON (wo.operation_id = op.id)
                    LEFT JOIN %(currency_table)s ON account_currency_table.company_id = t.company_id
                    WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %(workorder_ids)s
                    GROUP BY wo.production_id, wo.id, op.id, wo.name, wc.costs_hour, wc.name, account_currency_table.rate
                    ORDER BY wo.name, wc.name
                    """,
                    currency_table=currency_table,
                    workorder_ids=tuple(Workorders.ids))
        self.env.cr.execute(query)
        for mo_id, dummy_wo_id, op_id, wo_name, wc_name, duration, cost_hour, currency_rate, employee_total_cost in self.env.cr.fetchall():
            cost = duration / 60.0 * cost_hour * currency_rate
            employee_total_cost = employee_total_cost or 0
            total_cost_by_mo[mo_id] += cost + employee_total_cost
            operation_cost_by_mo[mo_id] += cost + employee_total_cost
            total_cost_operations += cost
            operations.append([wc_name, op_id, wo_name, duration / 60.0, cost_hour * currency_rate])

        return total_cost_operations
