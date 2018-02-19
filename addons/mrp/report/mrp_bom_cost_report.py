# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_round


class MrpBomCost(models.AbstractModel):
    _name = 'report.mrp.mrp_bom_cost_report'

    def get_bom_cost(self, current_line, quantity):
        total = 0
        for child_line in current_line.child_line_ids:
            if child_line._skip_bom_line(current_line.product_id):
                continue
            line_quantity = (quantity / child_line.bom_id.product_qty) * child_line.product_qty
            if child_line.child_bom_id:
                line_quantity = child_line.product_uom_id._compute_quantity(line_quantity, child_line.child_bom_id.product_uom_id)
            total += self.get_bom_cost(child_line, line_quantity)
        if not current_line.child_bom_id:
            unit_price = current_line.product_id.uom_id._compute_price(current_line.product_id.standard_price, current_line.product_uom_id)
            total = unit_price * quantity
        return total

    def _get_operation_line(self, routing, bom, parent, qty):
        operations = []
        total = 0.0
        for operation in routing.operation_ids:
            rounding = bom.product_uom_id.rounding
            cycle_number = float_round((1.0 / operation.workcenter_id.capacity), precision_rounding=rounding)
            duration_expected = cycle_number * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency
            if parent:
                duration_expected = duration_expected * qty
            duration_expected += operation.workcenter_id.time_stop + operation.workcenter_id.time_start
            total = ((duration_expected / 60.0) * operation.workcenter_id.costs_hour)
            operations.append({
                'name': operation.name + ' - ' + bom.product_tmpl_id.name,
                'duration_expected': duration_expected,
                'workcenter': operation.workcenter_id.name,
                'costs_hour': operation.workcenter_id.costs_hour,
                'total': float_round(total, precision_rounding=rounding),
                })
        return operations

    def get_bom_lines(self, bom_lines, product, qty, parent_line, level, bom_ids):
        lines, operations = [], []
        boms = bom_lines.mapped('bom_id')
        total = 0.0
        next_level = level + 1
        for bom_line in bom_lines:
            if bom_line._skip_bom_line(product):
                continue
            line_quantity = bom_line.product_qty
            if parent_line:
                qty = parent_line.product_uom_id._compute_quantity(qty, bom_line.bom_id.product_uom_id, round=False) / bom_line.bom_id.product_qty
                line_quantity = bom_line.product_qty * qty
            if bom_line.bom_id.routing_id and bom_line.bom_id.id not in bom_ids:
                bom_ids.append(bom_line.bom_id.id)
                operations = self._get_operation_line(bom_line.bom_id.routing_id, bom_line.bom_id, parent_line, qty)
            has_child = bom_line.child_line_ids and True or False
            unit_price = 0.0
            total_price = 0.0
            if has_child:
                qty = bom_line.product_uom_id._compute_quantity(line_quantity, bom_line.child_bom_id.product_uom_id, round=False)
                unit_price = self.get_bom_cost(bom_line, qty) / line_quantity
            else:
                unit_price = bom_line.product_id.uom_id._compute_price(bom_line.product_id.standard_price, bom_line.product_uom_id)
            total_price = line_quantity * unit_price
            lines.append(({
                'product_id': bom_line.product_id,
                'product_uom': bom_line.product_uom_id,
                'level': level,
                'price_unit': unit_price,
                'product_uom_qty': line_quantity,
                'total_price': total_price,
                'has_child': has_child,
                'id': bom_line.id,
                'parent_id': parent_line and parent_line.id,
            }))
            if not parent_line:
                total += total_price
            for child_line in bom_line.child_line_ids:
                _, _lines, _boms, _operations = self.get_bom_lines(child_line, bom_line.product_id, line_quantity, bom_line, next_level, bom_ids)
                lines += _lines
                boms += _boms
                operations += _operations
        return total, lines, boms, operations

    @api.multi
    def get_lines(self, boms):
        product_lines = {}
        for bom in boms:
            products = bom.product_id
            if not products:
                products = bom.product_tmpl_id.product_variant_ids
            for product in products:
                total, lines, boms, operations = self.get_bom_lines(bom.bom_line_ids, product, bom.product_qty, False, 0, [])
                operations_total = sum([op['total'] for op in operations])
                if lines:
                    product_line = {
                        'bom': bom,
                        'name': product.display_name,
                        'lines': lines,
                        'operations': operations,
                        'operations_total': operations_total,
                        'total': total,
                        'currency': self.env.user.company_id.currency_id,
                        'reference': bom.code,
                        'product_uom_qty': bom.product_qty,
                        'product_uom': bom.product_uom_id,
                        'id': product.id
                    }
                    product_lines[product] = product_line
        return product_lines

    @api.model
    def get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        bom_products = self.get_lines(boms)
        print_mode = self.env.context.get('print_mode')
        return {'bom_products': bom_products, 'print_mode': print_mode}
