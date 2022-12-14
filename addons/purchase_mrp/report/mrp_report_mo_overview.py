# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_compare

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_extra_replenishments(self, product):
        res = super()._get_extra_replenishments(product)
        domain = [('state', 'in', ['draft', 'sent', 'to approve']), ('product_id', '=', product.id)]
        warehouse_id = self.env.context.get('warehouse', False)
        if warehouse_id:
            domain += [('order_id.picking_type_id.warehouse_id', '=', warehouse_id)]
        po_lines = self.env['purchase.order.line'].search(domain, order='date_planned, id')

        for po_line in po_lines:
            line_qty = po_line.product_uom_qty
            if po_line.move_dest_ids.raw_material_production_id:
                for move in po_line.move_dest_ids:
                    if float_compare(line_qty, move.product_uom_qty, precision_rounding=po_line.product_uom.rounding) >= 0:
                        prod_qty = move.product_uom_qty
                    else:
                        prod_qty = line_qty
                    res.append(self._format_extra_replenishment(po_line, prod_qty, move.raw_material_production_id.id))
                    line_qty -= prod_qty
            else:
                res.append(self._format_extra_replenishment(po_line, po_line.product_uom_qty))

        return res

    def _format_extra_replenishment(self, po_line, quantity, production_id=False):
        return {
            '_name': 'purchase.order',
            'id': po_line.order_id.id,
            'cost': po_line.price_total,
            'quantity': quantity,
            'production_id': production_id
        }

    def _get_replenishment_receipt(self, doc_in, components):
        res = super()._get_replenishment_receipt(doc_in, components)
        if doc_in._name == 'purchase.order':
            receipt_state = 'expected' if doc_in.state == 'purchase' else 'estimated'
            return self._format_receipt_date(receipt_state, doc_in.date_planned)
        return res

    def _get_resupply_data(self, rules, rules_delay, quantity, product, warehouse):
        res = super()._get_resupply_data(rules, rules_delay, quantity, product, warehouse)
        if any(rule for rule in rules if rule.action == 'buy' and product.seller_ids):
            supplier = product._select_seller(quantity=quantity, uom_id=product.uom_id)
            return {
                'delay': supplier.delay + rules_delay,
                'cost': supplier.price * quantity,
            }
        return res

    def _get_replenishment_cost(self, product, quantity, currency, move_in=False):
        if move_in and move_in.purchase_line_id:
            return currency.round(move_in.purchase_line_id.price_unit * quantity)
        return super()._get_replenishment_cost(product, quantity, currency, move_in)
