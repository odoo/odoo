# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockNotEntirePackWarning(models.TransientModel):
    _name = 'stock.not.entire.pack.warning'
    _description = 'Package No Longer Entire Warning'

    move_line_ids = fields.Many2many('stock.move.line')
    package_ids = fields.Many2many('stock.package', compute='_compute_package_ids')

    def _compute_package_ids(self):
        for wizard in self:
            wizard.package_ids = wizard.move_line_ids.package_id

    def unpack(self):
        self.move_line_ids.with_context(skip_entire_packs_check=True).write({
            'result_package_id': False,
        })
        picking_ids_to_validate = self.env.context.get('button_validate_picking_ids')
        if picking_ids_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(picking_ids_to_validate)
            return pickings_to_validate.with_context(skip_entire_packs=True).button_validate()
        return True
