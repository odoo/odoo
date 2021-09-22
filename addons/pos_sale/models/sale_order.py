# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_origin_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")
    pos_order_count = fields.Integer(string='Pos Order Count', compute='_count_pos_order', readonly=True, groups="point_of_sale.group_pos_user")

    def _count_pos_order(self):
        for order in self:
            linked_orders = order.pos_order_line_ids.mapped('order_id')
            order.pos_order_count = len(linked_orders)

    def action_view_pos_order(self):
        self.ensure_one()
        linked_orders = self.pos_order_line_ids.mapped('order_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked POS Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', linked_orders.ids)],
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pos_order_line_ids = fields.One2many('pos.order.line', 'sale_order_line_id', string="Order lines Transfered to Point of Sale", readonly=True, groups="point_of_sale.group_pos_user")

    @api.depends('pos_order_line_ids.qty')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()
        for sale_line in self:
            sale_line.qty_delivered += sum([self._convert_qty(sale_line, pos_line.qty, 'p2s') for pos_line in sale_line.pos_order_line_ids if sale_line.product_id.type != 'service'], 0)

    @api.depends('pos_order_line_ids.qty')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for sale_line in self:
            sale_line.qty_invoiced += sum([self._convert_qty(sale_line, pos_line.qty, 'p2s') for pos_line in sale_line.pos_order_line_ids], 0)

    def read_converted(self):
        field_names = ["product_id", "price_unit", "product_uom_qty", "tax_id", "qty_delivered", "qty_invoiced", "discount", "qty_to_invoice", "price_total"]
        results = []
        for sale_line in self:
            if sale_line.product_type:
                product_uom = sale_line.product_id.uom_id
                sale_line_uom = sale_line.product_uom
                item = sale_line.read(field_names)[0]
                if sale_line.product_id.tracking != 'none':
                    item['lot_names'] = sale_line.move_ids.move_line_ids.lot_id.mapped('name')
                if product_uom == sale_line_uom:
                    results.append(item)
                    continue
                item['product_uom_qty'] = self._convert_qty(sale_line, item['product_uom_qty'], 's2p')
                item['qty_delivered'] = self._convert_qty(sale_line, item['qty_delivered'], 's2p')
                item['qty_invoiced'] = self._convert_qty(sale_line, item['qty_invoiced'], 's2p')
                item['qty_to_invoice'] = self._convert_qty(sale_line, item['qty_to_invoice'], 's2p')
                item['price_unit'] = sale_line_uom._compute_price(item['price_unit'], product_uom)
                results.append(item)

            elif sale_line.display_type == 'line_note':
                if results:
                    results[-1]['customer_note'] = sale_line.name

        return results

    @api.model
    def _convert_qty(self, sale_line, qty, direction):
        """Converts the given QTY based on the given SALE_LINE and DIR.

        if DIR='s2p': convert from sale line uom to product uom
        if DIR='p2s': convert from product uom to sale line uom
        """
        product_uom = sale_line.product_id.uom_id
        sale_line_uom = sale_line.product_uom
        if direction == 's2p':
            return sale_line_uom._compute_quantity(qty, product_uom, False)
        elif direction == 'p2s':
            return product_uom._compute_quantity(qty, sale_line_uom, False)
