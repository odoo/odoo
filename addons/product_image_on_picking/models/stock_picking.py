# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from itertools import groupby

class StockMove(models.Model):
	_inherit = "stock.move"

	def _get_serial_numbers(self):
		line_num = 1
		for line_rec in self.picking_id.move_ids_without_package:
			line_rec.sr_number = line_num
			line_num += 1

	image_128 = fields.Binary(string="Image")
	sr_number = fields.Char(string="Sr. No", default=False, compute="_get_serial_numbers" )


	@api.onchange('product_id')
	def onchange_product_image(self):
		for product in self:
			product.image_128 = product.product_id.image_128

	def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
		self.ensure_one()
		# apply putaway
		location_dest_id = self.location_dest_id._get_putaway_strategy(self.product_id).id or self.location_dest_id.id
		vals = {
			'move_id': self.id,
			'product_id': self.product_id.id,
			'product_uom_id': self.product_uom.id,
			'location_id': self.location_id.id,
			'location_dest_id': location_dest_id,
			'picking_id': self.picking_id.id,
		}
		if quantity:
			uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
			uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
			rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
			if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
				vals = dict(vals, reserved_uom_qty=uom_quantity)
			else:
				vals = dict(vals, reserved_uom_qty=quantity, product_uom_id=self.product_id.uom_id.id)
		if reserved_quant:
			vals = dict(
				vals,
				location_id=reserved_quant.location_id.id,
				lot_id=reserved_quant.lot_id.id or False,
				package_id=reserved_quant.package_id.id or False,
				owner_id =reserved_quant.owner_id.id or False,
			)
		for move in self:
			self.write({
						'image_128' : move.product_id.image_128,
					})
		return vals

	def _assign_picking(self):
		Picking = self.env['stock.picking']
		grouped_moves = groupby(sorted(self, key=lambda m: [f.id for f in m._key_assign_picking()]), key=lambda m: [m._key_assign_picking()])
		for group, moves in grouped_moves:
			moves = self.env['stock.move'].concat(*list(moves))
			new_picking = False
			picking = moves[0]._search_picking_for_assignation()
			if picking:
				if any(picking.partner_id.id != m.partner_id.id or
						picking.origin != m.origin for m in moves):
					picking.write({
						'partner_id': False,
						'origin': False,
					})
			else:
				new_picking = True
				picking = Picking.create(moves._get_new_picking_values())
			for product in self:
				product.image_128 = product.product_id.image_128
				
			for move in picking.move_ids:
				move.image_128 =  move.product_id.image_128
		
			moves.write({'picking_id': picking.id})
			moves._assign_picking_post_process(new=new_picking)
		return True
	

class StockMoveline_Inherit(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            description = move.description_picking
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
            return (line_key, name, description, uom)

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key, name, description, uom = get_aggregated_properties(move_line=move_line)

            qty_done = move_line.product_uom_id._compute_quantity(move_line.qty_done, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum(map(lambda m: m.product_uom_id._compute_quantity(m.qty_done, uom), previous_move_lines))
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'qty_done': qty_done,
                                                   'qty_ordered': qty_ordered or qty_done,
                                                   'product_uom': uom,
                                                   'product': move_line.product_id,
                                                   'sr_number': move_line.move_id.sr_number,
                                                   'image_128': move_line.move_id.image_128,
                                                   }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += qty_done
                aggregated_move_lines[line_key]['qty_done'] += qty_done

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return aggregated_move_lines
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            if not (empty_move.state == "cancel" and empty_move.product_uom_qty
                    and float_is_zero(empty_move.quantity_done, precision_rounding=empty_move.product_uom.rounding)):
                continue
            line_key, name, description, uom = get_aggregated_properties(move=empty_move)

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'qty_done': False,
                    'qty_ordered': qty_ordered,
                    'product_uom': uom,
                    'product': empty_move.product_id,
                    'sr_number': empty_move.sr_number,
                    'image_128': empty_move.image_128,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty

        return aggregated_move_lines
