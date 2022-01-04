# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _compute_qty_delivered(self):
        """ Computes the quantity delivered when a kit is sold.
        To achieve this, this method fetch the quantities delivered of
        each component of the kit and the quantity needed of each components to produce 1 kit.
        Based on this, a ratio is computed for each component,
        and the lowest one is kept to define the kit's quantity delivered.
        """
        super(SaleOrderLine, self)._compute_qty_delivered()
        for order_line in self:
            if order_line.qty_delivered_method == 'stock_move':
                boms = order_line.move_ids.mapped('bom_line_id.bom_id')
                # We fetch the BoMs of type kits linked to the order_line,
                # the we keep only the one related to the finished produst.
                # This bom shoud be the only one since bom_line_id was written on the moves
                relevant_bom = boms.filtered(lambda b: b.type == 'phantom' and
                        (b.product_id == order_line.product_id or
                        (b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    qty_ratios = []
                    order_uom_qty = order_line.product_uom._compute_quantity(order_line.product_uom_qty, relevant_bom.product_uom_id)
                    boms, bom_sub_lines = relevant_bom.explode(order_line.product_id, order_uom_qty)
                    for bom_line, bom_line_data in bom_sub_lines:
                        bom_line_moves = moves.filtered(lambda m: m.bom_line_id == bom_line)
                        if bom_line_moves:
                            # We compute the quantities needed of each components to make one kit.
                            # Then, we collect every relevant moves related to a specific component
                            # to know how many are considered delivered.
                            uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                            qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id)
                            delivery_moves = bom_line_moves.filtered(lambda m: m.location_dest_id.usage == 'customer' and not m.origin_returned_move_id or not (m.origin_returned_move_id and m.to_refund))
                            return_moves = bom_line_moves.filtered(lambda m: m.location_dest_id.usage != 'customer' and m.to_refund)
                            qty_delivered = sum(delivery_moves.mapped('product_qty')) - sum(return_moves.mapped('product_qty'))
                            # We compute a ratio to know how many kits we can produce with this quantity of that specific component
                            qty_ratios.append(qty_delivered / qty_per_kit)
                        else:
                            qty_ratios.append(0.0)
                            break
                    if qty_ratios:
                        # Now that we have every ratio by components, we keep the lowest one to know how many kits we can produce
                        # with the quantities delivered of each component. We use the euclidean division here because a 'partial kit'
                        # doesn't make sense.
                        order_line.qty_delivered = min(qty_ratios) // 1
                    else:
                        order_line.qty_delivered = 0.0

    @api.multi
    def _get_bom_component_qty(self, bom):
        bom_quantity = self.product_uom._compute_quantity(1, bom.product_uom_id)
        boms, lines = bom.explode(self.product_id, bom_quantity)
        components = {}
        for line, line_data in lines:
            product = line.product_id.id
            uom = line.product_uom_id
            qty = line.product_qty
            if components.get(product, False):
                if uom.id != components[product]['uom']:
                    from_uom = uom
                    to_uom = self.env['uom.uom'].browse(components[product]['uom'])
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

    def _get_qty_procurement(self):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we compare the quantity before
        # and after update, and return the difference. We don't take into account what was already
        # sent, or any other exceptional case.
        bom = self.env['mrp.bom']._bom_find(product=self.product_id)
        if bom and bom.type == 'phantom' and 'previous_product_uom_qty' in self.env.context:
            return self.env.context['previous_product_uom_qty'].get(self.id, 0.0)
        return super(SaleOrderLine, self)._get_qty_procurement()

    @api.multi
    @api.depends('product_id', 'move_ids.state')
    def _compute_qty_delivered_method(self):
        lines = self.env['sale.order.line']
        for line in self:
            bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id)
            if bom and bom.type == 'phantom' and line.order_id.state == 'sale':
                bom_delivered = all(
                    [
                        move.state == "done"
                        for move in line.move_ids.filtered(lambda m: m.picking_id and m.picking_id.state != "cancel")
                    ]
                )
                if not bom_delivered:
                    line.qty_delivered_method = 'manual'
                    lines |= line
        super(SaleOrderLine, self - lines)._compute_qty_delivered_method()


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
                qty_done = sum([x.uom_id._compute_quantity(x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'in_payment', 'paid')])
                quantity = self.uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.move_ids.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                bom = self.env['mrp.bom'].sudo()._bom_find(product=s_line.product_id, company_id=s_line.company_id.id)
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
