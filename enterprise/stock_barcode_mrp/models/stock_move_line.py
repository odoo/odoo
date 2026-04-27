# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    manual_consumption = fields.Boolean(related='move_id.manual_consumption', inverse='_inverse_manual_consumption')
    pick_type_create_components_lots = fields.Boolean(related='picking_type_id.use_create_components_lots')

    @api.depends('pick_type_create_components_lots', 'picking_code')
    def _compute_hide_lot_name(self):
        super()._compute_hide_lot_name()
        for line in self:
            production = line.production_id or line.move_id.production_id
            if production and line.tracking in ('lot', 'serial'):
                line.hide_lot = False
                line.hide_lot_name = True

    @api.depends('move_id', 'production_id')
    def _compute_parent_location_id(self):
        lines_not_in_production = self.env['stock.move.line']
        for line in self:
            # if component
            if line.production_id:
                line.parent_location_id = line.production_id.location_src_id
                line.parent_location_dest_id = line.production_id.production_location_id
            # if final product
            elif line.move_id.production_id:
                line.parent_location_id = line.move_id.production_id.production_location_id
                line.parent_location_dest_id = line.move_id.production_id.location_dest_id
            else:
                lines_not_in_production |= line
        super(StockMoveLine, lines_not_in_production)._compute_parent_location_id()

    def _inverse_manual_consumption(self):
        for rec in self:
            rec.move_id.manual_consumption = rec.manual_consumption

    @api.model_create_multi
    def create(self, vals):
        move_line_ids = super().create(vals)
        for ml in move_line_ids:
            if not ml.move_id and ml.production_id:
                # Try to find a move this move line belongs to
                if self.env.context.get('newByProduct'):
                    mrp_o2m_field = 'move_byproduct_ids'
                else:
                    mrp_o2m_field = 'move_raw_ids'
                candidate_moves = ml.production_id[mrp_o2m_field]
                move = candidate_moves.filtered(lambda m: m.product_id == ml.product_id)
                if not move:
                    # To avoid setting production_id when creating stock move we clear it from the context
                    move = self.env['stock.move'].with_context(default_production_id=None).create(ml._prepare_stock_move_vals())
                ml.move_id = move[0].id
        return move_line_ids

    def _prepare_stock_move_vals(self):
        move_vals = super()._prepare_stock_move_vals()
        if not self.production_id:
            return move_vals
        move_vals.update({
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'state': 'assigned',
            'picking_type_id': self.production_id.picking_type_id.id,
            'company_id': self.production_id.company_id.id
        })
        if self.env.context.get('newByProduct'):
            move_vals['production_id'] = self.production_id.id
        else:
            move_vals['raw_material_production_id'] = self.production_id.id
        return move_vals

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + ['description_bom_line', 'manual_consumption']
