# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_possible_qty(self, bom, products_qty):
        components = self._get_bom_component_qty(bom)
        possible_qty = []
        for product_id, line in components.items():
            qty = line.get('qty', 0.0)
            if qty > 0:
                qty = products_qty[product_id] / qty
            possible_qty.append(qty)
        return possible_qty and min(possible_qty) or 0.0

    def _get_bom_products_moves(self, moves):
        products = moves.mapped('product_id')
        line_product = self.product_id
        products_qty = {}
        for product in products:
            products_qty[product.id] = 0.0
            product_moves = moves.filtered(lambda r: r.product_id == product)
            returned_moves = product_moves.mapped('returned_move_ids').filtered(lambda r: r.to_refund)
            delivered_moves = product_moves - returned_moves
            for move in delivered_moves:
                products_qty[product.id] += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
            for move in returned_moves:
                products_qty[product.id] -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')

        bom = line_product.bom_ids._bom_find(
            product=line_product,
            company_id=self.env.user.company_id.id
        )
        return self._get_possible_qty(bom, products_qty)

    @api.multi
    def _get_delivered_qty(self):
        self.ensure_one()

        # In the case of a kit, we need to check if all components are shipped. Since the BOM might
        # have changed, we don't compute the quantities but verify the move state.
        bom = self.env['mrp.bom']._bom_find(product=self.product_id)
        if bom and bom.type == 'phantom':
            moves = self.move_ids.filtered(lambda r: r.state == 'done')
            return self.sudo()._get_bom_products_moves(moves)
        return super(SaleOrderLine, self)._get_delivered_qty()

    def _get_qty_procurement(self):
        self.ensure_one()
        moves = self.move_ids.filtered(lambda r: r.state != 'cancel')
        products = moves.mapped('product_id')
        if products and self.product_id not in products:
            return self.sudo()._get_bom_products_moves(moves)
        else:
            return super(SaleOrderLine, self)._get_qty_procurement()

    @api.multi
    def _get_bom_component_qty(self, bom):
        bom_quantity = self.product_uom._compute_quantity(self.product_uom_qty, bom.product_uom_id)
        boms, lines = bom.explode(self.product_id, bom_quantity)
        components = {}
        for line, line_data in lines:
            product = line.product_id.id
            uom = line.product_uom_id
            qty = line.product_qty
            if components.get(product, False):
                if uom.id != components[product]['uom']:
                    from_uom = uom
                    to_uom = self.env['product.uom'].browse(components[product]['uom'])
                    qty = from_uom._compute_quantity(qty, to_uom)
                components[product]['qty'] += qty
            else:
                # To be in the uom reference of the product
                to_uom = self.env['product.product'].browse(product).uom_id
                if uom.id != to_uom.id:
                    from_uom = uom
                    qty = from_uom._compute_quantity(qty, to_uom)
                components[product] = {'qty': qty, 'uom': to_uom.id}
        return components


class AccountInvoiceLine(models.Model):
    # TDE FIXME: what is this code ??
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine, self)._get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([x.uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.move_ids.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                bom = s_line.product_id.product_tmpl_id.bom_ids and s_line.product_id.product_tmpl_id.bom_ids[0]
                if bom.type == 'phantom':
                    average_price_unit = 0
                    components = s_line._get_bom_component_qty(bom)
                    for product_id in components:
                        factor = components[product_id]['qty']
                        prod_moves = [m for m in moves if m.product_id.id == product_id]
                        prod_qty_done = factor * qty_done
                        prod_quantity = factor * quantity
                        average_price_unit += factor * self._compute_average_price(prod_qty_done, prod_quantity, prod_moves)
                    price_unit = average_price_unit or price_unit
                    price_unit = self.product_id.uom_id._compute_price(price_unit, self.uom_id)
        return price_unit
