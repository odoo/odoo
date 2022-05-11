# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_price_difference_svl_values(self):
        svl_vals_list = []
        cost_to_add_byproduct = defaultdict(lambda: {'qty': 0, 'cost': 0})
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        # Kits must be handle differently because there is a SVL by component, so we need to create
        # a SVL for the price diff by valued component, and we have to divide the value between them
        # proportionally to their initial cost.
        lines_for_kit_product = self.filtered(lambda aml: aml.product_id.is_kits)
        for line in lines_for_kit_product:
            if line.move_id._skip_move_for_price_diff() or line._is_not_eligible_for_price_difference():
                continue
            move = line.move_id.with_company(line.move_id.company_id)

            # Retrieve stock valuation moves.
            valuation_stock_moves = move._retrieve_stock_valuation_moves(line)

            if line.product_id.cost_method != 'standard' and line.purchase_line_id:
                po_currency = line.purchase_line_id.currency_id
                po_company = line.purchase_line_id.company_id

                if valuation_stock_moves:
                    valuation_price_unit_total, valuation_total_qty = valuation_stock_moves._get_valuation_price_and_qty(line, move.currency_id)
                    valuation_price_unit = valuation_price_unit_total / valuation_total_qty
                    valuation_price_unit = line.product_id.uom_id._compute_price(valuation_price_unit, line.product_uom_id)
                elif line.product_id.cost_method == 'fifo':
                    # In this condition, we have a real price-valuated product which has not yet been received
                    valuation_price_unit = po_currency._convert(
                        line.purchase_line_id.price_unit, move.currency_id,
                        po_company, move.date, round=False,
                    )
                else:
                    # For average/fifo/lifo costing method, fetch real cost price from incoming moves.
                    price_unit = line.purchase_line_id.product_uom._compute_price(line.purchase_line_id.price_unit, line.product_uom_id)
                    valuation_price_unit = po_currency._convert(
                        price_unit, move.currency_id,
                        po_company, move.date, round=False
                    )

            else:
                # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
                price_unit = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id)
                valuation_price_unit = line.company_currency_id._convert(
                    price_unit, move.currency_id,
                    move.company_id, fields.Date.today(), round=False
                )

            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.tax_ids:
                if line.discount and line.quantity:
                    # We do not want to round the price unit since :
                    # - It does not follow the currency precision
                    # - It may include a discount
                    # Since compute_all still rounds the total, we use an ugly workaround:
                    # multiply then divide the price unit.
                    price_unit *= line.quantity
                    price_unit = line.tax_ids.with_context(round=False, force_sign=move._get_tax_force_sign()).compute_all(
                        price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']
                    price_unit /= line.quantity
                else:
                    price_unit = line.tax_ids.compute_all(
                        price_unit, currency=move.currency_id, quantity=1.0, is_refund=move.move_type == 'in_refund')['total_excluded']
            price_unit_val_dif = price_unit - valuation_price_unit
            price_subtotal = line.quantity * price_unit_val_dif
            linked_layers = valuation_stock_moves.stock_valuation_layer_ids

            # We consider there is a price difference if the subtotal is not zero. In case a
            # discount has been applied, we can't round the price unit anymore, and hence we
            # can't compare them.
            if not move.currency_id.is_zero(price_subtotal) and linked_layers and\
               float_compare(line["price_unit"], line.price_unit, precision_digits=price_unit_prec) == 0:
                qty_invoiced = line.purchase_line_id.qty_invoiced
                qty_received = line.purchase_line_id.qty_received
                qty_to_diff = min(line.quantity, qty_received - (qty_invoiced - line.quantity))
                if qty_to_diff <= 0:
                    continue
                product = line.product_id
                svl_description = _(
                    'Price difference between %(purchase_name)s and %(invoice_name)s',
                    purchase_name=line.purchase_line_id.order_id.name,
                    invoice_name=move._get_next_sequence())
                kit_unit_cost = sum(linked_layers.mapped('unit_cost'))
                price_unit_val_dif = line.price_unit - kit_unit_cost
                if price_unit_val_dif == 0:
                    continue
                for linked_layer in linked_layers:
                    ratio = linked_layer.unit_cost / kit_unit_cost
                    price_subtotal = move.company_id.currency_id.round(qty_to_diff * price_unit_val_dif * ratio)
                    # Creates a new stock valuation layer for the price difference.
                    svl_vals_list.append({
                        'company_id': line.company_id.id,
                        'product_id': linked_layer.product_id.id,
                        'description': svl_description,
                        'value': price_subtotal,
                        'quantity': 0,
                        'account_move_id': move.id,
                        'stock_valuation_layer_id': linked_layer.id
                    })
                    linked_layer.remaining_value += price_subtotal
                    # If linked_layer.product_id cost method is AVCO, updates the standard price.
                    if linked_layer.product_id.cost_method == 'average' and\
                       not float_is_zero(linked_layer.product_id.quantity_svl, precision_rounding=linked_layer.product_id.uom_id.rounding):
                        cost_to_add_byproduct[linked_layer.product_id]['qty'] += qty_to_diff
                        cost_to_add_byproduct[linked_layer.product_id]['cost'] += price_unit_val_dif
        # Batch standard price computation avoids recompute `quantity_svl` at each iteration.
        products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys())
        for product in products:  # Iterates on recordset to prefetch efficiently `quantity_svl`.
            unit_cost = cost_to_add_byproduct[product]['cost']
            invoiced_qty = cost_to_add_byproduct[product]['qty']
            cost_to_add = (unit_cost * invoiced_qty) / product.quantity_svl
            product.with_company(move.company_id).sudo().with_context(disable_auto_svl=True).standard_price += cost_to_add
        svl_vals_list += super(AccountMoveLine, self - lines_for_kit_product)._get_price_difference_svl_values()
        return svl_vals_list
