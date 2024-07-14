# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import SQL


class MrpReport(models.Model):
    _name = 'mrp.report'
    _description = "Manufacturing Report"
    _rec_name = 'production_id'
    _auto = False
    _order = 'date_finished desc'

    id = fields.Integer("", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, required=True)
    production_id = fields.Many2one('mrp.production', "Manufacturing Order", readonly=True)
    date_finished = fields.Datetime('End Date', readonly=True)
    product_id = fields.Many2one('product.product', "Product", readonly=True)
    total_cost = fields.Monetary(
        "Total Cost", readonly=True,
        help="Total cost of manufacturing order (component + operation costs)")
    component_cost = fields.Monetary(
        "Total Component Cost", readonly=True,
        help="Total cost of components for manufacturing order")
    operation_cost = fields.Monetary(
        "Total Operation Cost", readonly=True, groups="mrp.group_mrp_routings",
        help="Total cost of operations for manufacturing order")
    duration = fields.Float(
        "Total Duration of Operations", readonly=True, groups="mrp.group_mrp_routings",
        help="Total duration (minutes) of operations for manufacturing order")

    qty_produced = fields.Float(
        "Quantity Produced", readonly=True,
        help="Total quantity produced in product's UoM")
    qty_demanded = fields.Float(
        "Quantity Demanded", readonly=True,
        help="Total quantity demanded in product's UoM")
    yield_rate = fields.Float(
        "Yield Percentage(%)", readonly=True,
        help="Ratio of quantity produced over quantity demanded")

    # note that unit costs take include subtraction of byproduct cost share
    unit_cost = fields.Monetary(
        "Cost / Unit", readonly=True, group_operator="avg",
        help="Cost per unit produced (in product UoM) of manufacturing order")
    unit_component_cost = fields.Monetary(
        "Component Cost / Unit", readonly=True, group_operator="avg",
        help="Component cost per unit produced (in product UoM) of manufacturing order")
    unit_operation_cost = fields.Monetary(
        "Total Operation Cost / Unit", readonly=True, group_operator="avg",
        groups="mrp.group_mrp_routings",
        help="Operation cost per unit produced (in product UoM) of manufacturing order")
    unit_duration = fields.Float(
        "Duration of Operations / Unit", readonly=True, group_operator="avg",
        groups="mrp.group_mrp_routings",
        help="Operation duration (minutes) per unit produced of manufacturing order")

    byproduct_cost = fields.Monetary(
        "By-Products Total Cost", readonly=True,
        groups="mrp.group_mrp_byproducts")

    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    def _select_total_cost(self):
        return "comp_cost.total + op_cost.total"

    def _select(self):
        select_str = f"""
            SELECT
                min(mo.id)             AS id,
                mo.id                  AS production_id,
                mo.company_id          AS company_id,
                rc.currency_id         AS currency_id,
                mo.date_finished       AS date_finished,
                mo.product_id          AS product_id,
                prod_qty.product_qty   AS qty_produced,
                prod_qty.qty_demanded  AS qty_demanded,
                prod_qty.product_qty / prod_qty.qty_demanded * 100                                                                      AS yield_rate,
                comp_cost.total * currency_table.rate                                                                                   AS component_cost,
                op_cost.total * currency_table.rate                                                                                     AS operation_cost,
                ({self._select_total_cost()}) * currency_table.rate                                                                     AS total_cost,
                op_cost.total_duration                                                                                                  AS duration,
                comp_cost.total * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * currency_table.rate                    AS unit_component_cost,
                op_cost.total * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * currency_table.rate                      AS unit_operation_cost,
                ({self._select_total_cost()}) * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * currency_table.rate      AS unit_cost,
                op_cost.total_duration / prod_qty.product_qty                                                                           AS unit_duration,
                ({self._select_total_cost()}) * cost_share.byproduct_cost_share * currency_table.rate                                   AS byproduct_cost
        """

        return select_str

    def _from(self):
        """ MO costs are quite complicated so the table is built with the following subqueries (per MO):
            1. total component cost (note we cover no components use case)
            2. total operations cost (note we cover no operations use case)
            3. total byproducts cost share
            4. total qty produced based on the product's UoM
        Note subqueries 3 and 4 exist because 3 subqueries use the stock_move table and combining them would result in duplicated SVL values and
        subquery 2 (i.e. the nested subquery) exists to prevent duplication of operation costs (i.e. 2+ comp lines and 2+ operations at diff wc in
        the same MO results in op cost duplication if op cost isn't aggregated first).
        Subqueries will return 0.0 as value whenever value IS NULL to prevent SELECT calculations from being nulled (e.g. there is no cost then
        it is mathematically 0 anyways).
        """
        from_str = """
            FROM mrp_production AS mo
            JOIN res_company AS rc ON rc.id = {company_id}
            {comp_cost}
            {op_cost}
            {byproducts_cost}
            {total_produced}
            LEFT JOIN {currency_table} ON currency_table.company_id = mo.company_id
        """.format(
            currency_table=self.env['res.currency']._get_query_currency_table(self.env.companies.ids, fields.Date.today()),
            company_id=int(self.env.company.id),
            comp_cost=self._join_component_cost(),
            op_cost=self._join_operations_cost(),
            byproducts_cost=self._join_byproducts_cost_share(),
            total_produced=self._join_total_qty_produced()
        )

        return from_str

    def _join_component_cost(self):
        return """
            LEFT JOIN (
                SELECT
                    mo.id                                                                    AS mo_id,
                    COALESCE(ABS(SUM(svl.value)), 0.0)                                       AS total
                FROM mrp_production AS mo
                LEFT JOIN stock_move AS sm on sm.raw_material_production_id = mo.id
                LEFT JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                WHERE mo.state = 'done'
                    AND (sm.state = 'done' or sm.state IS NULL)
                    AND (sm.scrapped != 't' or sm.scrapped IS NULL)
                GROUP BY
                    mo.id
            ) comp_cost ON comp_cost.mo_id = mo.id
        """

    def _join_operations_cost(self):
        return """
            LEFT JOIN (
                SELECT
                    mo_id                                                                    AS mo_id,
                    SUM(op_costs_hour / 60. * op_duration)                                   AS total,
                    SUM(op_duration)                                                         AS total_duration
                FROM (
                    SELECT
                        mo.id AS mo_id,
                        CASE
                            WHEN wo.costs_hour != 0.0 AND wo.costs_hour IS NOT NULL THEN wo.costs_hour
                            ELSE COALESCE(wc.costs_hour, 0.0) END                                       AS op_costs_hour,
                        COALESCE(SUM(t.duration), 0.0)                                                  AS op_duration
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

    def _join_byproducts_cost_share(self):
        return """
            LEFT JOIN (
                SELECT
                    mo.id AS mo_id,
                    COALESCE(SUM(sm.cost_share), 0.0) / 100.0 AS byproduct_cost_share
                FROM stock_move AS sm
                LEFT JOIN mrp_production AS mo ON sm.production_id = mo.id
                WHERE
                    mo.state = 'done'
                    AND sm.state = 'done'
                    AND sm.quantity != 0
                    AND sm.scrapped != 't'
                GROUP BY mo.id
            ) cost_share ON cost_share.mo_id = mo.id
        """

    def _join_total_qty_produced(self):
        return """
            LEFT JOIN (
                SELECT
                    mo.id AS mo_id,
                    mo.name,
                    SUM(sm.quantity / uom.factor * uom_prod.factor) AS product_qty,
                    SUM(sm.product_uom_qty / uom.factor * uom_prod.factor) AS qty_demanded
                FROM stock_move AS sm
                JOIN mrp_production AS mo ON sm.production_id = mo.id
                JOIN uom_uom AS uom ON uom.id = sm.product_uom
                JOIN product_product AS product ON product.id = sm.product_id
                JOIN product_template AS template ON template.id = product.product_tmpl_id
                JOIN uom_uom AS uom_prod ON uom_prod.id = template.uom_id
                WHERE
                    mo.state = 'done'
                    AND sm.state = 'done'
                    AND sm.quantity != 0
                    AND mo.product_id = sm.product_id
                    AND (sm.scrapped != 't' or sm.scrapped IS NULL)
                GROUP BY mo.id
            ) prod_qty ON prod_qty.mo_id = mo.id
        """

    def _where(self):
        where_str = """
            WHERE
                mo.state = 'done'
        """

        return where_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                mo.id,
                rc.currency_id,
                cost_share.byproduct_cost_share,
                comp_cost.total,
                op_cost.total,
                op_cost.total_duration,
                prod_qty.product_qty,
                prod_qty.qty_demanded,
                currency_table.rate
        """

        return group_by_str

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec in ('unit_cost:avg', 'unit_component_cost:avg', 'unit_operation_cost:avg', 'unit_duration:avg'):
            # Make a weigthed average instead of simple average for these fields
            fname, *__ = models.parse_read_group_spec(aggregate_spec)
            sql_field = self._field_to_sql(self._table, fname, query)
            sql_qty_produced = self._field_to_sql(self._table, 'qty_produced', query)
            sql_expr = SQL("SUM(%s * %s) / SUM(%s)", sql_field, sql_qty_produced, sql_qty_produced)
            return sql_expr, [fname, 'qty_produced']
        if aggregate_spec == 'yield_rate:sum':
            sql_qty_produced = self._field_to_sql(self._table, 'qty_produced', query)
            sql_qty_demanded = self._field_to_sql(self._table, 'qty_demanded', query)
            sql_expr = SQL("SUM(%s) / SUM(%s) * 100", sql_qty_produced, sql_qty_demanded)
            return sql_expr, ['yield_rate', 'qty_produced', 'qty_demanded']
        return super()._read_group_select(aggregate_spec, query)
