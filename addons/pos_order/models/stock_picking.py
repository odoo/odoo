from odoo import models, api


class StockPicking(models.Model):
    _inherit='stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):

        pos_order = lines.mapped("order_id")
        pickings = self.env['stock.picking']            
        existing_picking = self.search([
            ('pos_order_id', '=', pos_order.id),
            ('picking_type_id', '=', picking_type.id),
            ('state', '!=', 'done')
        ], limit=1)
        
        if not pos_order.select_date:
            return super()._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type)
        
        if existing_picking:
            try:
                with self.env.cr.savepoint():
                    existing_picking._action_done()
                return existing_picking
            except Exception as e:
                print(f"Error while completing picking: {e}")
                return existing_picking
    
            
        stockable_lines = lines.filtered(lambda l: l.product_id.type == 'consu' and l.qty != 0)
        if not stockable_lines:
            return pickings

        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            self.env.flush_all()   
            
            pickings |= positive_picking   

        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            self.env.flush_all()
                
            pickings |= negative_picking

        return pickings
