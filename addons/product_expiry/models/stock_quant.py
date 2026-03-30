# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    expiration_date = fields.Datetime(compute='_compute_expiration_date', inverse='_inverse_expiration_date', store=True)
    removal_date = fields.Datetime(related='lot_id.removal_date', store=True)
    use_expiration_date = fields.Boolean(related='product_id.use_expiration_date')
    available_quantity = fields.Float(help="On hand quantity which hasn't been reserved on a transfer and is still fresh, in the default unit of measure of the product")

    def _get_gs1_barcode(self, gs1_quantity_rules_ai_by_uom=False):
        barcode = super()._get_gs1_barcode(gs1_quantity_rules_ai_by_uom)
        if self.use_expiration_date:
            if self.lot_id.expiration_date:
                barcode = '17' + self.lot_id.expiration_date.strftime('%y%m%d') + barcode
            if self.lot_id.use_date:
                barcode = '15' + self.lot_id.use_date.strftime('%y%m%d') + barcode
        return barcode

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == 'fefo':
            return 'removal_date, in_date, id'
        return super()._get_removal_strategy_order(removal_strategy)

    @api.depends('lot_id.expiration_date', 'use_expiration_date')
    def _compute_expiration_date(self):
        for quant in self:
            if quant.lot_id and quant.use_expiration_date:
                quant.expiration_date = quant.lot_id.expiration_date
            else:
                quant.expiration_date = False

    def _inverse_expiration_date(self):
        for quant in self:
            if not quant.lot_id:
                continue
            if not quant.expiration_date:
                quant.lot_id.expiration_date = False
            elif quant.use_expiration_date:
                delta = quant.expiration_date - quant.lot_id.expiration_date
                quant.lot_id.expiration_date = quant.expiration_date
                quant.lot_id._update_expiry_dates(delta)

    @api.depends('removal_date')
    def _compute_available_quantity(self):
        super()._compute_available_quantity()
        current_date = fields.Datetime.now()
        for quant in self:
            if quant.use_expiration_date and quant.removal_date and quant.removal_date <= current_date:
                quant.available_quantity = 0

    def _set_view_context(self):
        self_with_context = self
        if self.env.context.get('default_product_id') and self.env['product.product'].browse(self.env.context.get('default_product_id')).use_expiration_date:
            self_with_context = self.with_context(show_removal_date=True)
        return super(StockQuant, self_with_context)._set_view_context()
