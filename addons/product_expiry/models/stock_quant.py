# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    removal_date = fields.Datetime(related='lot_id.removal_date', store=True)

    @api.model
    def _quants_removal_get_order(self, removal_strategy):
        if removal_strategy == 'fefo':
            return 'removal_date, in_date, id'
        return super(StockQuant, self)._quants_removal_get_order(removal_strategy=removal_strategy)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _prepare_lot_vals(self, pack_op_lot):
        vals = super(StockPicking, self)._prepare_lot_vals(pack_op_lot)
        vals['life_date'] = pack_op_lot.life_date
        return vals
