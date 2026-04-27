# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpReport(models.Model):
    _inherit = 'mrp.report'

    total_cost = fields.Monetary(help="Total cost of manufacturing order (component + operation costs + subcontracting cost)")
    subcontracting_cost = fields.Monetary(
        "Total Subcontracting Cost", readonly=True,
        help="Total cost of subcontracting for manufacturing order")
    unit_subcontracting_cost = fields.Monetary(
        "Total Subcontracting Cost / Unit", readonly=True, aggregator="avg",
        help="Subcontracting cost per unit produced (in product UoM) of manufacturing order")

    def _select_total_cost(self):
        return super()._select_total_cost() + " + sub_cost.total"

    def _select(self):
        extra_select = """ ,
            sub_cost.total * account_currency_table.rate                                                                    AS subcontracting_cost,
            sub_cost.total * (1 - cost_share.byproduct_cost_share) / prod_qty.product_qty * account_currency_table.rate     AS unit_subcontracting_cost

        """
        return super()._select() + extra_select

    def _from(self):
        extra_from = """
            LEFT JOIN (
                SELECT
                    mo.id AS mo_id,
                    COALESCE(SUM(sm_sub_total.total), 0.0) AS total
                FROM mrp_production AS mo
                LEFT JOIN (
                    SELECT
                        sm_fin.production_id,
                        sm_fin.product_id,
                        sm_sub.price_unit * sm_fin.product_qty AS total
                    FROM stock_move AS sm_fin
                    LEFT JOIN stock_move_move_rel AS sm_rel ON sm_rel.move_orig_id = sm_fin.id
                    LEFT JOIN stock_move AS sm_sub ON sm_rel.move_dest_id = sm_sub.id
                    WHERE sm_sub.is_subcontract = 't'
                    GROUP BY sm_fin.production_id, sm_fin.product_id, sm_sub.price_unit, sm_fin.product_qty
                ) AS sm_sub_total ON sm_sub_total.production_id = mo.id AND sm_sub_total.product_id = mo.product_id
                GROUP BY mo.id
            ) sub_cost ON sub_cost.mo_id = mo.id
        """
        return super()._from() + extra_from

    def _group_by(self):
        extra_groupby = """
            , sub_cost.total
        """
        return super()._group_by() + extra_groupby
