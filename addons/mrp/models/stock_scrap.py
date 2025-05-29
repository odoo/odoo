# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        check_company=True)
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order',
        check_company=True) # Not to restrict or prefer quants, but informative
    product_is_kit = fields.Boolean(related='product_id.is_kits')
    product_template = fields.Many2one(related='product_id.product_tmpl_id')
    bom_id = fields.Many2one(
        'mrp.bom', 'Kit',
        domain="[('type', '=', 'phantom'), '|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_template)]",
        check_company=True)

    @api.depends('workorder_id', 'production_id')
    def _compute_location_id(self):
        remaining_scrap = self.browse()

        for scrap in self:
            if scrap.production_id:
                if scrap.production_id.state != 'done':
                    scrap.location_id = scrap.production_id.location_src_id.id
                else:
                    scrap.location_id = scrap.production_id.location_dest_id.id
            elif scrap.workorder_id:
                scrap.location_id = scrap.workorder_id.production_id.location_src_id.id
            else:
                remaining_scrap |= scrap

        res = super(StockScrap, remaining_scrap)._compute_location_id()
        return res

    def _prepare_move_values(self):
        vals = super(StockScrap, self)._prepare_move_values()
        if self.production_id:
            vals['origin'] = vals['origin'] or self.production_id.name
            if self.product_id in self.production_id.move_finished_ids.mapped('product_id'):
                vals.update({'production_id': self.production_id.id})
            else:
                vals.update({'raw_material_production_id': self.production_id.id})
        return vals

    @api.onchange('lot_id')
    def _onchange_serial_number(self):
        if self.product_id.tracking == 'serial' and self.lot_id:
            if self.production_id:
                message, recommended_location = self.env['stock.quant'].sudo()._check_serial_number(self.product_id,
                                                                                                    self.lot_id,
                                                                                                    self.company_id,
                                                                                                    self.location_id,
                                                                                                    self.production_id.location_dest_id)
                if message:
                    if recommended_location:
                        self.location_id = recommended_location
                    return {'warning': {'title': _('Warning'), 'message': message}}
            else:
                return super()._onchange_serial_number()

    @api.depends('move_ids', 'move_ids.move_line_ids.quantity', 'product_id')
    def _compute_scrap_qty(self):
        self.scrap_qty = 1
        for scrap in self:
            if not scrap.bom_id:
                return super(StockScrap, scrap)._compute_scrap_qty()
            if scrap.move_ids:
                filters = {
                    'incoming_moves': lambda m: True,
                    'outgoing_moves': lambda m: False
                }
                scrap.scrap_qty = scrap.move_ids._compute_kit_quantities(scrap.product_id, scrap.scrap_qty, scrap.bom_id, filters)

    def _should_check_available_qty(self):
        return super()._should_check_available_qty() or self.product_is_kit

    def do_replenish(self, values=False):
        self.ensure_one()
        values = values or {}
        if self.production_id and self.production_id.procurement_group_id:
            values.update({
                'group_id': self.production_id.procurement_group_id,
            })
        super().do_replenish(values)
