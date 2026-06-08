# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPackageDestination(models.TransientModel):
    _name = 'stock.package.destination'
    _description = 'Stock Package Destination'

    move_line_ids = fields.Many2many('stock.move.line', 'Products', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination location', required=True)
    filtered_location = fields.One2many(comodel_name='stock.location', compute='_compute_filtered_location')

    @api.depends('move_line_ids')
    def _compute_filtered_location(self):
        for wizard in self:
            wizard.filtered_location = wizard.move_line_ids.mapped('location_dest_id')

    def action_done(self):
        # set the same location on each move line and pass again in action_put_in_pack
        self.move_line_ids.location_dest_id = self.location_dest_id
        return self.move_line_ids.action_put_in_pack()
