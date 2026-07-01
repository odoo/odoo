# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date = fields.Datetime(
        string='Expiration Date', compute='_compute_expiration_date', store=True,
        help='This is the date on which the goods with this Serial Number may'
        ' become dangerous and must not be consumed.', init_column=lambda model: None)
    removal_date = fields.Datetime(string='Removal Date', compute='_compute_removal_date', readonly=False, store=True, init_column=lambda model: None)
    is_expired = fields.Boolean(related='lot_id.product_expiry_alert')
    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')

    @api.depends('product_id', 'lot_id.expiration_date', 'picking_id.scheduled_date', 'quant_id')
    def _compute_expiration_date(self):
        for move_line in self:
            if lot_id := move_line.quant_id.lot_id or move_line.lot_id:
                move_line.expiration_date = lot_id.expiration_date
            elif move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date:
                    if not move_line.expiration_date:
                        from_date = move_line.picking_id.scheduled_date or fields.Datetime.today()
                        move_line.expiration_date = from_date + datetime.timedelta(days=move_line.product_id.expiration_time)
                else:
                    move_line.expiration_date = False

    @api.depends('product_id', 'expiration_date', 'lot_id.removal_date')
    def _compute_removal_date(self):
        for move_line in self:
            if move_line.lot_id.removal_date:
                move_line.removal_date = move_line.lot_id.removal_date
            elif move_line.picking_type_use_create_lots:
                if move_line.product_id.use_expiration_date and move_line.expiration_date:
                    move_line.removal_date = move_line.expiration_date - datetime.timedelta(days=move_line.product_id.removal_time)
                else:
                    move_line.removal_date = False

    def _prepare_new_lot_vals(self):
        vals = super()._prepare_new_lot_vals()
        if self.expiration_date:
            vals['expiration_date'] = self.expiration_date
        return vals
