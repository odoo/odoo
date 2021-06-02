# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'qty_delivered', 'product_id', 'state')
    def _compute_qty_to_deliver(self):
        """The inventory widget should now be visible in more cases if the product is consumable."""
        super(SaleOrderLine, self)._compute_qty_to_deliver()
        for line in self:
            if line.state == 'draft' and line.product_type == 'consu':
                components = line.product_id.get_components()
                if components and components != [line.product_id.id]:
                    line.display_qty_widget = True

    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()
        for order_line in self:
            if order_line.qty_delivered_method == 'stock_move':
                boms = order_line.move_ids.mapped('bom_line_id.bom_id')
                dropship = False
                if not boms and any([m._is_dropshipped() for m in order_line.move_ids]):
                    boms = boms._bom_find(product=order_line.product_id, company_id=order_line.company_id.id, bom_type='phantom')
                    dropship = True
                # We fetch the BoMs of type kits linked to the order_line,
                # the we keep only the one related to the finished produst.
                # This bom shoud be the only one since bom_line_id was written on the moves
                relevant_bom = boms.filtered(lambda b: b.type == 'phantom' and
                        (b.product_id == order_line.product_id or
                        (b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    # In case of dropship, we use a 'all or nothing' policy since 'bom_line_id' was
                    # not written on a move coming from a PO.
                    # FIXME: if the components of a kit have different suppliers, multiple PO
                    # are generated. If one PO is confirmed and all the others are in draft, receiving
                    # the products for this PO will set the qty_delivered. We might need to check the
                    # state of all PO as well... but sale_mrp doesn't depend on purchase.
                    if dropship:
                        if order_line.move_ids and all([m.state == 'done' for m in order_line.move_ids]):
                            order_line.qty_delivered = order_line.product_uom_qty
                        else:
                            order_line.qty_delivered = 0.0
                        continue
                    moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    filters = {
                        'incoming_moves': lambda m: m.location_dest_id.usage == 'customer' and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_dest_id.usage != 'customer' and m.to_refund
                    }
                    order_qty = order_line.product_uom._compute_quantity(order_line.product_uom_qty, relevant_bom.product_uom_id)
                    order_line.qty_delivered = moves._compute_kit_quantities(order_line.product_id, order_qty, relevant_bom, filters)

                # If no relevant BOM is found, fall back on the all-or-nothing policy. This happens
                # when the product sold is made only of kits. In this case, the BOM of the stock moves
                # do not correspond to the product sold => no relevant BOM.
                elif boms:
                    if all([m.state == 'done' for m in order_line.move_ids]):
                        order_line.qty_delivered = order_line.product_uom_qty
                    else:
                        order_line.qty_delivered = 0.0

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

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we compare the quantity before
        # and after update, and return the difference. We don't take into account what was already
        # sent, or any other exceptional case.
        bom = self.env['mrp.bom']._bom_find(product=self.product_id, bom_type='phantom')
        if bom and previous_product_uom_qty:
            return previous_product_uom_qty and previous_product_uom_qty.get(self.id, 0.0)
        return super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
