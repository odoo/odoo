# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockRequestCount(models.TransientModel):
    _inherit = 'stock.request.count'

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        stock_quants = self.env['stock.quant'].browse(self.env.context.get('active_ids')).exists()
        res['accounting_date'] = max(
            stock_quants.filtered(lambda q: q.accounting_date and q.accounting_date <= fields.Date.today()).mapped('accounting_date'),
            default=fields.Date.today()
        )
        return res

    accounting_date = fields.Date('Accounting Date')

    def _get_values_to_write(self):
        res = super()._get_values_to_write()
        if self.accounting_date:
            res['accounting_date'] = self.accounting_date
        return res
