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

    @api.depends('product_id', 'picking_type_use_create_lots', 'lot_id.expiration_date')
    def _compute_expiration_date(self):
        for move_line in self:
            if not move_line.expiration_date and move_line.lot_id.expiration_date:
                move_line.expiration_date = move_line.lot_id.expiration_date
            elif move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date:
                    if not move_line.expiration_date:
                        move_line.expiration_date = fields.Datetime.today() + datetime.timedelta(days=move_line.product_id.expiration_time)
                else:
                    move_line.expiration_date = False

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if not self.picking_type_use_existing_lots or not self.product_id.use_expiration_date:
            return
        if self.lot_id:
            self.expiration_date = self.lot_id.expiration_date
        else:
            self.expiration_date = False

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        res = super()._onchange_product_id()
        if self.picking_type_use_create_lots:
            if self.product_id.use_expiration_date:
                self.expiration_date = fields.Datetime.today() + datetime.timedelta(days=self.product_id.expiration_time)
            else:
                self.expiration_date = False
        return res

    def _assign_production_lot(self, lot):
        super()._assign_production_lot(lot)
        self.lot_id._update_date_values(self[0].expiration_date)
