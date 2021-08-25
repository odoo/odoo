# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models



class StockMove(models.Model):
    _inherit = 'stock.move'

    weight = fields.Float(compute='_cal_move_weight', digits='Stock Weight', store=True, compute_sudo=True)

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_weight(self):
        moves_with_weight = self.filtered(lambda moves: moves.product_id.weight > 0.00)
        for move in moves_with_weight:
            move.weight = (move.product_qty * move.product_id.weight)
        (self - moves_with_weight).weight = 0

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['carrier_id'] = self.mapped('sale_line_id.order_id.carrier_id').id
        return vals

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.sale_line_id.order_id.carrier_id,)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sale_price = fields.Float(compute='_compute_sale_price')

    @api.depends('qty_done', 'product_uom_id', 'product_id', 'move_id.sale_line_id', 'move_id.sale_line_id.price_reduce_taxinc', 'move_id.sale_line_id.product_uom')
    def _compute_sale_price(self):
        for move_line in self:
            if move_line.move_id.sale_line_id:
                unit_price = move_line.move_id.sale_line_id.price_reduce_taxinc
                qty = move_line.product_uom_id._compute_quantity(move_line.move_id.sale_line_id.product_qty, move_line.move_id.sale_line_id.product_uom)
            else:
                unit_price = move_line.product_id.list_price
                qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)
            move_line.sale_price = unit_price * qty
        super(StockMoveLine, self)._compute_sale_price()

    def _get_aggregated_product_quantities(self, **kwargs):
        """Returns dictionary of products and corresponding values of interest + hs_code

        Unfortunately because we are working with aggregated data, we have to loop through the
        aggregation to add more values to each datum. This extension adds on the hs_code value.

        returns: dictionary {same_key_as_super: {same_values_as_super, hs_code}, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for aggregated_move_line in aggregated_move_lines:
            hs_code = aggregated_move_lines[aggregated_move_line]['product'].product_tmpl_id.hs_code
            aggregated_move_lines[aggregated_move_line]['hs_code'] = hs_code
        return aggregated_move_lines
