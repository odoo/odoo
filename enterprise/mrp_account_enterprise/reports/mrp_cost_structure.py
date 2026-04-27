# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models
from odoo.tools import float_round, SQL


class MrpCostStructure(models.AbstractModel):
    _name = 'report.mrp_account_enterprise.mrp_cost_structure'
    _description = 'MRP Cost Structure Report'

    def get_lines(self, productions):
        ProductProduct = self.env['product.product']
        StockMove = self.env['stock.move']
        res = []
        currency_table = self.env['res.currency']._get_simple_currency_table(self.env.companies)
        for product in productions.mapped('product_id'):
            mos = productions.filtered(lambda m: m.product_id == product)
            # variables to calc cost share (i.e. between products/byproducts) since MOs can have varying distributions
            total_cost_by_mo = defaultdict(float)
            component_cost_by_mo = defaultdict(float)
            operation_cost_by_mo = defaultdict(float)

            # Get operations details + cost
            operations = []
            total_cost_operations = 0.0
            Workorders = self.env['mrp.workorder'].search([('production_id', 'in', mos.ids)])
            if Workorders:
                total_cost_operations = self._compute_mo_operation_cost(currency_table, Workorders, total_cost_by_mo, operation_cost_by_mo, total_cost_operations, operations)

            # Get the cost of raw material effectively used
            raw_material_moves = {}
            total_cost_components = 0.0
            query = SQL("""SELECT
                                sm.product_id,
                                mo.id,
                                abs(SUM(svl.quantity)),
                                abs(SUM(svl.value)),
                                account_currency_table.rate
                             FROM stock_move AS sm
                       INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                       LEFT JOIN mrp_production AS mo on sm.raw_material_production_id = mo.id
                       LEFT JOIN %(currency_table)s ON account_currency_table.company_id = mo.company_id
                            WHERE sm.raw_material_production_id in %(mos_ids)s AND sm.state != 'cancel' AND sm.product_qty != 0 AND scrapped != 't'
                         GROUP BY sm.product_id, mo.id, account_currency_table.rate""",
                        currency_table=currency_table,
                        mos_ids=tuple(mos.ids))
            self.env.cr.execute(query)
            for product_id, mo_id, qty, cost, currency_rate in self.env.cr.fetchall():
                cost *= currency_rate
                if product_id in raw_material_moves:
                    product_moves = raw_material_moves[product_id]
                    product_moves['cost'] += cost
                    product_moves['qty'] += qty
                else:
                    raw_material_moves[product_id] = {
                    'qty': qty,
                    'cost': cost,
                    'product_id': ProductProduct.browse(product_id),
                }
                total_cost_by_mo[mo_id] += cost
                component_cost_by_mo[mo_id] += cost
                total_cost_components += cost
            raw_material_moves = list(raw_material_moves.values())
            # Get the cost of scrapped materials

            scraps = StockMove.search([
                '|',
                ('production_id', 'in', mos.ids),
                ('raw_material_production_id', 'in', mos.ids),
                ('scrapped', '=', True),
                ('state', '=', 'done')
            ])
            # Get the byproducts and their total + avg per uom cost share amounts
            total_cost_by_product = defaultdict(float)
            qty_by_byproduct = defaultdict(float)
            qty_by_byproduct_w_costshare = defaultdict(float)
            component_cost_by_product = defaultdict(float)
            operation_cost_by_product = defaultdict(float)
            # tracking consistent uom usage across each byproduct when not using byproduct's product uom is too much of a pain
            # => calculate byproduct qtys/cost in same uom + cost shares (they are MO dependent)
            byproduct_moves = mos.move_byproduct_ids.filtered(lambda m: m.state != 'cancel')
            for move in byproduct_moves:
                qty_by_byproduct[move.product_id] += move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
                # byproducts w/o cost share shouldn't be included in cost breakdown
                if move.cost_share != 0:
                    qty_by_byproduct_w_costshare[move.product_id] += move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
                    cost_share = move.cost_share / 100
                    total_cost_by_product[move.product_id] += total_cost_by_mo[move.production_id.id] * cost_share
                    component_cost_by_product[move.product_id] += component_cost_by_mo[move.production_id.id] * cost_share
                    operation_cost_by_product[move.product_id] += operation_cost_by_mo[move.production_id.id] * cost_share

            # Get product qty and its relative total + avg per uom cost share amount
            uom = product.uom_id
            mo_qty = 0
            for m in mos:
                cost_share = float_round(1 - sum(m.move_finished_ids.mapped('cost_share')) / 100, precision_rounding=0.0001)
                total_cost_by_product[product] += total_cost_by_mo[m.id] * cost_share
                component_cost_by_product[product] += component_cost_by_mo[m.id] * cost_share
                operation_cost_by_product[product] += operation_cost_by_mo[m.id] * cost_share
                for move in m.move_finished_ids:
                    if move.state != 'done' or move.product_id != product:
                        continue
                    mo_qty += move.product_uom._compute_quantity(move.quantity, m.product_id.uom_id)
            res.append({
                'product': product,
                'mo_qty': mo_qty,
                'mo_uom': uom,
                'operations': operations,
                'currency': self.env.company.currency_id,
                'raw_material_moves': raw_material_moves,
                'total_cost_components': total_cost_components,
                'total_cost_operations': total_cost_operations,
                'total_cost': total_cost_components + total_cost_operations,
                'scraps': scraps,
                'mocount': len(mos),
                'byproduct_moves': byproduct_moves,
                'component_cost_by_product': component_cost_by_product,
                'operation_cost_by_product': operation_cost_by_product,
                'qty_by_byproduct': qty_by_byproduct,
                'qty_by_byproduct_w_costshare': qty_by_byproduct_w_costshare,
                'total_cost_by_product': total_cost_by_product
            })
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        productions = self.env['mrp.production']\
            .browse(docids)\
            .filtered(lambda p: p.state != 'cancel')
        res = None
        if all(production.state == 'done' for production in productions):
            res = self.get_lines(productions)
        return {'lines': res}

    def _compute_mo_operation_cost(self, currency_table, Workorders, total_cost_by_mo, operation_cost_by_mo, total_cost_operations, operations):
        query = SQL("""  SELECT
                        wo.production_id,
                        wo.id,
                        op.id,
                        wo.name,
                        wc.name,
                        wo.duration,
                        CASE WHEN wo.costs_hour = 0.0 THEN wc.costs_hour ELSE wo.costs_hour END AS costs_hour,
                        account_currency_table.rate
                    FROM mrp_workcenter_productivity t
                    LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
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
        for mo_id, dummy_wo_id, op_id, wo_name, wc_name, duration, cost_hour, currency_rate in self.env.cr.fetchall():
            cost = duration / 60.0 * cost_hour * currency_rate
            total_cost_by_mo[mo_id] += cost
            operation_cost_by_mo[mo_id] += cost
            total_cost_operations += cost
            operations.append([wc_name, op_id, wo_name, duration / 60.0, cost_hour * currency_rate])

        return total_cost_operations


class ProductTemplateCostStructure(models.AbstractModel):
    _name = 'report.mrp_account_enterprise.product_template_cost_structure'
    _description = 'Product Template Cost Structure Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        productions = self.env['mrp.production'].search([('product_id', 'in', docids), ('state', '=', 'done')])
        res = self.env['report.mrp_account_enterprise.mrp_cost_structure'].get_lines(productions)
        return {'lines': res}
