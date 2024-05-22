# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockImmediateTransferLine(models.TransientModel):
    _name = 'stock.immediate.transfer.line'
    _description = 'Immediate Transfer Line'

    immediate_transfer_id = fields.Many2one('stock.immediate.transfer', 'Immediate Transfer', required=True)
    picking_id = fields.Many2one('stock.picking', 'Transfer', required=True)
    to_immediate = fields.Boolean('To Process')


class StockImmediateTransfer(models.TransientModel):
    _name = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_transfer_rel')
    show_transfers = fields.Boolean()
    immediate_transfer_line_ids = fields.One2many(
        'stock.immediate.transfer.line',
        'immediate_transfer_id',
        string="Immediate Transfer Lines")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'immediate_transfer_line_ids' in fields and res.get('pick_ids'):
            res['immediate_transfer_line_ids'] = [
                (0, 0, {'to_immediate': True, 'picking_id': pick_id})
                for pick_id in res['pick_ids'][0][2]
            ]
            # default_get returns x2m values as [(6, 0, ids)]
            # because of webclient limitations
        return res

    def process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        for picking in pickings_to_do:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty

        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate)
            pickings_to_validate = pickings_to_validate - pickings_not_to_do
            return pickings_to_validate.with_context(skip_immediate=True).button_validate()
        return True

