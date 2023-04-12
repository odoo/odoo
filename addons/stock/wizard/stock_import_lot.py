from odoo import fields, models


class StockImportLot(models.TransientModel):
    _name = 'stock.import.lot'
    _description = 'Import lots or serial numbers to create stock move lines'

    move_id = fields.Many2one('stock.move')
    lots = fields.Text('Lots')
    move_location_dest_id = fields.Many2one('stock.location', 'Move Destination Location', related='move_id.location_dest_id')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', domain="[('id', 'child_of', move_location_dest_id)]")
    picking_code = fields.Selection(related='move_id.picking_code')


    def action_import_lot(self):
        """ Create stock move lines with imported lot/quantity as well as stock
        quant in the move source location with 0 quantity if they don't exist
        """
        self.ensure_one()
        self.move_id._import_lots(self.lots, location_id=self.location_dest_id)
        return self.move_id.action_show_details()
