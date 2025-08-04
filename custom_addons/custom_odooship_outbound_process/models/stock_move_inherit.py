# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"


    packed = fields.Boolean('Packed', default=False)
    pick_status = fields.Selection([
        ('partial_pick', 'Partial Picked'),
        ('fully_pick', 'Fully Picked'),
        ('partial_pack','Partial Packed'),
        ('fully_pack','Fully Packed')],
        string='Pick Status')
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

    @api.onchange('picked_qty')
    def _onchange_picked_qty(self):
        for move in self:
            move.remaining_picked_qty = move.product_uom_qty - move.picked_qty
            if move.remaining_picked_qty !=0:
                move.pick_status = 'partial_pick'
                move.picked = False
            else:
                move.pick_status = 'fully_pick'
                move.picked = True

    @api.onchange('packed_qty')
    def _onchange_packed_qty(self):
        for move in self:
            move.remaining_packed_qty = move.picked_qty - move.packed_qty
            if move.remaining_packed_qty !=0:
                move.pick_status = 'partial_pack'
            else:
                move.pick_status = 'fully_pack'
                move.packed = True
            #  Check if all lines in the picking are packed
            if move.picking_id and all(m.packed for m in move.picking_id.move_ids_without_package):
                move.picking_id.current_state = 'pack'

    def _update_picking_current_state(self):
        for move in self:
            picking = move.picking_id
            if not picking:
                continue
            moves = picking.move_ids_without_package
            fully_picked = all(m.picked_qty >= m.product_uom_qty and m.product_uom_qty > 0 for m in moves)
            any_picked = any(m.picked_qty > 0 for m in moves)
            if fully_picked:
                picking.current_state = 'pick'
            elif any_picked:
                picking.current_state = 'partially_pick'
            else:
                picking.current_state = 'draft'


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
        res._update_picking_current_state()
        return res

    def write(self, vals):
        result = super().write(vals)
        # Only update for the affected lines (self)
        for move in self:
            # Update remaining_picked_qty if picked_qty changed
            if 'picked_qty' in vals:
                move.remaining_picked_qty = move.product_uom_qty - move.picked_qty
                move.picked = move.remaining_picked_qty == 0
                move.pick_status = 'fully_pick' if move.picked else 'partial_pick'
                # If pick_status changed to 'partial_pick', set allow_partial if allowed by tenant
                if vals.get('pick_status') == 'partial_pick' and move.picking_id:
                    tenant = move.picking_id.tenant_code_id or move.picking_id.sale_id.tenant_code_id
                    if tenant and tenant.allow_partial_packing:
                        move.picking_id.allow_partial = True
            # Update remaining_packed_qty if packed_qty changed
            if 'packed_qty' in vals:
                move.remaining_packed_qty = move.picked_qty - move.packed_qty
                move.packed = move.remaining_packed_qty == 0
                move.pick_status = 'fully_pack' if move.packed else 'partial_pack'
                # If all moves are packed, update picking state
                if move.picking_id and all(m.packed for m in move.picking_id.move_ids_without_package):
                    move.picking_id.current_state = 'pack'
                #  Update quantity if operation type is 'pick'
                if move.picking_id and move.picking_id.operation_process_type == 'pick':
                    move.quantity = move.packed_qty

        self._ensure_pc_barcode_config()
        if 'picked_qty' in vals:
            self._update_picking_current_state()
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


