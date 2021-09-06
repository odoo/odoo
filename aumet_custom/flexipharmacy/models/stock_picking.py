# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import Warning, UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Warehouse
    def _prepare_stock_move_vals(self, first_line, order_lines):
        return {
            'name': first_line.name,
            'product_uom': first_line.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': first_line.product_id.id,
            'product_uom_qty': abs(sum(order_lines.mapped('qty'))),
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    # internal transfer
    @api.model
    def internal_transfer(self, vals):
        if vals:
            picking_id = self.create({'location_id': vals.get('location_src_id'),
                                      'state': 'draft',
                                      'move_lines': [(0, 0, move_line) for move_line in
                                                     vals.get('moveLines')],
                                      'location_dest_id': vals.get('location_dest_id'),
                                      'picking_type_id': vals.get('picking_type_id')})
            if picking_id:
                if vals.get('state') == 'confirmed':
                    picking_id.action_confirm()
                if vals.get('state') == 'done':
                    picking_id.action_confirm()
                    picking_id.action_assign()
                    wizard = self.env['stock.immediate.transfer'].with_context(
                        dict(self.env.context, default_show_transfers=False,
                             default_pick_ids=[(4, picking_id.id)])).create({})
                    wizard.process()
                    picking_id.button_validate()
            return [picking_id.id, picking_id.name]
        return []

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False,
                                             is_delivery_charge=False):
        """We'll create some picking based on order_lines"""
        pickings = self.env['stock.picking']
        if not is_delivery_charge:
            stockable_lines = lines.filtered(
                lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                          precision_rounding=l.product_id.uom_id.rounding) and not l.order_id.is_delivery_charge)
        else:
            stockable_lines = lines.filtered(
                lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                          precision_rounding=l.product_id.uom_id.rounding))
        if not stockable_lines:
            return pickings
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            try:
                with self.env.cr.savepoint():
                    if not is_delivery_charge:
                        positive_picking._action_done()
            except (UserError, ValidationError):
                pass

            pickings |= positive_picking
        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking
        if is_delivery_charge:
            filtered_lines = lines.filtered(lambda l: l.order_id.is_delivery_charge)
            delivery_date = self.env['pos.order.line'].search([('id', 'in', filtered_lines.ids)],
                                                              limit=1).order_id.delivery_date
            pickings.write({
                'scheduled_date': delivery_date
            })
        return pickings
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
