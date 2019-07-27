# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_qty_delivered(self):
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
                    filters = {
                        'incoming_moves': lambda m: m.location_dest_id.usage == 'customer' and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_dest_id.usage != 'customer' and m.to_refund
                    }
                    order_qty = order_line.product_uom._compute_quantity(order_line.product_uom_qty, relevant_bom.product_uom_id)
                    order_line.qty_delivered = moves._compute_kit_quantities(order_line.product_id, order_qty, relevant_bom, filters)

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

    def _check_availability(self, product_id):
        """ If the 'product_id' is a kit, this method check if every component's
        availability and catch every warning returned in order to merge them in a single
        comprehensive warning
        """
        bom_kit = self.env['mrp.bom']._bom_find(product=product_id, bom_type='phantom')
        if not bom_kit:
            return super(SaleOrderLine, self)._check_availability(product_id)

        kit = product_id
        kit_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id)

        # We check if we need to display the quantities of each missing components for all warehouses
        kit_by_wh = self.product_id.with_context(warehouse=self.order_id.warehouse_id.id)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(kit_by_wh.virtual_available, kit_qty, precision_digits=precision) != -1:
            return {}
        ignore_warehouse = float_compare(kit.virtual_available, kit_qty, precision_digits=precision) != -1

        message = ''
        boms, bom_sub_lines = bom_kit.explode(kit, kit_qty)
        for bom_line, bom_line_data in bom_sub_lines:
            component = bom_line.product_id
            component_uom_qty = bom_line_data['qty']
            component_qty = bom_line.product_uom_id._compute_quantity(component_uom_qty, bom_line.product_id.uom_id)
            component_warning = self._check_availability_warning(component, component_qty, ignore_warehouse=ignore_warehouse)
            if component_warning:
                message += component_warning['warning']['message'] + '\n'

        warning = {}
        if message:
            warning_mess = {
                'title': _('Not enough inventory!'),
                'message': message
            }
            warning = {'warning': warning_mess}
        return warning

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        # Specific case when we change the qty on a SO for a kit product.
        # We don't try to be too smart and keep a simple approach: we compare the quantity before
        # and after update, and return the difference. We don't take into account what was already
        # sent, or any other exceptional case.
        bom = self.env['mrp.bom']._bom_find(product=self.product_id, bom_type='phantom')
        if bom and 'previous_product_uom_qty' in self.env.context:
            return previous_product_uom_qty and previous_product_uom_qty.get(self.id, 0.0)
        return super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
