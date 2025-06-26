# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    zip = fields.Char(related='partner_id.zip', string='Zip', search="_search_zip")

    def _search_zip(self, operator, value):
        return [('partner_id.zip', operator, value)]

    def write(self, vals):
        res = super().write(vals)
        if 'batch_id' not in vals:
            return res
        batch = self.env['stock.picking.batch'].browse(vals.get('batch_id'))
        if batch and batch.dock_id:
            batch._set_moves_destination_to_dock()
        else:
            self._reset_location()
        return res

    def _reset_location(self):
        for picking in self:
            moves = picking.move_ids.filtered(lambda m: not m.location_dest_id._child_of(picking.location_dest_id))
            moves.write({'location_dest_id': picking.location_dest_id.id})
