# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class StockBackorderConfirmationLine(models.TransientModel):
    _name = 'stock.backorder.confirmation.line'
    _description = 'Backorder Confirmation Line'

    backorder_confirmation_id = fields.Many2one('stock.backorder.confirmation', 'Immediate Transfer')
    picking_id = fields.Many2one('stock.picking', 'Transfer')
    to_backorder = fields.Boolean('To Backorder')


class StockBackorderConfirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_backorder_rel')
    show_transfers = fields.Boolean()
    backorder_confirmation_line_ids = fields.One2many(
        'stock.backorder.confirmation.line',
        'backorder_confirmation_id',
        string="Backorder Confirmation Lines")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'backorder_confirmation_line_ids' in fields and res.get('pick_ids'):
            res['backorder_confirmation_line_ids'] = [
                (0, 0, {'to_backorder': True, 'picking_id': pick_id})
                for pick_id in res['pick_ids'][0][2]
            ]
            # default_get returns x2m values as [(6, 0, ids)]
            # because of webclient limitations
        return res

    def _check_less_quantities_than_expected(self, pickings):
        for pick_id in pickings:
            moves_to_log = {}
            for move in pick_id.move_lines:
                if float_compare(move.product_uom_qty,
                                 move.quantity_done,
                                 precision_rounding=move.product_uom.rounding) > 0:
                    moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
            if moves_to_log:
                pick_id._log_less_quantities_than_expected(moves_to_log)

    def process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']
        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate).with_context(skip_backorder=True)
            if pickings_not_to_do:
                self._check_less_quantities_than_expected(pickings_not_to_do)
                pickings_to_validate = pickings_to_validate.with_context(picking_ids_not_to_backorder=pickings_not_to_do.ids)
            return pickings_to_validate.button_validate()
        return True

    def process_cancel_backorder(self):
        pickings_to_validate_ids = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate_ids:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate_ids)
            self._check_less_quantities_than_expected(pickings_to_validate)
            return pickings_to_validate\
                .with_context(skip_backorder=True, picking_ids_not_to_backorder=self.pick_ids.ids)\
                .button_validate()
        return True

