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
    remaining_packed_qty = fields.Float('Packed Remaining Quantity', compute='_compute_remaining_packed_qty',
                                        store=True)
    released_manual = fields.Boolean('Packed', default=False)
    pc_container_code = fields.Char(string='PC Container code')


    @api.depends('quantity')
    def _compute_remaining_packed_qty(self):
        """
        Compute remaining quantity based on the quantity ordered (product_uom_qty)
        and the quantity done (quantity). Remaining qty is initially equal to available qty.
        """
        for move in self:
            # Initial remaining qty is the product_uom_qty (expected qty)
            move.remaining_packed_qty = move.quantity
            # move.is_remaining_qty = move.remaining_qty > 0

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
            # Only if code and picking are set
            if move.pc_container_code and move.picking_id:
                picking = move.picking_id
                if picking.site_code_id:
                    code = move.pc_container_code.strip()
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

