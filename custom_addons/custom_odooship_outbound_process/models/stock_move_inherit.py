# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"


    packed = fields.Boolean('Packed', default=False)
    released_manual_orders = fields.Selection([('partial_pack','Partial Packed'),
                                        ('fully_pack','Fully Packed')],
                                       string='Packed Orders')
    # released_manual = fields.Boolean('Packed', default=False)
    pc_container_code = fields.Char(string='PC Container code')
    picked_qty = fields.Float(
        string='Picked Quantity',
        default=0.0,
        help="Quantity that has been picked."
    )
    packed_qty = fields.Float(
        string='Packed Quantity',
        default=0.0,
        help="Quantity that has been packed."
    )
    remaining_picked_qty = fields.Float(
        string='Remaining Picked Quantity',
        # compute='_compute_remaining_picked_qty',
        store=True,
        help="Quantity remaining to be picked."
    )

    remaining_packed_qty = fields.Float(
        string='Remaining Packed Quantity',
        # compute='_compute_remaining_packed_qty',
        store=True,
        help="Quantity remaining to be packed."
    )

    # @api.depends('product_uom_qty', 'picked_qty')
    # def _compute_remaining_picked_qty(self):
    #     for move in self:
    #         print("\n\n\n mmove picked ==", move)
    #         # move.remaining_picked_qty = move.product_uom_qty - move.picked_qty
    #
    # @api.depends('picked_qty', 'packed_qty')
    # def _compute_remaining_packed_qty(self):
    #     for move in self:
    #         print("\n\n\n packed qty=====",  move)
    #         move.remaining_packed_qty = move.picked_qty - move.packed_qty

    @api.onchange('packed')
    def _onchange_packed(self):
        """
        Prevent unpacking if the item is already marked as manually released.
        """
        for move in self:
            if not move.packed and move.released_manual:
                raise ValidationError("This item has already been delivered manually and cannot be unpacked.")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._ensure_pc_barcode_config()
        return res

    def write(self, vals):
        result = super().write(vals)
        self._ensure_pc_barcode_config()
        return result

    def _ensure_pc_barcode_config(self):
        BarcodeConfig = self.env['pc.container.barcode.configuration']
        for move in self:
            if move.pc_container_code and move.picking_id and move.picking_id.site_code_id:
                codes = [code.strip() for code in move.pc_container_code.split(',') if code.strip()]
                picking = move.picking_id
                for code in codes:
                    exists = BarcodeConfig.search([
                        ('name', '=', code),
                        ('site_code_id', '=', picking.site_code_id.id)
                    ], limit=1)
                    if not exists:
                        BarcodeConfig.create({
                            'name': code,
                            'site_code_id': picking.site_code_id.id,
                            'warehouse_id': picking.warehouse_id.id,
                        })


