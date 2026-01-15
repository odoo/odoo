# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True, index='btree_not_null')
    production_id = fields.Many2one('mrp.production', 'Production Order', check_company=True)

    @api.depends('production_id')
    def _compute_picking_type_id(self):
        line_to_remove = self.env['stock.move.line']
        for line in self:
            if production_id := line.production_id or line.move_id.production_id:
                line.picking_type_id = production_id.picking_type_id
                line_to_remove |= line
        return super(StockMoveLine, self - line_to_remove)._compute_picking_type_id()

    def _search_picking_type_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        domain = super()._search_picking_type_id(operator, value)
        return (Domain('production_id', '=', False) & domain) | Domain('production_id.picking_type_id', operator, value)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for line in res:
            # If the line is added in a done production, we need to map it
            # manually to the produced move lines in order to see them in the
            # traceability report
            if line.move_id.raw_material_production_id and line.state == 'done':
                mo = line.move_id.raw_material_production_id
                finished_lots = mo.lot_producing_ids
                finished_lots |= mo.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id).move_line_ids.lot_id
                if finished_lots:
                    produced_move_lines = mo.move_finished_ids.move_line_ids.filtered(lambda sml: sml.lot_id in finished_lots)
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
                else:
                    produced_move_lines = mo.move_finished_ids.move_line_ids
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
        return res

    def _get_similar_move_lines(self):
        lines = super()._get_similar_move_lines()
        if self.move_id.production_id:
            finished_moves = self.move_id.production_id.move_finished_ids
            finished_move_lines = finished_moves.mapped('move_line_ids')
            lines |= finished_move_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        if self.move_id.raw_material_production_id:
            raw_moves = self.move_id.raw_material_production_id.move_raw_ids
            raw_moves_lines = raw_moves.mapped('move_line_ids')
            lines |= raw_moves_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        return lines

    def write(self, vals):
        for move_line in self:
            production = move_line.move_id.production_id or move_line.move_id.raw_material_production_id
            if production and move_line.state == 'done' and any(field in vals for field in ('lot_id', 'location_id', 'quantity')):
                move_line._log_message(production, move_line, 'mrp.track_production_move_template', vals)
        return super().write(vals)

    def _get_aggregated_properties(self, move_line=False, move=False):
        aggregated_properties = super()._get_aggregated_properties(move_line, move)
        bom = aggregated_properties['move'].bom_line_id.bom_id
        aggregated_properties['bom'] = bom or False
        aggregated_properties['line_key'] += f'_{bom.id if bom else ""}'
        return aggregated_properties

    def _get_aggregated_product_quantities(self, **kwargs):
        """Returns dictionary of products and corresponding values of interest grouped by optional kit_name

        Removes descriptions where description == kit_name. kit_name is expected to be passed as a
        kwargs value because this is not directly stored in move_line_ids. Unfortunately because we
        are working with aggregated data, we have to loop through the aggregation to do this removal.

        arguments: kit_name (optional): string value of a kit name passed as a kwarg
        returns: dictionary {same_key_as_super: {same_values_as_super, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        kit_name = kwargs.get('kit_name')

        to_be_removed = []
        for aggregated_move_line in aggregated_move_lines:
            bom = aggregated_move_lines[aggregated_move_line]['bom']
            is_phantom = bom.type == 'phantom' if bom else False
            if kit_name:
                product = bom.product_id or bom.product_tmpl_id if bom else False
                display_name = product.display_name if product else False
                description = aggregated_move_lines[aggregated_move_line]['description']
                if not is_phantom or display_name != kit_name:
                    to_be_removed.append(aggregated_move_line)
                elif description == kit_name:
                    aggregated_move_lines[aggregated_move_line]['description'] = ""
            elif not kwargs and is_phantom:
                to_be_removed.append(aggregated_move_line)

        for move_line in to_be_removed:
            del aggregated_move_lines[move_line]

        return aggregated_move_lines

    def _prepare_stock_move_vals(self):
        move_vals = super()._prepare_stock_move_vals()
        if self.env['product.product'].browse(move_vals['product_id']).is_kits:
            move_vals['location_id'] = self.location_id.id
            move_vals['location_dest_id'] = self.location_dest_id.id
        return move_vals

    def _get_linkable_moves(self):
        """ Don't linke move lines with kit products to moves with dissimilar locations so that
        post `action_explode()` move lines will have accurate location data.
        """
        self.ensure_one()
        if self.product_id and self.product_id.is_kits:
            moves = self.picking_id.move_ids.filtered(lambda move:
                move.product_id == self.product_id and
                move.location_id == self.location_id and
                move.location_dest_id == self.location_dest_id
            )
            return sorted(moves, key=lambda m: m.quantity < m.product_qty, reverse=True)
        else:
            return super()._get_linkable_moves()

    def _exclude_requiring_lot(self):
        return (
            self.move_id.unbuild_id
            and not self.move_id.origin_returned_move_id.move_line_ids.lot_id
        ) or super()._exclude_requiring_lot()
