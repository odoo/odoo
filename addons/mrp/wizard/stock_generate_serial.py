from odoo import fields, models


class StockGenerateSerial(models.TransientModel):
    _inherit = 'stock.generate.serial'

    stock_assign_serial_id = fields.Many2one('stock.assign.serial')

    def generate_serial_numbers_production(self):
        if self.next_serial and self.next_serial_count:
            generated_serial_numbers = "\n".join(lot[0] for lot in self.env['stock.lot'].generate_lot_names(self.next_serial, self.next_serial_count))
            self.stock_assign_serial_id.lot_numbers = f'{generated_serial_numbers}'
            self.stock_assign_serial_id._onchange_serial_numbers()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.act_assign_serial_numbers_production")
        action['context'] = {
            'from_generate_sn_wizard': True,
        }
        action['res_id'] = self.stock_assign_serial_id.id
        return action
