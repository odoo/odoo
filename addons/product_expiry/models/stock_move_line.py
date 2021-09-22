# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date = fields.Datetime(string='Expiration Date', compute='_compute_expiration_date', store=True,
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.')

    @api.depends('product_id', 'picking_type_use_create_lots')
    def _compute_expiration_date(self):
        for move_line in self:
            if move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date:
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

    def _assign_production_lot(self, lot):
        super()._assign_production_lot(lot)
        self.lot_id._update_date_values(self.expiration_date)
