# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import frozendict


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_barcode = fields.Char(related='product_id.barcode')
    location_processed = fields.Boolean()
    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')
    parent_location_id = fields.Many2one('stock.location', compute='_compute_parent_location_id')
    parent_location_dest_id = fields.Many2one('stock.location', compute='_compute_parent_location_id')
    product_stock_quant_ids = fields.One2many('stock.quant', compute='_compute_product_stock_quant_ids')
    product_packaging_id = fields.Many2one(related='move_id.product_packaging_id')
    product_packaging_uom_qty = fields.Float('Packaging Quantity', compute='_compute_product_packaging_uom_qty', help="Quantity of the Packaging in the UoM of the Stock Move Line.")
    hide_lot_name = fields.Boolean(compute='_compute_hide_lot_name')
    hide_lot = fields.Boolean(compute='_compute_hide_lot_name')
    image_1920 = fields.Image(related="product_id.image_1920")
    product_reference_code = fields.Char(related="product_id.code", string="Product Reference Code")
    qty_done = fields.Float(compute='_compute_qty_done', inverse='_inverse_qty_done')  # Dummy field

    @api.depends('tracking', 'picking_type_use_existing_lots', 'picking_type_use_create_lots', 'lot_name')
    def _compute_hide_lot_name(self):
        for line in self:
            if line.tracking == 'none':
                line.hide_lot_name = True
                line.hide_lot = True
                continue
            line.hide_lot_name = not line.picking_type_use_create_lots or (line.picking_type_use_existing_lots and not line.lot_name)
            line.hide_lot = not line.picking_type_use_existing_lots or (line.picking_type_use_create_lots and line.lot_name)

    @api.depends('picking_id')
    def _compute_parent_location_id(self):
        for line in self:
            line.parent_location_id = line.picking_id.location_id
            line.parent_location_dest_id = line.picking_id.location_dest_id

    def _compute_product_stock_quant_ids(self):
        for line in self:
            line.product_stock_quant_ids = line.product_id.stock_quant_ids.filtered(lambda q: q.company_id in self.env.companies and q.location_id.usage == 'internal')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _compute_qty_done(self):
        for line in self:
            line.qty_done = line.quantity if line.picked else 0

    def _compute_product_packaging_uom_qty(self):
        for sml in self:
            sml.product_packaging_uom_qty = sml.product_packaging_id.product_uom_id._compute_quantity(sml.product_packaging_id.qty, sml.product_uom_id)

    def _inverse_dummy_id(self):
        pass

    def _inverse_qty_done(self):
        for line in self:
            line.quantity = line.qty_done
            line.picked = line.quantity > 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # To avoid a write on `quantity` at the creation of the record (in the `qty_done`
            # inverse, when the line's move is not created yet), we set the `quantity` directly at
            # the creation and remove `qty_done` in the meantime.
            if 'qty_done' in vals:
                vals['quantity'] = vals['qty_done']
                vals['picked'] = vals['qty_done'] > 0
                del vals['qty_done']
                # Also delete the default value in the context.
                self.env.context = frozendict({k: v for k, v in self.env.context.items() if k != 'default_qty_done'})
        return super().create(vals_list)


    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'product_category_name',
            'location_id',
            'location_dest_id',
            'move_id',
            'qty_done',
            'quantity',
            'display_name',
            'product_uom_id',
            'product_barcode',
            'owner_id',
            'lot_id',
            'lot_name',
            'package_id',
            'result_package_id',
            'dummy_id',
            'picked',
            'product_packaging_id',
            'product_packaging_uom_qty',
            'move_id',
        ]
