# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    removal_date = fields.Datetime(related='lot_id.removal_date', store=True)

    @api.model
    def apply_removal_strategy(self, qty, move, ops=False, domain=None, removal_strategy='fifo'):
        if removal_strategy == 'fefo':
            return self._quants_get_order(qty, move, ops=ops, domain=domain, orderby='removal_date, in_date, id')
        return super(StockQuant, self).apply_removal_strategy(qty, move, ops=ops, domain=domain, removal_strategy=removal_strategy)
