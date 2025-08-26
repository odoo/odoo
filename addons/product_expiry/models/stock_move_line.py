# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date = fields.Datetime(
        string='Expiration Date', compute='_compute_expiration_date', store=True,
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.')
    is_expired = fields.Boolean(related='lot_id.product_expiry_alert')
    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')

    def _get_fields_to_skip_compute_on_init(self):
        fields_to_skip_compute = super()._get_fields_to_skip_compute_on_init()
        fields_to_skip_compute.update([
            'expiration_date',
        ])
        return fields_to_skip_compute

    @api.depends('product_id', 'lot_id.expiration_date', 'picking_id.scheduled_date')
    def _compute_expiration_date(self):
        for move_line in self:
            if move_line.lot_id.expiration_date:
                move_line.expiration_date = move_line.lot_id.expiration_date
            elif move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date:
                    if not move_line.expiration_date:
                        from_date = move_line.picking_id.scheduled_date or fields.Datetime.today()
                        move_line.expiration_date = from_date + datetime.timedelta(days=move_line.product_id.expiration_time)
                else:
                    move_line.expiration_date = False

    @api.onchange('product_id', 'product_uom_id', 'picking_id')
    def _onchange_product_id(self):
        res = super()._onchange_product_id()
        if self.picking_type_use_create_lots:
            if self.product_id.use_expiration_date:
                from_date = self.picking_id.scheduled_date or fields.Datetime.today()
                self.expiration_date = from_date + datetime.timedelta(days=self.product_id.expiration_time)
            else:
                self.expiration_date = False
        return res

    def _prepare_new_lot_vals(self):
        vals = super()._prepare_new_lot_vals()
        if self.expiration_date:
            vals['expiration_date'] = self.expiration_date
        return vals
