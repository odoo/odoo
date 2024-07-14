# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpReport(models.Model):
    _inherit = 'mrp.report'

    employee_cost = fields.Monetary(
        "Total Employee Cost", readonly=True,
        help="Total cost of employees for manufacturing order")
    unit_employee_cost = fields.Monetary(
        "Average Employee Cost / Unit", readonly=True, group_operator="avg",
        help="Employee Cost per unit produced (in product UoM) of manufacturing order")

    def _select_total_cost(self):
        return super()._select_total_cost() + " + op_cost.total_emp"

    def _select(self):
        extra_select = """
                    , op_cost.total_emp * currency_table.rate                                                                   AS employee_cost,
                    op_cost.total_emp * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * currency_table.rate      AS unit_employee_cost
                """
        return super()._select() + extra_select

    def _join_operations_cost(self):
        return """
            LEFT JOIN (
                SELECT
                    mo_id                                                                    AS mo_id,
                    SUM(op_costs_hour / 60. * op_duration)                                   AS total,
                    SUM(op_duration)                                                         AS total_duration,
                    SUM(emp_costs)                                                           AS total_emp
                FROM (
                    SELECT
                        mo.id AS mo_id,
                        CASE
                            WHEN wo.costs_hour != 0.0 AND wo.costs_hour IS NOT NULL THEN wo.costs_hour
                            ELSE COALESCE(wc.costs_hour, 0.0) END                                       AS op_costs_hour,
                        COALESCE(SUM(t.duration), 0.0)                                                  AS op_duration,
                        COALESCE(SUM(t.duration / 60. * t.employee_cost), 0.0)                                         AS emp_costs
                    FROM mrp_production AS mo
                    LEFT JOIN mrp_workorder wo ON wo.production_id = mo.id
                    LEFT JOIN mrp_workcenter_productivity t ON t.workorder_id = wo.id
                    LEFT JOIN mrp_workcenter wc ON wc.id = t.workcenter_id
                    WHERE mo.state = 'done'
                    GROUP BY
                        mo.id,
                        wc.costs_hour,
                        wo.id
                    ) AS op_cost_vars
                GROUP BY mo_id
            ) op_cost ON op_cost.mo_id = mo.id
        """

    def _group_by(self):
        extra_groupby = """
            , op_cost.total_emp
        """
        return super()._group_by() + extra_groupby
