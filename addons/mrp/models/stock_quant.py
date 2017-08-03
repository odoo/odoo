# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    consumed_quant_ids = fields.Many2many(
        'stock.quant', 'stock_quant_consume_rel', 'produce_quant_id', 'consume_quant_id')
    produced_quant_ids = fields.Many2many(
        'stock.quant', 'stock_quant_consume_rel', 'consume_quant_id', 'produce_quant_id')

    def _prepare_history(self):
        vals = super(StockQuant, self)._prepare_history()
        vals['consumed_quant_ids'] = [(4, quant.id) for quant in self.consumed_quant_ids]
        vals['produced_quant_ids'] = [(4, quant.id) for quant in self.produced_quant_ids]
        return vals
