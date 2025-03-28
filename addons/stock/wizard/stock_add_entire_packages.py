# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockAddEntirePackages(models.TransientModel):
    _name = 'stock.add.entire.packages'
    _description = 'Add entire Packages'

    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)
    location_id = fields.Many2one('stock.location', compute='_compute_location_id')
    linked_package_ids = fields.Many2many('stock.package', 'stock_package_linked_package', 'link_id', 'package_id')
    new_package_ids = fields.Many2many('stock.package', string='Packages', required=True)

    def _compute_location_id(self):
        for wizard in self:
            wizard.location_id = wizard.picking_id.location_id

    def action_add_entire_packs(self):
        return self.picking_id.action_add_entire_packs(packages=self.new_package_ids)
