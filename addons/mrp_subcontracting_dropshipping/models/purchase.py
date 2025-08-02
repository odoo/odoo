# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    default_location_dest_id_is_subcontracting_loc = fields.Boolean(compute='_compute_default_location_dest_id_is_subcontracting_loc')

    @api.depends('picking_type_id.default_location_dest_id')
    def _compute_default_location_dest_id_is_subcontracting_loc(self):
        for order in self:
            order.default_location_dest_id_is_subcontracting_loc = order.picking_type_id.default_location_dest_id.is_subcontract()

    @api.depends('default_location_dest_id_is_subcontracting_loc')
    def _compute_dest_address_id(self):
        dropship_subcontract_pos = self.filtered(lambda po: po.default_location_dest_id_is_subcontracting_loc)
        for order in dropship_subcontract_pos:
            subcontractor_ids = order.picking_type_id.default_location_dest_id.subcontractor_ids
            if len(subcontractor_ids) == 1:
                order.dest_address_id = subcontractor_ids
        super(PurchaseOrder, self - dropship_subcontract_pos)._compute_dest_address_id()

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.default_location_dest_id_is_subcontracting_loc:
            return {
                'warning': {'title': _('Warning'), 'message': _('Please note this purchase order is for subcontracting purposes.')}
            }

    def _get_destination_location(self):
        self.ensure_one()
        if self.default_location_dest_id_is_subcontracting_loc:
            return self.dest_address_id.property_stock_subcontractor.id
        return super()._get_destination_location()
