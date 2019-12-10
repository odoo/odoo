# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date_readonly = fields.Boolean(compute='_compute_expiration_date_readonly')
    expiration_date = fields.Datetime(string='Expiration Date',
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.')

    @api.depends('picking_id', 'product_id')
    def _compute_expiration_date_readonly(self):
        for line in self:
            line.expiration_date_readonly = bool(not line.picking_id.picking_type_id.use_existing_lots and line.product_id.use_expiration_date)

    @api.onchange('product_id', 'product_uom_id')
    def onchange_product_id(self):
        res = super(StockMoveLine, self).onchange_product_id()
        if self.picking_type_use_create_lots:
            if self.product_id.use_expiration_date:
                self.expiration_date = fields.Datetime.today() + datetime.timedelta(days=self.product_id.expiration_time)
            else:
                self.expiration_date = False
        return res

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if not self.picking_type_use_existing_lots or not self.product_id.use_expiration_date:
            return
        if self.lot_id:
            self.expiration_date = self.lot_id.expiration_date
        else:
            self.expiration_date = False

    def _create_and_assign_production_lot(self):
        super(StockMoveLine, self)._create_and_assign_production_lot()
        self.lot_id._update_date_values(self.expiration_date)
