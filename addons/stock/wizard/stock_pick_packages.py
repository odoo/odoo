# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PickPack(models.TransientModel):
    _name = 'stock.pick.packages'
    _description = 'Add package on a picking'

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError(_("You may only add packages for one picking at a time."))
        res = super(PickPack, self).default_get(fields)
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if picking:
            res.update({'picking_id': picking.id})
        return res

    picking_id = fields.Many2one('stock.picking')
    package_ids = fields.Many2many('stock.quant.package')

    entire_package_ids = fields.One2many('stock.quant.package', related='picking_id.entire_package_ids')

    def action_add_packages(self):
        values = self._pick_packages(self.picking_id, self.package_ids)
        for move_values, move_line_values in values:
            move_id = self.env['stock.move'].create(move_values)
            move_line_values.update({'move_id': move_id.id})
            self.env['stock.move.line'].create(move_line_values)

    def _pick_packages(self, picking, packages):
        result = []
        for package in packages:
            for quant in package.quant_ids:
                result.append(self._pick_quant(quant, picking, package))
        return result

    def _pick_quant(self, quant, picking, package, quantity=0):
        destination_location = self.env.context.get('destination_location')
        if not destination_location:
            destination_location = picking.location_dest_id.id
        common_values = {
            'picking_id': picking.id,
            'product_id': quant.product_id.id,
            'location_id': quant.location_id.id,
            'location_dest_id': destination_location,
        }
        move_values = {
            'name': _('New Move:') + quant.product_id.display_name,
            'product_uom': quant.product_uom_id.id,
        }
        move_line_values = {
            'lot_id': quant.lot_id.id,
            'owner_id': quant.owner_id.id,
            'package_id': package.id,
            'result_package_id': package.id,
            'qty_done': quantity and quantity or quant.quantity,
            'product_uom_id': quant.product_uom_id.id,
        }
        move_values.update(common_values)
        move_line_values.update(common_values)
        return move_values, move_line_values
