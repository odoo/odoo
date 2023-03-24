# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_dropship = fields.Boolean("Is a Dropship", compute='_compute_is_dropship')

    @api.depends('location_dest_id.usage', 'location_id.usage')
    def _compute_is_dropship(self):
        for picking in self:
            picking.is_dropship = picking.picking_type_id.code == 'dropship'

    def _is_to_external_location(self):
        self.ensure_one()
        return super()._is_to_external_location() or self.is_dropship


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(
        selection_add=[('dropship', 'Dropship')], ondelete={'dropship': 'cascade'})

    @api.depends('default_location_src_id', 'default_location_dest_id')
    def _compute_warehouse_id(self):
        dropship_records = self.filtered(lambda t: t.code == 'dropship')
        dropship_records.warehouse_id = False
        super(StockPickingType, self - dropship_records)._compute_warehouse_id()

    @api.depends('code')
    def _compute_show_picking_type(self):
        dropship_records = self.filtered(lambda t: t.code == 'dropship')
        dropship_records.show_picking_type = True
        super(StockPickingType, self - dropship_records)._compute_show_picking_type()
