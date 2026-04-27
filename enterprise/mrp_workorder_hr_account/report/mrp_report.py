# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpReport(models.Model):
    _inherit = 'mrp.report'

    employee_cost = fields.Monetary(
        "Total Employee Cost", readonly=True, groups="mrp.group_mrp_routings",
        help="Total cost of employees for manufacturing order")
    unit_employee_cost = fields.Monetary(
        "Average Employee Cost / Unit", readonly=True, aggregator="avg", groups="mrp.group_mrp_routings",
        help="Employee Cost per unit produced (in product UoM) of manufacturing order")

    def _select_total_cost(self):
        return super()._select_total_cost() + " + op_cost.total_emp"

    def _select(self):
        extra_select = """
                    , op_cost.total_emp * account_currency_table.rate                                                                   AS employee_cost,
                    op_cost.total_emp * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * account_currency_table.rate      AS unit_employee_cost
                """
        return super()._select() + extra_select

    def _expected_component_cost(self):
        return """
            , AVG(COALESCE(product_standard_price.value,0))              AS expected_component_cost_unit
            """

    def _expected_employee_cost(self):
        return """
            , AVG(COALESCE(operation.employee_cost,0))                   AS expected_employee_cost_unit
            """

    def _expected_operation_cost(self):
        return """
            , AVG(COALESCE(operation.workcenter_cost,0))                 AS expected_operation_cost_unit
            """

    def _expected_total_cost(self):
        return """
            ,
                AVG(
                    COALESCE(product_standard_price.value,0) +
                    COALESCE(operation.employee_cost,0) +
                    COALESCE(operation.workcenter_cost,0)
                )                                                          AS expected_total_cost_unit
            """

    def _from(self):
        res = super()._from()
        res += f"""
            {self._join_expected_operation_cost_unit()}
        """
        return res

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

    def _join_expected_operation_cost_unit(self):
        return f"""
            LEFT JOIN (
                SELECT
                    MIN(mo.id)                                                                  AS mo_id,
                    SUM(
                        {self._get_expected_duration()} * wc.costs_hour
                    )                                                                           AS workcenter_cost,
                    SUM(
                        {self._get_expected_duration()} * wc.employee_costs_hour * op.employee_ratio
                    )                                                                           AS employee_cost
                FROM mrp_production                                                             AS mo
                JOIN mrp_bom                                                                    AS bom
                    ON mo.bom_id = bom.id
                JOIN mrp_routing_workcenter                                                     AS op
                    ON op.bom_id = bom.id
                JOIN mrp_workcenter                                                             AS wc
                    ON wc.id = op.workcenter_id
                LEFT JOIN mrp_workcenter_capacity                                               AS cap
                    ON cap.product_id = bom.product_tmpl_id
                    AND cap.workcenter_id = wc.id
                    AND mo.state = 'done'
                GROUP BY mo.id
            ) operation
                ON operation.mo_id = mo.id
        """

    def _get_expected_duration(self):
        return f"""
            (
                (
                    (
                        ({self._get_operation_time_cycle()})
                        * 100 / wc.time_efficiency
                    )
                    + COALESCE(cap.time_start, COALESCE(wc.time_start,0))
                    + COALESCE(cap.time_stop, COALESCE(wc.time_stop,0))
                )
                / 60
            )
        """

    def _get_operation_time_cycle(self):
        return """
            WITH cycle_info AS (
                SELECT
                    SUM(wo.duration)                                            AS total_duration,
                    SUM(
                        COALESCE(
                            CEIL(
                                wo.qty_produced
                                / COALESCE(cap.capacity,wc.default_capacity)
                            ),
                            1
                        )
                    )                                                           AS cycle_number
                FROM mrp_workorder                                              AS wo
                JOIN mrp_workcenter                                             AS wc
                    ON wc.id = wo.workcenter_id
                LEFT JOIN mrp_workcenter_capacity                               AS cap
                    ON cap.workcenter_id = wc.id
                        AND cap.product_id = bom.product_tmpl_id
                WHERE wo.operation_id = op.id
                    AND wo.qty_produced > 0
                    AND wo.state = 'done'
                GROUP BY op.id
            )
            SELECT
                CASE
                    WHEN op.time_mode = 'manual'        THEN op.time_cycle_manual
                    WHEN cycle_info.cycle_number = 0    THEN op.time_cycle_manual
                    ELSE cycle_info.total_duration / cycle_info.cycle_number
                END
            FROM cycle_info
        """

    def _group_by(self):
        extra_groupby = """
            , op_cost.total_emp
        """
        return super()._group_by() + extra_groupby
