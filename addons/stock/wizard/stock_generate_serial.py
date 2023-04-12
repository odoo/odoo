from odoo import _, fields, models
from odoo.exceptions import UserError


class StockGenerateSerial(models.TransientModel):
    _name = 'stock.generate.serial'
    _description = 'Generate serial number from a pattern'

    move_id = fields.Many2one('stock.move')
    next_serial = fields.Char('First SN')
    next_serial_count = fields.Integer('Number of SN')
    move_location_dest_id = fields.Many2one('stock.location', 'Move Destination Location', related='move_id.location_dest_id')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', domain="[('id', 'child_of', move_location_dest_id)]")
    picking_code = fields.Selection(related='move_id.picking_code')


    def action_generate_serial(self):
        """ On `self.move_line_ids`, assign `lot_name` according to
        `self.next_serial` before returning `self.action_show_details`.
        """
        self.ensure_one()
        if not self.next_serial:
            raise UserError(_("You need to set a Serial Number before generating more."))
        self.move_id._generate_serial_numbers(self.next_serial, self.next_serial_count, location_id=self.location_dest_id)
        return self.move_id.action_show_details()
