# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date = fields.Datetime(
        string='Expiration Date', compute='_compute_expiration_date', store=True,
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.')
    is_expired = fields.Boolean(related='lot_id.product_expiry_alert')
    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')

    def _auto_init(self):
        """ Create column for 'expiration_date' here to avoid MemoryError when letting
        the ORM compute it after module installation. Since both 'lot_id.expiration_date'
        and 'product_id.use_expiration_date' are new fields introduced in this module,
        there is no need for an UPDATE statement here.
        """
        if not column_exists(self._cr, "stock_move_line", "expiration_date"):
            create_column(self._cr, "stock_move_line", "expiration_date", "timestamp")
        return super()._auto_init()

    @api.depends('product_id', 'picking_type_use_create_lots', 'lot_id.expiration_date', 'picking_id.scheduled_date')
    def _compute_expiration_date(self):
        for move_line in self:
            if not move_line.expiration_date and move_line.lot_id.expiration_date:
                move_line.expiration_date = move_line.lot_id.expiration_date
            elif move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date:
                    if not move_line.expiration_date:
                        from_date = move_line.picking_id.scheduled_date or fields.Datetime.today()
                        move_line.expiration_date = from_date + datetime.timedelta(days=move_line.product_id.expiration_time)
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
