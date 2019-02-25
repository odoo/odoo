# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class StockDuplicateWarning(models.TransientModel):
    _name = 'stock.duplicate.warning'
    _description = 'Stock Duplicate Warning'

    tracking_line_ids = fields.One2many('stock.duplicate.line', 'wizard_id')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')

    @api.one
    def action_confirm(self):
        # Add correction line directly into the inventory
        for line in self.tracking_line_ids:
            if line.to_correct:
                # check if the correction line is already present we just need to update it
                dup = self.inventory_id.line_ids.filtered(lambda l: l.product_id == line.product_id and l.prod_lot_id == line.lot_id and l.location_id == line.location_id)
                if dup:
                    dup.write({
                        'product_qty': 0,
                        'correction_line': 'warning'
                    })
                else:
                    self.env['stock.inventory.line'].create({
                        'inventory_id': self.inventory_id.id,
                        'location_id': line.location_id.id,
                        'product_id': line.product_id.id,
                        'prod_lot_id': line.lot_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'theoretical_qty': 1,
                        'correction_line': 'warning',
                    })
                line.inventory_line_id.correction_line = False
            else:
                # Cancel the inventory for this serial number to keep the old
                # quant
                line.inventory_line_id.correction_line = 'danger'

class StockDuplicatesLines(models.TransientModel):
    _name = 'stock.duplicate.line'
    _description = 'Stock duplicate Line'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', readonly=True)
    product_qty = fields.Float('Actual quantity', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Serial Number', readonly=True)
    wizard_id = fields.Many2one('stock.duplicate.warning', readonly=True)
    to_correct = fields.Boolean('Use correction line ?', default=True)
    inventory_line_id = fields.Many2one('stock.inventory.line')
