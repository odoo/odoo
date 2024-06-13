# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'qty_delivered', 'product_id', 'state')
    def _compute_qty_to_deliver(self):
        """The inventory widget should now be visible in more cases if the product is consumable."""
        super(SaleOrderLine, self)._compute_qty_to_deliver()
        for line in self:
            # Hide the widget for kits since forecast doesn't support them.
            boms = self.env['mrp.bom']
            if line.state == 'sale':
                boms = line.move_ids.mapped('bom_line_id.bom_id')
            elif line.state in ['draft', 'sent'] and line.product_id:
                boms = boms._bom_find(line.product_id, company_id=line.company_id.id, bom_type='phantom')[line.product_id]
            relevant_bom = boms.filtered(lambda b: b.type == 'phantom' and
                    (b.product_id == line.product_id or
                    (b.product_tmpl_id == line.product_id.product_tmpl_id and not b.product_id)))
            if relevant_bom:
                line.display_qty_widget = False
                continue
            if line.state == 'draft' and line.product_type == 'consu':
                components = line.product_id.get_components()
                if components and components != [line.product_id.id]:
                    line.display_qty_widget = True

    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()
        for order_line in self:
            if order_line.qty_delivered_method == 'stock_move':
                boms = order_line.move_ids.filtered(lambda m: m.state != 'cancel').mapped('bom_line_id.bom_id')
                dropship = any(m._is_dropshipped() for m in order_line.move_ids)
                # We fetch the BoMs of type kits linked to the order_line,
                # the we keep only the one related to the finished produst.
                # This bom should be the only one since bom_line_id was written on the moves
                relevant_bom = boms.filtered(lambda b: b.type == 'phantom' and
                        (b.product_id == order_line.product_id or
                        (b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                if not relevant_bom:
                    relevant_bom = boms._bom_find(order_line.product_id, company_id=order_line.company_id.id, bom_type='phantom')[order_line.product_id]
                if relevant_bom:
                    # not written on a move coming from a PO: all moves (to customer) must be done
                    # and the returns must be delivered back to the customer
                    # FIXME: if the components of a kit have different suppliers, multiple PO
                    # are generated. If one PO is confirmed and all the others are in draft, receiving
                    # the products for this PO will set the qty_delivered. We might need to check the
                    # state of all PO as well... but sale_mrp doesn't depend on purchase.
                    if dropship:
                        moves = order_line.move_ids.filtered(lambda m: m.state != 'cancel')
                        if any((m.location_dest_id.usage == 'customer' and m.state != 'done')
                               or (m.location_dest_id.usage != 'customer'
                               and m.state == 'done'
                               and float_compare(m.quantity,
                                                 sum(sub_m.product_uom._compute_quantity(sub_m.quantity, m.product_uom) for sub_m in m.returned_move_ids if sub_m.state == 'done'),
                                                 precision_rounding=m.product_uom.rounding) > 0)
                               for m in moves) or not moves:
                            order_line.qty_delivered = 0
                        else:
                            order_line.qty_delivered = order_line.product_uom_qty
                        continue
                    moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    filters = {
                        'incoming_moves': lambda m: m.location_dest_id.usage == 'customer' and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_dest_id.usage != 'customer' and m.to_refund
                    }
                    order_qty = order_line.product_uom._compute_quantity(order_line.product_uom_qty, relevant_bom.product_uom_id)
                    qty_delivered = moves._compute_kit_quantities(order_line.product_id, order_qty, relevant_bom, filters)
                    order_line.qty_delivered += relevant_bom.product_uom_id._compute_quantity(qty_delivered, order_line.product_uom)

                # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
                # when the product sold is made only of kits. In this case, the BOM of the stock moves
                # do not correspond to the product sold => no relevant BOM.
                elif boms:
                    # if the move is ingoing, the product **sold** has delivered qty 0
                    if all(m.state == 'done' and m.location_dest_id.usage == 'customer' for m in order_line.move_ids):
                        order_line.qty_delivered = order_line.product_uom_qty
                    else:
                        order_line.qty_delivered = 0.0

    def compute_uom_qty(self, new_qty, stock_move, rounding=True):
        #check if stock move concerns a kit
        if stock_move.bom_line_id:
            return new_qty * stock_move.bom_line_id.product_qty
        return super(SaleOrderLine, self).compute_uom_qty(new_qty, stock_move, rounding)

    def _get_bom_component_qty(self, bom):
        bom_quantity = self.product_id.uom_id._compute_quantity(1, bom.product_uom_id, rounding_method='HALF-UP')
        boms, lines = bom.explode(self.product_id, bom_quantity)
        components = {}
        for line, line_data in lines:
            product = line.product_id.id
            uom = line.product_uom_id
            qty = line_data['qty']
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

    @api.model
    def _get_incoming_outgoing_moves_filter(self):
        """ Method to be override: will get incoming moves and outgoing moves.

        :return: Dictionary with incoming moves and outgoing moves
        :rtype: dict
        """
        # The first move created was the one created from the intial rule that started it all.
        sorted_moves = self.move_ids.sorted('id')
        triggering_rule_ids = []
        seen_wh_ids = set()
        for move in sorted_moves:
            if move.warehouse_id.id not in seen_wh_ids:
                triggering_rule_ids.append(move.rule_id.id)
                seen_wh_ids.add(move.warehouse_id.id)

        return {
            'incoming_moves': lambda m: (
                m.state != 'cancel' and not m.scrapped
                and m.rule_id.id in triggering_rule_ids
                and m.location_final_id.usage == 'customer'
                and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)
            )),
            'outgoing_moves': lambda m: (
                m.state != 'cancel' and not m.scrapped
                and m.location_dest_id.usage != 'customer' and m.to_refund
            ),
        }

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we use the quantity of entire
        # kits that are currently in delivery
        bom = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')[self.product_id]
        if bom:
            moves = self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped)
            filters = self._get_incoming_outgoing_moves_filter()
            order_qty = previous_product_uom_qty.get(self.id, 0) if previous_product_uom_qty else self.product_uom_qty
            order_qty = self.product_uom._compute_quantity(order_qty, bom.product_uom_id)
            qty = moves._compute_kit_quantities(self.product_id, order_qty, bom, filters)
            return bom.product_uom_id._compute_quantity(qty, self.product_uom)
        return super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
