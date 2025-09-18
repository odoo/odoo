# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_relevant_phantom_bom(self, retry=False):
        self.ensure_one()
        boms = self.env['mrp.bom']
        if self.state == 'draft':
            boms = boms._bom_find(
                self.product_id,
                company_id=self.company_id.id,
                bom_type='phantom',
            )[self.product_id]
        elif self.state == 'done':
            move_ids = self.move_ids.filtered(lambda m: m.state != 'cancel')
            boms = move_ids.bom_line_id.bom_id if move_ids.bom_line_id else boms

        # Filter to get only phantom BOMs matching this exact product
        relevant_bom = boms.filtered(
            lambda b: b.type == 'phantom'
            and (
                b.product_id == self.product_id
                or (
                    b.product_tmpl_id == self.product_id.product_tmpl_id
                    and not b.product_id
                )
            ),
        )

        # Fallback to _bom_find if requested and no relevant BOM found
        if not relevant_bom and retry:
            relevant_bom = self.env['mrp.bom']._bom_find(
                self.product_id,
                company_id=self.company_id.id,
                bom_type='phantom',
            )[self.product_id]

        return boms, relevant_bom

    def _compute_display_qty_widget(self):
        """The inventory widget should now be visible in more cases"""
        super()._compute_display_qty_widget()
        for line in self.filtered(lambda x: x.product_id and x.product_id.is_storable):
            # Hide the widget for kits since forecast doesn't support them.
            _boms, relevant_bom = line._get_relevant_phantom_bom()

            if relevant_bom:
                line.display_qty_widget = False
                continue

            if line.state == 'draft' and line.product_type == 'consu':
                components = line.product_id.get_components()
                if components and components != [line.product_id.id]:
                    line.display_qty_widget = True

    def _compute_qty_transferred(self):
        lines_by_stock_move = self.filtered(
            lambda line: line.qty_transferred_method == "stock_move",
        )
        super(SaleOrderLine, self - lines_by_stock_move)._compute_qty_transferred()

        for line in lines_by_stock_move:

            if not line.move_ids:
                super(SaleOrderLine, line)._compute_qty_transferred()
                continue

            dropship = any(m._is_dropshipped() for m in line.move_ids)
            # We fetch the BoMs of type kits linked to the line,
            # then we keep only the one related to the finished produst.
            # This bom should be the only one since bom_line_id was written on the moves
            boms, relevant_bom = line._get_relevant_phantom_bom(retry=True)

            if not boms and not relevant_bom:
                super(SaleOrderLine, line)._compute_qty_transferred()
                continue

            if relevant_bom:
                # not written on a move coming from a PO: all moves (to customer) must be done
                # and the returns must be delivered back to the customer
                # FIXME: if the components of a kit have different suppliers, multiple PO
                # are generated. If one PO is confirmed and all the others are in draft, receiving
                # the products for this PO will set the qty_transferred. We might need to check the
                # state of all PO as well... but sale_mrp doesn't depend on purchase.
                if dropship:
                    moves = line.move_ids.filtered(lambda m: m.state != 'cancel')

                    if any((m.location_dest_id.usage == 'customer' and m.state != 'done')
                            or (m.location_dest_id.usage != 'customer'
                            and m.state == 'done'
                            and float_compare(m.quantity,
                                                sum(sub_m.product_uom._compute_quantity(sub_m.quantity, m.product_uom) for sub_m in m.returned_move_ids if sub_m.state == 'done'),
                                                precision_rounding=m.product_uom.rounding) > 0)
                            for m in moves) or not moves:
                        line.qty_transferred = 0
                    else:
                        line.qty_transferred = line.product_uom_qty

                    continue

                moves = line.move_ids.filtered(lambda m: m.state == 'done' and m.location_dest_usage != 'inventory')
                filters = {
                    # in/out perspective w/ respect to moves is flipped for sale order document
                    'incoming_moves': lambda m:
                        m._is_outgoing() and
                        (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                    'outgoing_moves': lambda m:
                        m._is_incoming() and m.to_refund,
                }
                order_qty = line.product_uom_id._compute_quantity(line.product_uom_qty, relevant_bom.product_uom_id)
                qty_transferred = moves._compute_kit_quantities(line.product_id, order_qty, relevant_bom, filters)
                line.qty_transferred += relevant_bom.product_uom_id._compute_quantity(qty_transferred, line.product_uom_id)

            # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
            # when the product sold is made only of kits. In this case, the BOM of the stock moves
            # do not correspond to the product sold => no relevant BOM.
            elif boms:
                # if the move is ingoing, the product **sold** has delivered qty 0
                if all(m.state == 'done' and m.location_dest_id.usage == 'customer' for m in line.move_ids):
                    line.qty_transferred = line.product_uom_qty
                else:
                    line.qty_transferred = 0.0

    def _prepare_qty_transferred(self):
        delivered_qties = super()._prepare_qty_transferred()
        for order_line in self:
            if order_line.qty_delivered_method == 'stock_move':
                boms = order_line.move_ids.filtered(lambda m: m.state != 'cancel').bom_line_id.bom_id
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
                            delivered_qties[order_line] = 0
                        else:
                            delivered_qties[order_line] = order_line.product_uom_qty
                        continue
                    moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and m.location_dest_usage != 'inventory')
                    filters = {
                        # in/out perspective w/ respect to moves is flipped for sale order document
                        'incoming_moves': lambda m:
                            m._is_outgoing() and
                            (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m:
                            m._is_incoming() and m.to_refund,
                    }
                    order_qty = order_line.product_uom_id._compute_quantity(order_line.product_uom_qty, relevant_bom.product_uom_id)
                    qty_delivered = moves._compute_kit_quantities(order_line.product_id, order_qty, relevant_bom, filters)
                    delivered_qties[order_line] += relevant_bom.product_uom_id._compute_quantity(qty_delivered, order_line.product_uom_id)

                # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
                # when the product sold is made only of kits. In this case, the BOM of the stock moves
                # do not correspond to the product sold => no relevant BOM.
                elif boms:
                    # if the move is ingoing, the product **sold** has delivered qty 0
                    if all(m.state == 'done' and m.location_dest_id.usage == 'customer' for m in order_line.move_ids):
                        delivered_qties[order_line] = order_line.product_uom_qty
                    else:
                        delivered_qties[order_line] = 0.0
        return delivered_qties

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
        seen_bom_id = set()
        for move in sorted_moves:
            if move.bom_line_id.bom_id.id in seen_bom_id:
                triggering_rule_ids.append(move.rule_id.id)
            elif move.warehouse_id.id not in seen_wh_ids:
                triggering_rule_ids.append(move.rule_id.id)
                seen_wh_ids.add(move.warehouse_id.id)
                if move.bom_line_id and move.bom_line_id.bom_id.type == 'phantom':
                    seen_bom_id.add(move.bom_line_id.bom_id.id)

        return {
            'incoming_moves': lambda m: (
                m.state != 'cancel' and m.location_dest_usage != 'inventory'
                and m.rule_id.id in triggering_rule_ids
                and m.location_final_id.usage == 'customer'
                and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)
            )),
            'outgoing_moves': lambda m: (
                m.state != 'cancel' and m.location_dest_usage != 'inventory'
                and m.location_id.usage == 'customer' and m.to_refund
            ),
        }

    def _get_procurement_qty(self, previous_product_uom_qty=False):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we use the quantity of entire
        # kits that are currently in delivery
        bom = self.env['mrp.bom'].sudo()._bom_find(self.product_id, bom_type='phantom', company_id=self.company_id.id)[self.product_id]
        if bom and self.move_ids:
            moves = self.move_ids.filtered(lambda r: r.state != 'cancel' and r.location_dest_usage != 'inventory')
            filters = self._get_incoming_outgoing_moves_filter()
            order_qty = previous_product_uom_qty.get(self.id, 0) if previous_product_uom_qty else self.product_uom_qty
            order_qty = self.product_uom_id._compute_quantity(order_qty, bom.product_uom_id)
            qty = moves._compute_kit_quantities(self.product_id, order_qty, bom, filters)
            return bom.product_uom_id._compute_quantity(qty, self.product_uom_id)
        elif bom and previous_product_uom_qty:
            return previous_product_uom_qty.get(self.id)
        return super()._get_procurement_qty(previous_product_uom_qty=previous_product_uom_qty)
