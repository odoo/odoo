# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPutInPack(models.TransientModel):
    _name = 'stock.put.in.pack'
    _description = 'Put In Pack'

    package_type_id = fields.Many2one('stock.package.type', 'Package Type')
    package_ids = fields.Many2many('stock.package', string='Packages')
    move_line_ids = fields.Many2many('stock.move.line', string='Move lines')

    def action_put_in_pack(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'stock.package':
            return self.package_ids.action_put_in_pack(package_type_id=self.package_type_id.id)
        elif active_model == 'stock.move.line':
            return self.move_line_ids.action_put_in_pack(package_type_id=self.package_type_id.id)
        else:
            raise NotImplementedError(self.env._("This operation is not supported for this type of record."))
